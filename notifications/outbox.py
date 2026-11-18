"""Queueing notifications and sending them.

A comment or a visit writes PushMessage rows in its own transaction; a
long-running loop (`run`, in the scheduler service or `reeltime push`)
sends them, so a web request never waits on a push service.

Close-together messages about the same thing become one: the first goes
at once, later ones wait until MERGE after it and are merged while they
wait ("3 new comments on 1m05 v2").
"""

import datetime
import hashlib
import json
import logging
import threading
import unicodedata

from django.conf import settings
from django.db import close_old_connections
from django.db.models import QuerySet
from django.utils import timezone
import requests

from accounts.models import Role
from accounts.models import User
from notifications import devices
from notifications import keys
from notifications import webpush
from notifications.models import Kind
from notifications.models import PushDevice
from notifications.models import PushMessage

_LOGGER = logging.getLogger(__name__)

# How long a message is worth sending.
TTL = datetime.timedelta(days=1)
# Messages about one thing closer together than this are merged.
MERGE = datetime.timedelta(minutes=2)
# At most one "opened" per link and device in this long.
OPEN_QUIET = datetime.timedelta(minutes=10)
# Refusals in a row (e.g. a changed key) before a device is dropped.
MAX_FAILURES = 5
# Messages sent per pass, and the pause between passes.
BATCH = 50
INTERVAL = 2.0
MAX_BACKOFF = datetime.timedelta(hours=1)

_FLAGS = {Kind.COMMENT: "notify_comments", Kind.OPEN: "notify_opens"}
_DROPPED = {"Cc", "Cf", "Co", "Cs", "Zl", "Zp"}


def clean(text: str, limit: int) -> str:
    """Text fit for a lock screen: one line, no hidden characters.

    Control, format (bidi, zero-width), private-use and separator
    characters become spaces; runs of space become one; too long ends
    in an ellipsis.
    """
    shown = "".join(
        " " if unicodedata.category(c) in _DROPPED else c for c in text
    )
    shown = " ".join(shown.split())
    if len(shown) > limit:
        shown = shown[: limit - 1].rstrip() + "…"
    return shown


def who(name: str, member: bool) -> str:
    """A commenter's name as shown; a guest's always says so."""
    shown = clean(name, 40) or "Someone"
    return shown if member else f"{shown} (guest)"


def _wanted(user: User, kind: str) -> bool:
    if not user.is_active or user.role == Role.NONE:
        return False
    flag = _FLAGS.get(Kind(kind))
    return flag is None or bool(getattr(user, flag))


def _devices(kind: str, skip_user: int | None) -> QuerySet[PushDevice]:
    found = (
        PushDevice.objects.filter(key=keys.fingerprint(), user__is_active=True)
        .exclude(user__role=Role.NONE)
        .filter(**{f"user__{_FLAGS[Kind(kind)]}": True})
        .select_related("user")
    )
    if skip_user is not None:
        found = found.exclude(user_id=skip_user)
    return found


def comment(
    *,
    project: str,
    about: str,
    label: str,
    name: str,
    member: bool,
    author: int | None,
    text: str,
    reply: bool,
    path: str,
) -> int:
    """Queues "Jane (guest) commented on 1m05 v2: …" for everyone who wants it.

    Args:
        project: The project's name, the notification's title.
        about: What it's about, e.g. "cue-12".
        label: The cue and version, e.g. "1m05 v2".
        name: Who wrote it.
        member: Whether they're signed in to ReelTime.
        author: Their user id, who isn't told about their own comment.
        text: The comment.
        reply: Whether it answers another comment.
        path: The page a tap opens.

    Returns:
        How many devices it was queued for.
    """
    now = timezone.now()
    writer = who(name, member)
    said = clean(text, 120)
    verb = "replied on" if reply else "commented on"
    first = f"{writer} {verb} {label}: {said}"
    queued = 0
    for device in _devices(Kind.COMMENT, author):
        waiting = PushMessage.objects.filter(
            device=device, kind=Kind.COMMENT, about=about, sent_at__isnull=True
        ).first()
        if waiting is not None:
            waiting.count += 1
            waiting.body = (
                f"{waiting.count} new comments on {label}. {writer}: {said}"
            )
            waiting.path = path
            waiting.save(update_fields=["count", "body", "path"])
        else:
            PushMessage.objects.create(
                device=device,
                kind=Kind.COMMENT,
                about=about,
                title=clean(project, 100),
                body=first,
                path=path,
                created_at=now,
                next_try_at=_after_last(device, about, now),
            )
        queued += 1
    return queued


def _after_last(
    device: PushDevice, about: str, now: datetime.datetime
) -> datetime.datetime:
    """When the next comment message about `about` may go."""
    last = (
        PushMessage.objects.filter(
            device=device,
            kind=Kind.COMMENT,
            about=about,
            sent_at__isnull=False,
        )
        .order_by("-sent_at")
        .values_list("sent_at", flat=True)
        .first()
    )
    return max(now, last + MERGE) if last is not None else now


def opened(
    *,
    project: str,
    about: str,
    label: str,
    name: str,
    member: bool,
    viewer: int | None,
    path: str,
) -> int:
    """Queues "Jane (guest) opened 1m05 v2", at most once per OPEN_QUIET.

    Returns:
        How many devices it was queued for.
    """
    now = timezone.now()
    queued = 0
    for device in _devices(Kind.OPEN, viewer):
        if PushMessage.objects.filter(
            device=device,
            kind=Kind.OPEN,
            about=about,
            created_at__gte=now - OPEN_QUIET,
        ).exists():
            continue
        PushMessage.objects.create(
            device=device,
            kind=Kind.OPEN,
            about=about,
            title=clean(project, 100),
            body=f"{who(name, member)} opened {label}",
            path=path,
            created_at=now,
            next_try_at=now,
        )
        queued += 1
    return queued


def test(device: PushDevice) -> PushMessage:
    """Queues a test notification for one device."""
    return PushMessage.objects.create(
        device=device,
        kind=Kind.TEST,
        about=f"test-{device.pk}",
        title="ReelTime",
        body="Notifications are on for this device.",
        path="/notifications/",
    )


def topic(about: str) -> str:
    """A push Topic for `about`: 32 base64url characters, nothing readable."""
    return webpush.b64url(hashlib.sha256(about.encode()).digest()[:24])


def payload(message: PushMessage) -> bytes:
    """What the service worker gets."""
    return json.dumps(
        {
            "title": message.title,
            "body": message.body,
            "path": message.path,
            "tag": message.about,
        },
        ensure_ascii=False,
    ).encode()


def session() -> requests.Session:
    """A requests session that ignores proxy and .netrc settings."""
    made = requests.Session()
    made.trust_env = False
    return made


def _retry(message: PushMessage, now: datetime.datetime) -> None:
    message.tries += 1
    wait = min(datetime.timedelta(seconds=5 * 2**message.tries), MAX_BACKOFF)
    message.next_try_at = now + wait
    message.save(update_fields=["tries", "next_try_at"])


def _refused(device: PushDevice, message: PushMessage, status: int) -> None:
    _LOGGER.warning(
        "push refused (%s); %s refusals", status, device.failures + 1
    )
    message.delete()
    device.failures += 1
    if device.failures >= MAX_FAILURES:
        device.delete()
    else:
        device.save(update_fields=["failures"])


def deliver(
    message: PushMessage, now: datetime.datetime, client: requests.Session
) -> bool:
    """Sends one message, or deals with why it can't go.

    Returns:
        Whether the push service took it.
    """
    device = message.device
    if now - message.created_at > TTL:
        message.delete()
        return False
    if device.key != keys.fingerprint() or not devices.allowed(device.endpoint):
        device.delete()
        return False
    if not _wanted(device.user, message.kind):
        message.delete()
        return False
    body = webpush.encrypt(
        payload(message),
        webpush.unb64url(device.p256dh),
        webpush.unb64url(device.auth),
    )
    left = TTL - (now - message.created_at)
    headers = {
        "Authorization": webpush.vapid(
            keys.private_key(), device.endpoint, settings.BASE_URL
        ),
        "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream",
        "TTL": str(max(int(left.total_seconds()), 0)),
        "Urgency": "normal",
        "Topic": topic(message.about),
    }
    try:
        response = client.post(
            device.endpoint,
            data=body,
            headers=headers,
            timeout=settings.PUSH_TIMEOUT,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        _LOGGER.warning("push failed: %s", type(exc).__name__)
        _retry(message, now)
        return False
    status = response.status_code
    if 200 <= status < 300:
        message.sent_at = now
        message.tries += 1
        message.save(update_fields=["sent_at", "tries"])
        device.last_sent_at = now
        device.failures = 0
        device.save(update_fields=["last_sent_at", "failures"])
        return True
    if status in (404, 410):
        device.delete()  # the browser unsubscribed
    elif status == 429 or status >= 500:
        _retry(message, now)
    else:
        _refused(device, message, status)
    return False


def drain(
    now: datetime.datetime | None = None, client: requests.Session | None = None
) -> int:
    """Sends what's due and clears out old messages.

    Returns:
        How many were sent.
    """
    now = now or timezone.now()
    client = client or session()
    due = list(
        PushMessage.objects.filter(sent_at__isnull=True, next_try_at__lte=now)
        .select_related("device__user")
        .order_by("next_try_at", "id")[:BATCH]
    )
    sent = sum(deliver(message, now, client) for message in due)
    PushMessage.objects.filter(sent_at__lt=now - TTL).delete()
    PushMessage.objects.filter(
        sent_at__isnull=True, created_at__lt=now - TTL
    ).delete()
    return sent


def run(stop: threading.Event, interval: float = INTERVAL) -> None:
    """Sends notifications every `interval` seconds until `stop` is set."""
    client = session()
    while not stop.is_set():
        close_old_connections()
        try:
            drain(client=client)
        except Exception:  # pylint: disable=broad-exception-caught
            # Keep sending; the next pass may succeed.
            _LOGGER.exception("sending notifications failed")
        stop.wait(interval)
    close_old_connections()
