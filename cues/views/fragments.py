"""Pieces of a page that htmx loads, and where to send a direct visit.

A dialog or panel's address opened on its own (a reload, a bookmark, a
pasted link) would show the bare fragment, unstyled. Its view sends the
page it belongs to instead.
"""

from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.urls import reverse


def typed_in(request: HttpRequest) -> bool:
    """True for a GET that htmx didn't make."""
    return (
        request.method == "GET" and request.headers.get("HX-Request") != "true"
    )


def to_grid(project_id: int, action: str) -> HttpResponseRedirect:
    """The cue overview, which opens the dialog named by ?do= (grid.js)."""
    url = reverse("cues:project", args=[project_id])
    return HttpResponseRedirect(f"{url}?do={action}")


def to_cue(cue_id: int, anchor: str, version: str = "") -> HttpResponseRedirect:
    """The cue page at one of its sections."""
    url = reverse("cues:cue", args=[cue_id])
    query = f"?version={version}" if version.isdigit() else ""
    return HttpResponseRedirect(f"{url}{query}#{anchor}")
