"""Queueing and sending notifications (notifications.outbox)."""

import datetime
import json
import threading
from unittest import mock

from django.test import override_settings
from django.utils import timezone
import freezegun
import pytest
import requests
import responses

from accounts.models import Role
from accounts.models import User
from notifications import devices
from notifications import outbox
from notifications.models import Kind
from notifications.models import PushDevice
from notifications.models import PushMessage
from tests import factories
from tests.fakes import push_browser

pytestmark = pytest.mark.django_db

NOW = datetime.datetime(2026, 11, 17, 18, 0, tzinfo=datetime.UTC)


@pytest.fixture(autouse=True)
def _frozen() -> object:
    with freezegun.freeze_time(NOW) as frozen:
        yield frozen


def _device(
    browser: push_browser.Browser, user: User | None = None, **fields: object
) -> PushDevice:
    user = user or factories.UserFactory.create(**fields)
    return devices.subscribe(
        user, browser.endpoint, browser.p256dh, browser.secret
    )


def _comment(**changes: object) -> int:
    values: dict[str, object] = {
        "project": "Night Ferry",
        "about": "cue-1",
        "label": "1m01 v2",
        "name": "Jane",
        "member": False,
        "author": None,
        "text": "Too busy at the start",
        "reply": False,
        "path": "/cues/1/?version=2#group-review",
        **changes,
    }
    return outbox.comment(**values)  # type: ignore[arg-type]


def _opened(**changes: object) -> int:
    values: dict[str, object] = {
        "project": "Night Ferry",
        "about": "cue-1",
        "label": "1m01 v2",
        "name": "Jane",
        "member": False,
        "viewer": None,
        "path": "/cues/1/?version=2#group-review",
        **changes,
    }
    return outbox.opened(**values)  # type: ignore[arg-type]


# What's shown.


def test_lock_screen_text_loses_hidden_characters() -> None:
    sneaky = "Apple\u202eID\u200b\nverify\x00 now\ue000"
    assert outbox.clean(sneaky, 100) == "Apple ID verify now"
    assert outbox.clean("a" * 10, 5) == "aaaa…"


def test_a_guest_is_always_marked() -> None:
    assert outbox.who("Jane", member=False) == "Jane (guest)"
    assert outbox.who("Jane", member=True) == "Jane"
    assert outbox.who("\u200b", member=False) == "Someone (guest)"
    assert outbox.who("x" * 60, member=True) == "x" * 39 + "…"


def test_the_topic_is_short_and_says_nothing() -> None:
    topic = outbox.topic("cue-1")
    assert len(topic) == 32
    assert "cue" not in topic
    assert topic == outbox.topic("cue-1") != outbox.topic("cue-2")


# Queueing.


def test_a_comment_is_queued_for_everyone_who_wants_it(
    browser: push_browser.Browser,
) -> None:
    device = _device(browser)
    _device(
        push_browser.new("https://fcm.googleapis.com/a"), notify_comments=False
    )
    _device(push_browser.new("https://fcm.googleapis.com/b"), is_active=False)
    _device(push_browser.new("https://fcm.googleapis.com/c"), role=Role.NONE)
    stale = _device(push_browser.new("https://fcm.googleapis.com/d"))
    stale.key = "another"
    stale.save()
    assert _comment() == 1
    message = PushMessage.objects.get()
    assert message.device == device
    assert message.title == "Night Ferry"
    assert (
        message.body
        == "Jane (guest) commented on 1m01 v2: Too busy at the start"
    )
    assert message.next_try_at == NOW


def test_a_reply_says_so_and_its_author_isnt_told(
    browser: push_browser.Browser,
) -> None:
    device = _device(browser)
    other = _device(push_browser.new("https://fcm.googleapis.com/a"))
    assert _comment(reply=True, member=True, author=other.user.pk) == 1
    assert PushMessage.objects.get().device == device
    assert PushMessage.objects.get().body.startswith(
        "Jane replied on 1m01 v2: "
    )


def test_comments_close_together_become_one(
    browser: push_browser.Browser, _frozen: freezegun.api.FrozenDateTimeFactory
) -> None:
    device = _device(browser)
    _comment()
    sent = PushMessage.objects.get()
    sent.sent_at = NOW
    sent.save()
    _frozen.tick(30)
    _comment(name="Sam", text="Louder")
    _comment(name="Ann", text="Softer")
    waiting = PushMessage.objects.get(sent_at__isnull=True)
    assert waiting.count == 2
    assert waiting.body == "2 new comments on 1m01 v2. Ann (guest): Softer"
    assert waiting.next_try_at == NOW + outbox.MERGE
    assert device.messages.count() == 2


def test_a_link_opened_is_told_once_in_a_while(
    browser: push_browser.Browser, _frozen: freezegun.api.FrozenDateTimeFactory
) -> None:
    device = _device(browser)
    viewer = _device(push_browser.new("https://fcm.googleapis.com/a"))
    assert _opened(viewer=viewer.user.pk) == 1
    assert PushMessage.objects.get().body == "Jane (guest) opened 1m01 v2"
    assert PushMessage.objects.get().device == device
    _frozen.tick(60)
    assert _opened(viewer=viewer.user.pk) == 0
    _frozen.tick(outbox.OPEN_QUIET)
    assert _opened(viewer=viewer.user.pk) == 1


def test_links_opened_can_be_turned_off(browser: push_browser.Browser) -> None:
    _device(browser, notify_opens=False)
    assert _opened() == 0


# Sending.


def _accept(push_service: responses.RequestsMock, status: int = 201) -> None:
    push_service.add(responses.POST, push_browser.ENDPOINT, status=status)


def test_a_message_is_sent_encrypted_and_signed(
    browser: push_browser.Browser, push_service: responses.RequestsMock
) -> None:
    device = _device(browser)
    _accept(push_service)
    _comment()
    assert outbox.drain() == 1
    request = push_service.calls[0].request
    assert request.headers["Content-Encoding"] == "aes128gcm"
    assert request.headers["Urgency"] == "normal"
    assert request.headers["TTL"] == str(24 * 60 * 60)
    assert request.headers["Topic"] == outbox.topic("cue-1")
    assert request.headers["Authorization"].startswith("vapid t=")
    shown = json.loads(browser.read(request.body))
    assert shown == {
        "title": "Night Ferry",
        "body": "Jane (guest) commented on 1m01 v2: Too busy at the start",
        "path": "/cues/1/?version=2#group-review",
        "tag": "cue-1",
    }
    device.refresh_from_db()
    assert device.last_sent_at == NOW
    assert PushMessage.objects.get().sent_at == NOW


def test_a_test_message_goes_to_one_device(
    browser: push_browser.Browser, push_service: responses.RequestsMock
) -> None:
    device = _device(browser, notify_comments=False, notify_opens=False)
    _accept(push_service)
    outbox.test(device)
    assert outbox.drain() == 1
    assert json.loads(browser.read(push_service.calls[0].request.body))[
        "body"
    ] == ("Notifications are on for this device.")


def test_a_message_waits_its_turn(browser: push_browser.Browser) -> None:
    _device(browser)
    _comment()
    PushMessage.objects.update(next_try_at=NOW + datetime.timedelta(minutes=1))
    assert outbox.drain() == 0


@pytest.mark.parametrize("status", [404, 410])
def test_an_unsubscribed_browser_is_forgotten(
    browser: push_browser.Browser,
    push_service: responses.RequestsMock,
    status: int,
) -> None:
    _device(browser)
    _accept(push_service, status)
    _comment()
    assert outbox.drain() == 0
    assert not PushDevice.objects.exists()


@pytest.mark.parametrize("status", [429, 500, 503])
def test_a_busy_push_service_is_tried_again_later(
    browser: push_browser.Browser,
    push_service: responses.RequestsMock,
    status: int,
) -> None:
    _device(browser)
    _accept(push_service, status)
    _comment()
    outbox.drain()
    message = PushMessage.objects.get()
    assert message.tries == 1
    assert message.next_try_at == NOW + datetime.timedelta(seconds=10)
    assert message.sent_at is None


def test_a_push_service_out_of_reach_is_tried_again_later(
    browser: push_browser.Browser, push_service: responses.RequestsMock
) -> None:
    _device(browser)
    push_service.add(
        responses.POST, push_browser.ENDPOINT, body=requests.ConnectionError()
    )
    _comment()
    assert outbox.drain() == 0
    assert PushMessage.objects.get().tries == 1


def test_backing_off_stops_growing_at_an_hour(
    browser: push_browser.Browser,
) -> None:
    _device(browser)
    _comment()
    message = PushMessage.objects.get()
    message.tries = 20
    outbox._retry(message, NOW)  # pylint: disable=protected-access
    assert message.next_try_at == NOW + outbox.MAX_BACKOFF


def test_refusals_in_a_row_drop_the_device(
    browser: push_browser.Browser, push_service: responses.RequestsMock
) -> None:
    device = _device(browser)
    _accept(push_service, 403)
    for _ in range(outbox.MAX_FAILURES - 1):
        _comment()
        outbox.drain()
        PushMessage.objects.all().delete()
    device.refresh_from_db()
    assert device.failures == outbox.MAX_FAILURES - 1
    _comment()
    outbox.drain()
    assert not PushDevice.objects.exists()


def test_a_delivery_clears_the_refusals(
    browser: push_browser.Browser, push_service: responses.RequestsMock
) -> None:
    device = _device(browser)
    device.failures = 3
    device.save()
    _accept(push_service)
    _comment()
    outbox.drain()
    device.refresh_from_db()
    assert device.failures == 0


def test_a_message_past_its_time_is_dropped(
    browser: push_browser.Browser,
) -> None:
    _device(browser)
    _comment()
    PushMessage.objects.update(
        created_at=NOW - outbox.TTL - datetime.timedelta(1)
    )
    message = PushMessage.objects.select_related("device__user").get()
    assert not outbox.deliver(message, NOW, outbox.session())
    assert not PushMessage.objects.exists()


def test_a_device_on_an_old_key_is_dropped(
    browser: push_browser.Browser,
) -> None:
    _device(browser)
    _comment()
    PushDevice.objects.update(key="old")
    assert outbox.drain() == 0
    assert not PushDevice.objects.exists()


def test_a_device_no_longer_allowed_is_dropped(
    browser: push_browser.Browser,
) -> None:
    _device(browser)
    _comment()
    with override_settings(PUSH_HOSTS=("example.org",)):
        assert outbox.drain() == 0
    assert not PushDevice.objects.exists()


@pytest.mark.parametrize(
    "change",
    [{"is_active": False}, {"role": Role.NONE}, {"notify_comments": False}],
)
def test_nothing_goes_to_someone_who_no_longer_wants_it(
    browser: push_browser.Browser, change: dict[str, object]
) -> None:
    device = _device(browser)
    _comment()
    User.objects.filter(pk=device.user_id).update(**change)
    assert outbox.drain() == 0
    assert not PushMessage.objects.exists()
    assert PushDevice.objects.exists()


def test_old_messages_are_cleared_out(browser: push_browser.Browser) -> None:
    device = _device(browser)
    old = NOW - outbox.TTL - datetime.timedelta(minutes=1)
    for sent in (old, NOW, None):
        PushMessage.objects.create(
            device=device,
            kind=Kind.COMMENT,
            about="cue-1",
            title="t",
            body="b",
            path="/",
            created_at=old if sent is None else NOW,
            next_try_at=NOW + datetime.timedelta(days=9),
            sent_at=sent,
        )
    outbox.drain()
    assert list(PushMessage.objects.values_list("sent_at", flat=True)) == [NOW]


# The loop.


def test_the_loop_sends_until_stopped() -> None:
    stop = threading.Event()
    calls: list[int] = []

    def drain(**kwargs: object) -> int:
        del kwargs
        calls.append(1)
        if len(calls) == 2:
            stop.set()
            raise RuntimeError("push service gone")
        return 0

    with mock.patch.object(outbox, "drain", drain):
        outbox.run(stop, interval=0)
    assert len(calls) == 2


def test_the_loop_ends_when_stopped_while_waiting() -> None:
    stop = threading.Event()
    with (
        mock.patch.object(outbox, "drain", return_value=0) as drain,
        mock.patch.object(stop, "wait", side_effect=lambda _: stop.set()),
    ):
        outbox.run(stop)
    drain.assert_called_once()


def test_the_messages_say_what_they_are(browser: push_browser.Browser) -> None:
    device = _device(browser)
    _comment()
    assert str(device) == f"Notification device of {device.user}"
    assert str(PushMessage.objects.get()) == (
        "Night Ferry: Jane (guest) commented on 1m01 v2: Too busy at the start"
    )


def test_sessions_ignore_proxy_settings() -> None:
    assert outbox.session().trust_env is False


def test_now_defaults_to_the_clock(browser: push_browser.Browser) -> None:
    _device(browser)
    _comment()
    PushMessage.objects.update(
        next_try_at=timezone.now() + datetime.timedelta(1)
    )
    assert outbox.drain() == 0
