"""The name review pages show in place of ReelTime (App Settings)."""

from collections.abc import Callable

from django.test import Client
from django.urls import reverse
import pytest

from accounts.models import Role
from cues import models
from cues.services import review
from tests.medium.review.setup import guest
from tests.medium.review.setup import page_url

pytestmark = pytest.mark.django_db


def _named(name: str) -> None:
    settings_row = models.AppSettings.load()
    settings_row.review_name = name
    settings_row.save()


def test_review_pages_say_reeltime_by_default(link: models.ReviewLink) -> None:
    page = guest().get(page_url(link)).content.decode()
    assert '<span class="wordmark__reel">Reel</span>Time' in page
    assert "· Review · ReelTime</title>" in page


def test_a_name_replaces_reeltime_on_every_review_page(
    link: models.ReviewLink,
) -> None:
    _named("Christa Duggan")
    client = guest()
    page = client.get(page_url(link)).content.decode()
    assert '<p class="review-head__mark">Christa Duggan</p>' in page
    assert "· Review · Christa Duggan</title>" in page
    assert "wordmark__reel" not in page
    # Before the video: asking who's watching, behind a password, gone.
    fresh = Client().get(page_url(link)).content.decode()
    assert "Review Link · Christa Duggan</title>" in fresh
    review.set_password(link, "strings42")
    locked = Client().get(page_url(link)).content.decode()
    assert "Review Link · Christa Duggan</title>" in locked
    gone = Client().get(reverse("cues:review", args=["nope"]))
    assert "Review Link · Christa Duggan</title>" in gone.content.decode()


def test_the_name_is_escaped(link: models.ReviewLink) -> None:
    _named("<b>Christa</b>")
    page = guest().get(page_url(link)).content.decode()
    assert "&lt;b&gt;Christa&lt;/b&gt;" in page
    assert "<b>Christa</b>" not in page


def test_the_rest_of_the_app_keeps_its_name(
    role_client: Callable[[Role], Client],
) -> None:
    _named("Christa Duggan")
    editor = role_client(Role.EDITOR)
    page = editor.get(reverse("cues:dashboard")).content.decode()
    assert "Christa Duggan" not in page
