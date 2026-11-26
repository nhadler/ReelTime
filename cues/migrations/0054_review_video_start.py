"""A review link's Pre-Roll becomes the timecode its video starts at."""

from typing import Any

from django.db import migrations, models


def to_start(apps: Any, schema_editor: Any) -> None:
    """Sets Video Start to the current version's IN less the pre-roll.

    So the current version's comments keep their timecodes. Links
    without a pre-roll keep starting at each version's IN.
    """
    del schema_editor
    links = apps.get_model("cues", "ReviewLink").objects
    for link in links.filter(preroll__gt=0).select_related(
        "cue", "cue__current_version"
    ):
        version = link.cue.current_version
        start = version.tc_in if version and version.tc_in is not None else None
        if start is None:
            start = link.cue.tc_in or 0
        link.video_start = max(0, start - link.preroll)
        link.save(update_fields=["video_start"])


def to_preroll(apps: Any, schema_editor: Any) -> None:
    """Turns Video Start back into a pre-roll before the current IN."""
    del schema_editor
    links = apps.get_model("cues", "ReviewLink").objects
    for link in links.filter(video_start__isnull=False).select_related(
        "cue", "cue__current_version"
    ):
        version = link.cue.current_version
        start = version.tc_in if version and version.tc_in is not None else None
        if start is None:
            start = link.cue.tc_in or 0
        link.preroll = max(0, start - link.video_start)
        link.save(update_fields=["preroll"])


class Migration(migrations.Migration):
    dependencies = [
        ("cues", "0053_app_review_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="reviewlink",
            name="video_start",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(to_start, to_preroll),
        migrations.RemoveField(model_name="reviewlink", name="preroll"),
    ]
