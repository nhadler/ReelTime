"""Review links tell the team's devices: comments and visits."""

from collections.abc import Callable

from django.contrib.auth import get_user_model
from django.test import Client
import pytest

from accounts.models import Role
from accounts.models import User
from cues import models
from cues.services import review
from notifications import keys
from notifications.models import PushDevice
from notifications.models import PushMessage
from tests import factories
from tests.fakes import push_browser
from tests.medium.review.setup import guest
from tests.medium.review.setup import page_url

pytestmark = pytest.mark.django_db


@pytest.fixture(name="browser")
def fixture_browser() -> push_browser.Browser:
    return push_browser.new()


def _user(client: Client) -> User:
    return get_user_model().objects.get(pk=client.session["_auth_user_id"])


def test_a_guests_comment_tells_the_team(
    cue: models.Cue, link: models.ReviewLink, browser: push_browser.Browser
) -> None:
    del link
    editor = factories.UserFactory.create()
    PushDevice.objects.create(
        user=editor,
        endpoint=browser.endpoint,
        p256dh=browser.p256dh,
        auth=browser.secret,
        key=keys.fingerprint(),
    )
    version = cue.versions.get()
    review.add_comment(
        version, name="Dana", body="Too busy", frame=24, user=None
    )
    review.add_comment(version, name="Me", body="Mine", frame=24, user=editor)
    message = PushMessage.objects.get()
    assert message.title == "Night Ferry"
    assert (
        message.body == f"Dana (guest) commented on {cue.number} v1: Too busy"
    )
    assert message.path == (
        f"/cues/{cue.pk}/?version={version.pk}#group-review"
    )


def test_opening_a_link_tells_the_team_but_not_the_viewer(
    role_client: Callable[[Role], Client],
    cue: models.Cue,
    link: models.ReviewLink,
    browser: push_browser.Browser,
) -> None:
    del cue
    editor = factories.UserFactory.create()
    PushDevice.objects.create(
        user=editor,
        endpoint=browser.endpoint,
        p256dh=browser.p256dh,
        auth=browser.secret,
        key=keys.fingerprint(),
    )
    guest("Dana").get(page_url(link))
    assert PushMessage.objects.get().body.startswith("Dana (guest) opened ")
    PushMessage.objects.all().delete()
    viewer = role_client(Role.VIEWER)
    PushDevice.objects.update(user=_user(viewer))
    viewer.get(page_url(link))
    assert not PushMessage.objects.exists()
