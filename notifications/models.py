"""Devices that get notifications, and the messages waiting for them.

Not in backups (notifications isn't one of the backed-up apps): a device
belongs to one browser and to this server's VAPID key.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class PushDevice(models.Model):
    """A browser that turned notifications on, and the keys to reach it."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_devices",
    )
    # The push service's address for this browser (an https URL).
    endpoint = models.URLField(max_length=1024, unique=True)
    # The browser's public key (65 bytes) and auth secret (16), base64url.
    p256dh = models.CharField(max_length=100)
    auth = models.CharField(max_length=40)
    # Which VAPID key it subscribed with (notifications.keys.fingerprint).
    key = models.CharField(max_length=16)
    created_at = models.DateTimeField(default=timezone.now)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    # Refusals in a row; reset by a delivery.
    failures = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "notification device"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        """Returns whose device it is."""
        return f"Notification device of {self.user}"


class Kind(models.TextChoices):
    """What a message is about; each user chooses which they get."""

    COMMENT = "comment", "Comments and Replies"
    OPEN = "open", "Links Opened"
    TEST = "test", "Test"


class PushMessage(models.Model):
    """One notification for one device: waiting, or sent (kept a day).

    Messages about the same thing (`about`) close together become one:
    `count` says how many it stands for.
    """

    device = models.ForeignKey(
        PushDevice, on_delete=models.CASCADE, related_name="messages"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    # What it's about, e.g. "cue-12": one notification per thing on the
    # phone, and what close-together messages are merged by.
    about = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=400)
    # The page a tap opens, on this server.
    path = models.CharField(max_length=200)
    count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    next_try_at = models.DateTimeField(default=timezone.now, db_index=True)
    tries = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "notification"
        indexes = [models.Index(fields=["device", "about", "kind"])]

    def __str__(self) -> str:
        """Returns its title and text."""
        return f"{self.title}: {self.body}"
