"""Project cards keep their titles readable in a narrow window."""

from typing import Any

from playwright.sync_api import expect
import pytest

from cues.services import demo
from tests.large.e2e.conftest import SignInAs

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


@pytest.mark.parametrize("width", [645, 660, 739, 900, 961, 1280])
def test_a_project_title_isnt_cut_off(
    page: Any,
    app: str,
    sign_in_as: SignInAs,
    csp_violations: list[str],
    width: int,
) -> None:
    del csp_violations
    demo.build_demo()
    sign_in_as("Casey Composer")
    page.set_viewport_size({"width": width, "height": 700})
    page.goto(f"{app}/projects/")
    title = page.locator(".project__title").first
    expect(title).to_be_visible()
    assert title.evaluate("e => e.scrollWidth <= e.clientWidth")
    assert page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )
