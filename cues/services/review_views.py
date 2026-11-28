"""Who watched a review page, and how much of it.

The page starts a visit when it opens and reports back while it stays
open: how long the video or audio has played, the furthest frame
reached, each second of the video as it plays (so a stretch watched
again counts again), and where the video was paused. A reload within
half an hour carries on the same visit. Guests are known by the name
they gave to watch; nothing else about them is kept.

Used by the review page (cues.views.review) and the cue page's Review
section.
"""

from collections.abc import Iterator, Sequence
import dataclasses
import datetime
import secrets

from django.utils import timezone

from cues import models
from cues import timecode
from cues.services import review
from cues.services.summaries import clock
from notifications import outbox

# A reload this soon after the last sign of life is the same visit.
SAME_VISIT = datetime.timedelta(minutes=30)
# A version keeps its newest visits; older ones are dropped.
MAX_VIEWS = 200
# How far reported play time may run ahead of the visit's own length:
# the page's clock and the server's needn't agree to the second.
_SLACK = 30
# Seconds of video counted at most: four hours.
MAX_SECONDS = 4 * 60 * 60
# Seconds one report may add; the page reports every 15 seconds.
MAX_REPORTED = 1200
# Times one second can count, and pauses one visit keeps.
MAX_PLAYS = 999
MAX_PAUSES = 50
# The strips' width in SVG user units.
STRIP_WIDTH = 1000


def new_browser() -> str:
    """An id for a browser's session, to tell its visits apart."""
    return secrets.token_hex(16)


def start(
    version: models.CueVersion,
    *,
    name: str,
    member: bool,
    browser: str,
    viewer: int | None = None,
) -> models.ReviewView:
    """Starts a visit, or carries on this browser's recent one.

    A new visit tells whoever wants to know (notifications), except the
    viewer themself (`viewer`, their user id).
    """
    now = timezone.now()
    recent = (
        version.review_views.filter(
            browser=browser, last_seen_at__gte=now - SAME_VISIT
        )
        .order_by("-last_seen_at")
        .first()
    )
    if recent is not None:
        recent.name = name
        recent.last_seen_at = now
        recent.save(update_fields=["name", "last_seen_at"])
        return recent
    view = models.ReviewView.objects.create(
        version=version,
        key=secrets.token_hex(16),
        browser=browser,
        name=name,
        member=member,
        started_at=now,
        last_seen_at=now,
    )
    keep = list(version.review_views.values_list("pk", flat=True)[:MAX_VIEWS])
    version.review_views.exclude(pk__in=keep).delete()
    cue = version.cue
    outbox.opened(
        project=cue.project.title,
        about=f"cue-{cue.pk}",
        label=f"{cue.number} {version.label}",
        name=name,
        member=member,
        viewer=viewer,
        path=review.cue_path(version),
    )
    return view


def report(  # pylint: disable=too-many-arguments
    cue: models.Cue,
    key: str,
    *,
    played: int,
    furthest: int | None,
    seconds: Sequence[int] = (),
    pauses: Sequence[int] = (),
    length: int | None = None,
) -> bool:
    """Records what a visit's page says has happened since it last said.

    Play time and the furthest frame only go up, and play time can't
    pass the time since the visit started. `seconds` are the seconds of
    the video that started playing since the last report, each counted
    once more; `pauses` are the frames it was paused at. Anything past
    the video's end (or four hours, before its length is known) is left
    out.

    Returns:
        Whether the key is a visit to one of this cue's versions.
    """
    view = models.ReviewView.objects.filter(key=key, version__cue=cue).first()
    if view is None:
        return False
    now = timezone.now()
    open_for = int((now - view.started_at).total_seconds()) + _SLACK
    view.played = max(view.played, min(max(played, 0), open_for))
    rate = cue.project.rate
    last = timecode.max_frames(rate)
    if furthest is not None and 0 <= furthest <= last:
        view.furthest = max(view.furthest or 0, furthest)
    if length is not None and 0 < length <= MAX_SECONDS:
        view.length = length
    end = view.length + 1 if view.length else MAX_SECONDS
    counts = list(view.seconds)
    for second in seconds[:MAX_REPORTED]:
        if 0 <= second < end:
            counts.extend([0] * (second + 1 - len(counts)))
            counts[second] = min(counts[second] + 1, MAX_PLAYS)
    view.seconds = counts
    room = MAX_PAUSES - len(view.pauses)
    view.pauses = (
        list(view.pauses)
        + [
            frame
            for frame in pauses
            if 0 <= frame <= min(last, end * rate.nominal)
        ][: max(room, 0)]
    )
    view.last_seen_at = now
    view.save(
        update_fields=[
            "played",
            "furthest",
            "length",
            "seconds",
            "pauses",
            "last_seen_at",
        ]
    )
    return True


@dataclasses.dataclass(frozen=True)
class Bar:
    """A run of seconds played the same number of times, on a strip.

    Attributes:
        x: Where it starts, 0 to STRIP_WIDTH.
        width: How wide it is.
        level: 1 for once, 2 for twice, 3 for three times, 4 for more.
    """

    x: float
    width: float
    level: int


@dataclasses.dataclass(frozen=True)
class Strip:
    """Where the video played, and how often, drawn along its length.

    Attributes:
        bars: The stretches that played, by how often.
        pauses: Where it was paused, 0 to STRIP_WIDTH.
    """

    bars: tuple[Bar, ...]
    pauses: tuple[float, ...]


def strip(
    counts: Sequence[int],
    pauses: Sequence[float],
    length: int | None,
    *,
    relative: bool = False,
) -> Strip | None:
    """A strip of plays along a video `length` seconds long.

    `pauses` are in seconds. Levels are the play counts (four meaning
    four or more), or with `relative` each count's share of the highest,
    in quarters, for plays added up over many visits. None when nothing
    played and nothing was paused.
    """
    seconds = max(length or 0, len(counts))
    if not seconds or not (any(counts) or pauses):
        return None
    scale = STRIP_WIDTH / seconds
    top = max(counts, default=0)
    levels = [
        -(-4 * count // top) if relative else min(count, 4) for count in counts
    ]
    bars: list[Bar] = []
    for first, stop, level in _runs(levels, 1):
        bars.append(Bar(first * scale, (stop - first) * scale, level))
    return Strip(
        tuple(bars),
        tuple(min(at, seconds) * scale for at in pauses),
    )


def _runs(counts: Sequence[int], least: int) -> Iterator[tuple[int, int, int]]:
    """Runs of seconds counted at least `least` times.

    Yields (first second, the second after the last, count) for each run
    of seconds with the same count, merging nothing across a change.
    """
    first = 0
    for second in range(1, len(counts) + 1):
        if second == len(counts) or counts[second] != counts[first]:
            if counts[first] >= least:
                yield first, second, counts[first]
            first = second


def _replays(
    counts: Sequence[int], least: int = 2
) -> list[tuple[int, int, int]]:
    """Stretches counted at least `least` times, highest first.

    Each is (first second, the second after the last, the highest count
    in it). Neighbouring seconds that each count make one stretch,
    whatever their counts. By default, the stretches played again.
    """
    found = []
    first = None
    for second, count in enumerate([*counts, 0]):
        if count >= least and first is None:
            first = second
        elif count < least and first is not None:
            found.append((first, second, max(counts[first:second])))
            first = None
    return sorted(found, key=lambda run: (-run[2], -(run[1] - run[0])))


def _seen(counts: Sequence[int], length: int | None) -> str:
    """The share of the video played at least once, as a percentage."""
    if not length or not counts:
        return ""
    seen = sum(1 for count in counts[:length] if count)
    return f"{min(100, round(100 * seen / length))}%"


@dataclasses.dataclass(frozen=True)
class Visit:
    """A visit as the cue page lists it.

    Attributes:
        view: The visit.
        played: How long the video or audio played, as m:ss.
        open_for: How long the page was open, as m:ss.
        reached: The timecode of the furthest frame reached, or "".
        seen: How much of the video played at least once, as "85%", or
            "" before the page said how long the video is.
        strip: Where the video played and was paused, or None.
        replayed: The stretches played more than once, most first, as
            "1:00:10:00–1:00:14:00 ×3"; at most three.
        paused: The timecodes it was paused at, in order; at most five.
    """

    view: models.ReviewView
    played: str
    open_for: str
    reached: str
    seen: str = ""
    strip: Strip | None = None
    replayed: tuple[str, ...] = ()
    paused: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class Watched:
    """Every visit to a version, added up.

    Attributes:
        strip: Plays from every visit, along the video, shaded against
            the most played second; None before any.
        replayed: The stretches watched again most across visits, each
            as its timecodes and who did and the most times they played
            it: ("1:00:10:00–1:00:14:00", "Dana ×4, Sam ×2"); at most
            three.
    """

    strip: Strip | None
    replayed: tuple[tuple[str, str], ...]


class _Clock:
    """Turns seconds and frames of the video into the picture's timecode."""

    def __init__(self, rate: timecode.Rate, base: int) -> None:
        self.rate = rate
        self.base = base
        self.last = timecode.max_frames(rate)

    def frame(self, frame: int) -> str:
        """The timecode `frame` frames into the video."""
        return timecode.format_timecode(
            min(self.base + frame, self.last), self.rate
        )

    def span(self, first: int, stop: int) -> str:
        """Seconds `first` up to `stop` of the video, as two timecodes."""
        nominal = self.rate.nominal
        return f"{self.frame(first * nominal)}–{self.frame(stop * nominal)}"


def visits(
    link: models.ReviewLink | None, version: models.CueVersion
) -> list[Visit]:
    """A version's visits, newest first."""
    rate = version.cue.project.rate
    clock_ = _Clock(rate, review.first_frame(link, version))
    found = []
    for view in version.review_views.all():
        counts = list(view.seconds)
        found.append(
            Visit(
                view,
                clock(view.played),
                clock(
                    int((view.last_seen_at - view.started_at).total_seconds())
                ),
                "" if view.furthest is None else clock_.frame(view.furthest),
                _seen(counts, view.length),
                strip(
                    counts,
                    [frame / rate.nominal for frame in view.pauses],
                    view.length,
                ),
                tuple(
                    f"{clock_.span(first, stop)} ×{times}"
                    for first, stop, times in _replays(counts)[:3]
                ),
                tuple(clock_.frame(frame) for frame in view.pauses[:5]),
            )
        )
    return found


def watched(
    link: models.ReviewLink | None, version: models.CueVersion
) -> Watched:
    """Every visit to a version added up: what was watched again most."""
    rate = version.cue.project.rate
    clock_ = _Clock(rate, review.first_frame(link, version))
    views = list(version.review_views.all())
    width = max((len(view.seconds) for view in views), default=0)
    total = [0] * width
    # Plays beyond each visit's first, added up: where people went back.
    again = [0] * width
    for view in views:
        for second, count in enumerate(view.seconds):
            total[second] += count
            again[second] += max(count - 1, 0)
    length = max((view.length or 0 for view in views), default=0)
    pauses = [frame / rate.nominal for view in views for frame in view.pauses]
    replayed = []
    for first, stop, _ in _replays(again, least=1)[:3]:
        who = sorted(
            (
                (max(view.seconds[first:stop]), view.name)
                for view in views
                if max(view.seconds[first:stop], default=0) >= 2
            ),
            key=lambda each: (-each[0], each[1]),
        )
        replayed.append(
            (
                clock_.span(first, stop),
                ", ".join(f"{name} ×{times}" for times, name in who),
            )
        )
    return Watched(
        strip(total, pauses, length or None, relative=True), tuple(replayed)
    )
