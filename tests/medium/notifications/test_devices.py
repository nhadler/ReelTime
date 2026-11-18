"""Turning notifications on and off (notifications.devices)."""

import pytest

from accounts.models import User
from notifications import devices
from notifications import keys
from notifications import webpush
from notifications.models import PushDevice
from tests import factories
from tests.fakes import push_browser

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://web.push.apple.com/QAbc",
        "https://api.push.apple.com/x",
        "https://fcm.googleapis.com/fcm/send/abc",
        "https://updates.push.services.mozilla.com/wpush/v2/abc",
        "https://wns2-par02p.notify.windows.com/w/?token=abc",
        "https://WEB.PUSH.APPLE.COM:443/QAbc",
    ],
)
def test_push_services_are_allowed(endpoint: str) -> None:
    assert devices.allowed(endpoint)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://web.push.apple.com/QAbc",
        "https://web.push.apple.com:8443/QAbc",
        "https://evilpush.apple.com/x",
        "https://push.apple.com.evil.example/x",
        "https://127.0.0.1/x",
        "https://user:pw@web.push.apple.com/x",
        "https://web.push.apple.com:notaport/x",
        "https://[::1/x",
        "file:///etc/passwd",
        "",
    ],
)
def test_other_addresses_are_not(endpoint: str) -> None:
    assert not devices.allowed(endpoint)


def _subscribe(user: User, browser: push_browser.Browser) -> PushDevice:
    return devices.subscribe(
        user, browser.endpoint, browser.p256dh, browser.secret
    )


def test_a_browser_subscribes_with_the_current_key() -> None:
    user = factories.UserFactory.create()
    browser = push_browser.new()
    device = _subscribe(user, browser)
    assert device.user == user
    assert device.p256dh == browser.p256dh
    assert device.auth == browser.secret
    assert device.key == keys.fingerprint()


def test_subscribing_again_updates_the_device() -> None:
    user = factories.UserFactory.create()
    browser = push_browser.new()
    first = _subscribe(user, browser)
    first.failures = 3
    first.save()
    browser.auth = b"\x01" * 16
    again = _subscribe(user, browser)
    assert again.pk == first.pk
    assert again.auth == browser.secret
    assert again.failures == 0


def test_a_browser_another_user_subscribed_moves_to_the_new_user() -> None:
    first, second = factories.UserFactory.create_batch(2)
    browser = push_browser.new()
    _subscribe(first, browser)
    _subscribe(second, browser)
    assert PushDevice.objects.get().user == second


def test_the_oldest_device_goes_past_the_limit() -> None:
    user = factories.UserFactory.create()
    made = [
        _subscribe(user, push_browser.new(f"https://web.push.apple.com/{n}"))
        for n in range(devices.MAX_DEVICES + 1)
    ]
    kept = set(user.push_devices.values_list("pk", flat=True))
    assert len(kept) == devices.MAX_DEVICES
    assert made[0].pk not in kept


@pytest.mark.parametrize(
    ("endpoint", "p256dh", "auth", "error"),
    [
        (None, "k", "a", "isn't a push address"),
        ("https://x" + "a" * 1024, "k", "a", "isn't a push address"),
        ("https://10.0.0.1/push", "k", "a", "isn't one ReelTime uses"),
        ("ENDPOINT", None, "AUTH", "key is missing"),
        ("ENDPOINT", "a" * 201, "AUTH", "key is missing"),
        ("ENDPOINT", "!!", "AUTH", "key isn't readable"),
        ("ENDPOINT", "AAAA", "AUTH", "key isn't readable"),
        ("ENDPOINT", "OFFCURVE", "AUTH", "key isn't readable"),
        ("ENDPOINT", "P256DH", "AAAA", "secret isn't readable"),
    ],
)
def test_unusable_subscriptions_are_refused(
    endpoint: object, p256dh: object, auth: object, error: str
) -> None:
    browser = push_browser.new()
    given = {
        "ENDPOINT": browser.endpoint,
        "P256DH": browser.p256dh,
        "AUTH": browser.secret,
        "OFFCURVE": webpush.b64url(b"\x04" + b"\x01" * 64),
    }
    user = factories.UserFactory.create()

    def value(text: object) -> object:
        return given.get(text, text) if isinstance(text, str) else text

    with pytest.raises(devices.DeviceError, match=error):
        devices.subscribe(user, value(endpoint), value(p256dh), value(auth))
    assert not PushDevice.objects.exists()


def test_a_user_removes_only_their_own_devices() -> None:
    owner, other = factories.UserFactory.create_batch(2)
    device = _subscribe(owner, push_browser.new())
    assert not devices.remove(other, device.pk)
    assert not devices.remove(owner, "nonsense")
    assert devices.remove(owner, str(device.pk))
    assert not PushDevice.objects.exists()


def test_signing_out_forgets_this_browser() -> None:
    owner, other = factories.UserFactory.create_batch(2)
    browser = push_browser.new()
    _subscribe(owner, browser)
    assert not devices.forget(owner, None)
    assert not devices.forget(other, browser.endpoint)
    assert devices.forget(owner, browser.endpoint)
    assert not PushDevice.objects.exists()
