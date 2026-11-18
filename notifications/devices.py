"""Turning notifications on and off for a browser.

The server will POST to the endpoint a browser hands it, so only push
services' own https addresses are taken (settings.PUSH_HOSTS): nothing
can point ReelTime at an address inside the network.
"""

import urllib.parse

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from notifications import keys
from notifications import models
from notifications import webpush

# Devices kept per user; another removes the oldest.
MAX_DEVICES = 10


class DeviceError(ValueError):
    """A subscription ReelTime won't take."""


def allowed(endpoint: str) -> bool:
    """Whether an endpoint is a known push service's https address."""
    try:
        parts = urllib.parse.urlsplit(endpoint)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or port not in (None, 443):
        return False
    if parts.username is not None or parts.password is not None:
        return False
    return any(
        host == known or host.endswith("." + known)
        for known in settings.PUSH_HOSTS
    )


def _key(text: object, length: int, what: str) -> str:
    if not isinstance(text, str) or len(text) > 200:
        raise DeviceError(f"The browser's {what} is missing.")
    try:
        raw = webpush.unb64url(text)
    except ValueError:
        raise DeviceError(f"The browser's {what} isn't readable.") from None
    if len(raw) != length:
        raise DeviceError(f"The browser's {what} isn't readable.")
    return webpush.b64url(raw)


def subscribe(
    user: User, endpoint: object, p256dh: object, auth: object
) -> models.PushDevice:
    """Keeps a browser's subscription for the user.

    A subscription another user held moves to this one (one browser,
    one person signed in). Past MAX_DEVICES, the oldest goes.

    Raises:
        DeviceError: The endpoint or the keys aren't usable.
    """
    if not isinstance(endpoint, str) or len(endpoint) > 1024:
        raise DeviceError("That isn't a push address.")
    if not allowed(endpoint):
        raise DeviceError(
            "That browser's push service isn't one ReelTime uses."
        )
    public = _key(p256dh, 65, "key")
    try:
        webpush.load_public(webpush.unb64url(public))
    except ValueError:
        raise DeviceError("The browser's key isn't readable.") from None
    secret = _key(auth, 16, "secret")
    with transaction.atomic():
        device, _ = models.PushDevice.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": user,
                "p256dh": public,
                "auth": secret,
                "key": keys.fingerprint(),
                "failures": 0,
                "created_at": timezone.now(),
            },
        )
        older = user.push_devices.values_list("pk", flat=True)[MAX_DEVICES:]
        models.PushDevice.objects.filter(pk__in=list(older)).delete()
    return device


def remove(user: User, device_id: object) -> bool:
    """Removes one of the user's devices; whether there was one."""
    try:
        pk = int(str(device_id))
    except ValueError:
        return False
    deleted, _ = models.PushDevice.objects.filter(user=user, pk=pk).delete()
    return deleted > 0


def forget(user: User, endpoint: object) -> bool:
    """Removes the user's device with this endpoint (signing out)."""
    if not isinstance(endpoint, str):
        return False
    deleted, _ = models.PushDevice.objects.filter(
        user=user, endpoint=endpoint
    ).delete()
    return deleted > 0
