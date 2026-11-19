"""A dialog or panel's address opened directly goes to its page."""

from collections.abc import Callable

from django.test import Client
from django.urls import reverse
import pytest

from accounts.models import Role
from cues import models
from cues.services import demo

pytestmark = pytest.mark.django_db

HX = {"HX-Request": "true"}


@pytest.fixture(name="editor")
def fixture_editor(role_client: Callable[[Role], Client]) -> Client:
    return role_client(Role.EDITOR)


@pytest.fixture(name="project")
def fixture_project() -> models.Project:
    return demo.build_demo().project


@pytest.mark.parametrize(
    ("name", "action"),
    [("import", "import"), ("export", "export"), ("cue_sheet", "cue-sheet")],
)
def test_a_project_dialog_opens_on_the_grid(
    editor: Client, project: models.Project, name: str, action: str
) -> None:
    url = reverse(f"cues:{name}", args=[project.pk])
    response = editor.get(url)
    assert response.status_code == 302
    assert response["Location"] == (
        reverse("cues:project", args=[project.pk]) + f"?do={action}"
    )
    # htmx still gets the dialog itself.
    shown = editor.get(url, headers=HX)
    assert shown.status_code == 200 and b"<html" not in shown.content


@pytest.mark.parametrize(
    ("name", "anchor"),
    [
        ("cue_history", "history-title"),
        ("cue_compare", "group-cue"),
        ("cue_review", "group-review"),
    ],
)
def test_a_cue_panel_opens_on_the_cue_page(
    editor: Client, project: models.Project, name: str, anchor: str
) -> None:
    cue = project.cues.order_by("pk").first()
    assert cue is not None
    url = reverse(f"cues:{name}", args=[cue.pk])
    response = editor.get(url)
    assert response.status_code == 302
    assert response["Location"] == (
        reverse("cues:cue", args=[cue.pk]) + f"#{anchor}"
    )
    assert editor.get(url, headers=HX).status_code == 200


def test_the_review_panel_keeps_its_version(
    editor: Client, project: models.Project
) -> None:
    cue = project.cues.order_by("pk").first()
    assert cue is not None
    url = reverse("cues:cue_review", args=[cue.pk])
    response = editor.get(url, {"version": "12"})
    assert response["Location"] == (
        reverse("cues:cue", args=[cue.pk]) + "?version=12#group-review"
    )
    # Anything else in ?version= is left behind.
    response = editor.get(url, {"version": "x"})
    assert "?" not in response["Location"]
