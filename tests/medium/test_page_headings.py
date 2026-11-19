"""Each project page has one h1: its own title, or the project's name."""

from collections.abc import Callable
import re

from django.test import Client
from django.urls import reverse
import pytest

from accounts.models import Role
from cues import models
from cues.services import demo

pytestmark = pytest.mark.django_db


@pytest.fixture(name="project")
def fixture_project() -> models.Project:
    return demo.build_demo().project


def _h1s(html: str) -> list[str]:
    return [
        re.sub(r"<[^>]+>", "", found).strip()
        for found in re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    ]


def test_the_cue_overview_is_titled_by_the_project(
    role_client: Callable[[Role], Client], project: models.Project
) -> None:
    editor = role_client(Role.EDITOR)
    html = editor.get(
        reverse("cues:project", args=[project.pk])
    ).content.decode()
    assert _h1s(html) == [project.title]
    # The header htmx brings back after a change keeps it.
    header = editor.get(
        reverse("cues:project_header", args=[project.pk])
    ).content.decode()
    assert _h1s(header) == [project.title]


@pytest.mark.parametrize(
    ("name", "title"),
    [
        ("cues:conform", "Conform"),
        ("cues:activity", "Activity"),
        ("cues:trash", "Trash"),
        ("cues:settings", "General"),
    ],
)
def test_a_project_page_is_titled_by_itself(
    role_client: Callable[[Role], Client],
    project: models.Project,
    name: str,
    title: str,
) -> None:
    html = (
        role_client(Role.EDITOR)
        .get(reverse(name, args=[project.pk]))
        .content.decode()
    )
    assert _h1s(html) == [title]
    assert '<p class="project-bar__title">' in html
