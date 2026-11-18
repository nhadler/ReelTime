"""Notifications in a real browser: the page, the service worker, sign-out.

Headless Chromium has no push service, so a real subscription is checked
by hand on a phone; this checks everything up to it.
"""

from typing import Any

from playwright.sync_api import expect
import pytest

from tests.large.e2e.conftest import Check
from tests.large.e2e.conftest import SignInAs

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


def test_the_page_offers_to_turn_on_and_the_worker_registers(
    page: Any,
    app: str,
    sign_in_as: SignInAs,
    axe: Check,
    csp_violations: list[str],
) -> None:
    del csp_violations
    sign_in_as("Casey Composer")
    page.locator(".profile__button").click()
    page.get_by_role("link", name="Notifications").click()
    page.wait_for_url(f"{app}/notifications/")
    expect(
        page.get_by_role("button", name="Turn On for This Device")
    ).to_be_visible()
    expect(page.get_by_text("Add ReelTime to the Home Screen")).to_be_hidden()
    expect(page.get_by_text("No devices yet.")).to_be_visible()
    axe("notifications")

    manifest = page.evaluate(
        "fetch(document.querySelector('link[rel=manifest]').href)"
        ".then((r) => r.json())"
    )
    assert manifest["display"] == "standalone"

    scope = page.evaluate(
        """async () => {
          const registration = await navigator.serviceWorker.register(
              '/sw.js', {scope: '/'});
          await navigator.serviceWorker.ready;
          return registration.scope;
        }"""
    )
    assert scope == f"{app}/"

    page.get_by_label("Review Links Opened").uncheck()
    page.get_by_role("button", name="Save").click()
    expect(page.get_by_text("Saved.")).to_be_visible()
    expect(page.get_by_label("Review Links Opened")).not_to_be_checked()
    expect(page.get_by_label("Comments and Replies")).to_be_checked()

    # Signing out still works with a service worker and no subscription.
    page.locator(".profile__button").click()
    page.get_by_role("button", name="Sign Out").click()
    page.wait_for_url(f"{app}/auth/**")
