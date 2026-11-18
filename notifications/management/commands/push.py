"""manage.py push: sends notifications until stopped (bare metal).

Under Docker Compose the scheduler service does this as well as its
nightly job; on bare metal reeltime-push.service runs this.
"""

import signal
import threading
from types import FrameType
from typing import Any

from django.core.management.base import BaseCommand

from notifications import outbox


class Command(BaseCommand):
    """Sends queued notifications every few seconds until SIGTERM."""

    help = "Send queued push notifications until SIGTERM."

    def handle(self, *args: Any, **options: Any) -> None:
        """Loops until SIGTERM or SIGINT."""
        del args, options
        stop = threading.Event()

        def request_stop(signum: int, frame: FrameType | None) -> None:
            del signum, frame
            stop.set()

        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)
        self.stdout.write("Sending notifications.")
        outbox.run(stop)
        self.stdout.write("Stopped sending notifications.")
