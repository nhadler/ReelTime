"""Review comments about a stretch of the video."""

from django.test import Client
import pytest

from cues import models
from cues import timecode
from cues.services import history
from cues.services import review
from tests.medium.review.setup import guest
from tests.medium.review.setup import page_url
from tests.medium.review.setup import post

pytestmark = pytest.mark.django_db


def _tc(cue: models.Cue, frame: int) -> str:
    assert cue.tc_in is not None
    return timecode.format_timecode(cue.tc_in + frame, cue.project.rate)


def test_a_guest_comments_on_a_stretch(
    cue: models.Cue, link: models.ReviewLink
) -> None:
    client = guest()
    status, page = post(client, link, frame="24", end="72")
    assert status == 200
    note = models.ReviewComment.objects.get()
    assert (note.frame, note.end_frame) == (24, 72)
    # Listed with where it starts and ends; the page's script draws the
    # bar from both.
    (listed,) = review.comments(link, note.version)
    assert (listed.timecode, listed.until) == (_tc(cue, 24), _tc(cue, 72))
    assert f"{_tc(cue, 24)} – {_tc(cue, 72)}" in page
    assert 'data-frame="24" data-end="72"' in page
    assert "runs to" in client.get(page_url(link)).content.decode()


def test_a_stretch_of_one_frame_is_a_comment_at_it(
    cue: models.Cue, link: models.ReviewLink
) -> None:
    _, page = post(guest(), link, frame="24", end="24")
    note = models.ReviewComment.objects.get()
    assert (note.frame, note.end_frame) == (24, None)
    assert "data-end" not in page and " – " not in page
    (listed,) = review.comments(link, cue.versions.get())
    assert listed.until == ""


@pytest.mark.parametrize(
    ("end", "why"),
    [
        ("23", "ends before it starts"),
        ("0", "ends before it starts"),
        ("999999999", "in the video"),
        ("x", "in the video"),
        ("-1", "in the video"),
    ],
)
def test_an_end_before_the_start_or_out_of_range_is_refused(
    link: models.ReviewLink, end: str, why: str
) -> None:
    status, page = post(guest(), link, frame="24", end=end)
    assert status == 200
    assert why in page
    assert not models.ReviewComment.objects.exists()


def test_only_a_timed_note_has_an_end(
    cue: models.Cue, link: models.ReviewLink
) -> None:
    version = cue.versions.get()
    # On the whole version: nothing to end.
    post(guest(), link, frame="", end="72")
    whole = models.ReviewComment.objects.get()
    assert (whole.frame, whole.end_frame) == (None, None)
    # A reply is about its note.
    note = review.add_comment(
        version, name="Dana", body="Too busy", frame=24, user=None, end=72
    )
    post(guest(), link, parent=str(note.pk), frame="30", end="40")
    reply = models.ReviewComment.objects.get(parent=note)
    assert (reply.frame, reply.end_frame) == (None, None)


def test_a_deleted_stretch_comes_back_whole(
    cue: models.Cue, link: models.ReviewLink
) -> None:
    del link
    note = review.add_comment(
        cue.versions.get(),
        name="Dana",
        body="Too busy",
        frame=24,
        user=None,
        end=72,
    )
    review.delete_comment(note, None)
    deleted = models.ChangeSet.objects.first()
    assert deleted is not None
    history.undo(deleted)
    back = models.ReviewComment.objects.get()
    assert (back.frame, back.end_frame) == (24, 72)


def test_the_timeline_has_the_comments_marker(link: models.ReviewLink) -> None:
    client: Client = guest()
    page = client.get(page_url(link)).content.decode()
    assert 'id="review-draft"' in page and 'name="end"' in page
    # Nothing to place once comments are closed.
    link.comments_open = False
    link.save()
    closed = client.get(page_url(link)).content.decode()
    assert 'id="review-draft"' not in closed
