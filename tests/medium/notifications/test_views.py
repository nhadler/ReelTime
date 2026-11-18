"""The Notifications page, subscribing, and the web app files."""

from collections.abc import Callable, Iterator
import io
import json
import os
import signal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
import pytest

from accounts.models import AuditAction
from accounts.models import AuditEvent
from accounts.models import Role
from accounts.models import User
from notifications import keys
from notifications import outbox
from notifications.models import PushDevice
from notifications.models import PushMessage
from tests.fakes import push_browser

pytestmark = pytest.mark.django_db

PAGE = "/notifications/"


def _user(client: Client) -> User:
    return get_user_model().objects.get(pk=client.session["_auth_user_id"])


def _subscribe(client: Client, data: object) -> tuple[int, dict[str, object]]:
    response = client.post(
        reverse("notifications:subscribe"),
        data if isinstance(data, str) else json.dumps(data),
        content_type="application/json",
    )
    return response.status_code, response.json()


def test_a_viewer_turns_a_browser_on(
    role_client: Callable[[Role], Client], browser: push_browser.Browser
) -> None:
    client = role_client(Role.VIEWER)
    status, answer = _subscribe(client, browser.subscription())
    device = PushDevice.objects.get()
    assert (status, answer) == (200, {"id": device.pk})
    assert device.user == _user(client)
    assert AuditEvent.objects.filter(
        action=AuditAction.NOTIFICATIONS_ON
    ).exists()


@pytest.mark.parametrize(
    "data", ["not json", "[1]", {"endpoint": push_browser.ENDPOINT, "keys": 3}]
)
def test_a_bad_subscription_says_why(
    role_client: Callable[[Role], Client], data: object
) -> None:
    status, answer = _subscribe(role_client(Role.VIEWER), data)
    assert status == 400
    assert answer["error"]
    assert not PushDevice.objects.exists()


def test_the_page_lists_devices_and_carries_the_key(
    role_client: Callable[[Role], Client], browser: push_browser.Browser
) -> None:
    client = role_client(Role.VIEWER)
    _subscribe(client, browser.subscription())
    response = client.get(PAGE)
    html = response.content.decode()
    assert response.status_code == 200
    assert keys.public_key() in html
    assert reverse("notifications:subscribe") in html
    assert f'data-endpoint="{browser.endpoint}"' in html
    assert "Send Test" in html
    assert 'name="comments" checked' in html


def test_the_page_without_devices_says_so(
    role_client: Callable[[Role], Client],
) -> None:
    assert (
        "No devices yet." in role_client(Role.EDITOR).get(PAGE).content.decode()
    )


def test_the_profile_menu_links_here_and_sign_out_forgets(
    role_client: Callable[[Role], Client],
) -> None:
    html = role_client(Role.VIEWER).get(PAGE).content.decode()
    assert f'href="{PAGE}"' in html
    assert f'data-forget-url="{reverse("notifications:forget")}"' in html
    assert '<link rel="manifest" href="/manifest.webmanifest">' in html


def test_choosing_what_to_be_told_about(
    role_client: Callable[[Role], Client],
) -> None:
    client = role_client(Role.VIEWER)
    response = client.post(PAGE, {"action": "choose", "opens": "on"})
    assert response.status_code == 302
    user = _user(client)
    assert (user.notify_comments, user.notify_opens) == (False, True)


def test_sending_a_test_and_removing_a_device(
    role_client: Callable[[Role], Client], browser: push_browser.Browser
) -> None:
    client = role_client(Role.VIEWER)
    _subscribe(client, browser.subscription())
    device = PushDevice.objects.get()
    client.post(PAGE, {"action": "test", "device": str(device.pk)})
    assert PushMessage.objects.get().device == device
    client.post(PAGE, {"action": "test", "device": "x"})
    client.post(PAGE, {"action": "remove", "device": str(device.pk)})
    assert not PushDevice.objects.exists()
    assert (
        AuditEvent.objects.filter(action=AuditAction.NOTIFICATIONS_OFF).count()
        == 1
    )
    client.post(PAGE, {"action": "remove", "device": str(device.pk)})
    client.post(PAGE, {"action": "other"})
    assert (
        AuditEvent.objects.filter(action=AuditAction.NOTIFICATIONS_OFF).count()
        == 1
    )


def test_someone_elses_device_is_out_of_reach(
    role_client: Callable[[Role], Client], browser: push_browser.Browser
) -> None:
    _subscribe(role_client(Role.EDITOR), browser.subscription())
    device = PushDevice.objects.get()
    other = role_client(Role.VIEWER)
    other.post(PAGE, {"action": "test", "device": str(device.pk)})
    other.post(PAGE, {"action": "remove", "device": str(device.pk)})
    assert PushDevice.objects.exists()
    assert not PushMessage.objects.exists()
    assert (
        f'data-endpoint="{browser.endpoint}"'
        not in other.get(PAGE).content.decode()
    )


def test_signing_out_forgets_the_browser(
    role_client: Callable[[Role], Client], browser: push_browser.Browser
) -> None:
    client = role_client(Role.VIEWER)
    _subscribe(client, browser.subscription())
    url = reverse("notifications:forget")
    response = client.post(
        url,
        json.dumps({"endpoint": browser.endpoint}),
        content_type="application/json",
    )
    assert response.status_code == 204
    assert not PushDevice.objects.exists()
    assert (
        client.post(url, "nonsense", content_type="text/plain").status_code
        == 204
    )
    assert (
        AuditEvent.objects.filter(action=AuditAction.NOTIFICATIONS_OFF).count()
        == 1
    )


def test_the_manifest_is_public(client: Client) -> None:
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/manifest+json"
    manifest = response.json()
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == manifest["scope"] == "/"
    assert {icon["sizes"] for icon in manifest["icons"]} == {
        "192x192",
        "512x512",
    }
    assert "maskable" in {icon["purpose"] for icon in manifest["icons"]}


def test_the_service_worker_is_public_and_never_cached(client: Client) -> None:
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/javascript"
    assert response["Cache-Control"] == "no-cache"
    assert b"showNotification" in response.content
    assert b"'fetch'" not in response.content


# The commands.


@pytest.fixture(name="restore_signals")
def fixture_restore_signals() -> Iterator[None]:
    saved = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    yield
    for signum, handler in saved.items():
        signal.signal(signum, handler)


@pytest.mark.usefixtures("restore_signals")
def test_the_push_command_runs_until_sigterm() -> None:
    def fake_run(stop: object) -> None:
        os.kill(os.getpid(), signal.SIGTERM)
        assert stop.is_set()  # type: ignore[attr-defined]

    out = io.StringIO()
    with mock.patch.object(outbox, "run", fake_run):
        call_command("push", stdout=out)
    assert "Stopped sending notifications." in out.getvalue()
