"""The Notifications page, turning a browser on and off, and the web app files.

The manifest and the service worker are public: browsers fetch the
manifest without cookies, and a service worker's update check can't
follow the sign-in redirect. Neither holds anything about anyone.
"""

from collections.abc import Callable
import functools
import json
import pathlib
from typing import Any, TypeVar, cast

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from accounts import audit
from accounts.authz import role_required
from accounts.models import AuditAction
from accounts.models import Role
from accounts.models import User
from notifications import devices
from notifications import keys
from notifications import outbox

ViewT = TypeVar("ViewT", bound=Callable[..., Any])

_WORKER = pathlib.Path(__file__).with_name("service_worker.js")

# Per signed-in user: turning on, off and testing.
_limit: Callable[[ViewT], ViewT] = cast(
    Callable[[ViewT], ViewT],
    ratelimit(
        group="notifications",
        key="user",
        rate="30/m",
        method="POST",
        block=True,
    ),
)


def _user(request: HttpRequest) -> User:
    # Signed in: the middleware sends anyone else to the sign-in page.
    return cast(User, request.user)


def _act(request: HttpRequest, user: User) -> None:
    action = request.POST.get("action", "")
    if action == "remove":
        if devices.remove(user, request.POST.get("device", "")):
            audit.record(
                AuditAction.NOTIFICATIONS_OFF, request=request, user=user
            )
            messages.success(request, "Device removed.")
    elif action == "test":
        device = user.push_devices.filter(
            pk=_number(request.POST.get("device", ""))
        ).first()
        if device is not None:
            outbox.test(device)
            messages.success(request, "Test sent: it shows in a few seconds.")
    elif action == "choose":
        user.notify_comments = "comments" in request.POST
        user.notify_opens = "opens" in request.POST
        user.save(update_fields=["notify_comments", "notify_opens"])
        messages.success(request, "Saved.")


def _number(text: str) -> int:
    return int(text) if text.isdigit() else 0


@role_required(Role.VIEWER)
@require_http_methods(["GET", "POST"])
@_limit
def page(request: HttpRequest) -> HttpResponse:
    """Your devices and what you're told about (any role)."""
    user = _user(request)
    if request.method == "POST":
        _act(request, user)
        return redirect("notifications:page")
    return render(
        request,
        "notifications/page.html",
        {
            "nav": "",
            "devices": list(user.push_devices.all()),
            "config": {
                "publicKey": keys.public_key(),
                "subscribeUrl": reverse("notifications:subscribe"),
            },
        },
    )


def _json(request: HttpRequest) -> dict[str, Any]:
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


@role_required(Role.VIEWER)
@require_POST
@_limit
def subscribe(request: HttpRequest) -> JsonResponse:
    """Keeps this browser's subscription (from the page's script)."""
    user = _user(request)
    data = _json(request)
    found = data.get("keys")
    given = found if isinstance(found, dict) else {}
    try:
        device = devices.subscribe(
            user, data.get("endpoint"), given.get("p256dh"), given.get("auth")
        )
    except devices.DeviceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    audit.record(AuditAction.NOTIFICATIONS_ON, request=request, user=user)
    return JsonResponse({"id": device.pk})


@role_required(Role.VIEWER)
@require_POST
@_limit
def forget(request: HttpRequest) -> HttpResponse:
    """Removes this browser's device (signing out)."""
    user = _user(request)
    if devices.forget(user, _json(request).get("endpoint")):
        audit.record(AuditAction.NOTIFICATIONS_OFF, request=request, user=user)
    return HttpResponse(status=204)


@login_not_required
@require_GET
def manifest(request: HttpRequest) -> JsonResponse:
    """The web app manifest: ReelTime on a Home Screen."""
    del request
    # The manifest's own type, not application/json, which pylint expects.
    response = JsonResponse(  # pylint: disable=redundant-content-type-for-json-response
        {
            "name": "ReelTime",
            "short_name": "ReelTime",
            "id": "/",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#171b22",
            "theme_color": "#171b22",
            "icons": [
                {
                    "src": static(f"notifications/icon-{size}.png"),
                    "sizes": f"{size}x{size}",
                    "type": "image/png",
                    "purpose": "any",
                }
                for size in (192, 512)
            ]
            + [
                {
                    "src": static("notifications/icon-maskable-512.png"),
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                }
            ],
        },
        content_type="application/manifest+json",
    )
    response["Cache-Control"] = "no-cache"
    return response


@functools.cache
def _worker() -> bytes:
    return _WORKER.read_bytes()


@login_not_required
@require_GET
def service_worker(request: HttpRequest) -> HttpResponse:
    """The service worker: shows notifications and opens their page."""
    del request
    response = HttpResponse(_worker(), content_type="text/javascript")
    # Browsers check it for updates; never let a cache answer for it.
    response["Cache-Control"] = "no-cache"
    return response
