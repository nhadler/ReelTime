"""Fixtures for notifications: a fixed server key and a fake push service."""

from collections.abc import Iterator

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.test import override_settings
import pytest
import responses

from notifications import keys
from tests.fakes import push_browser

_KEY = ec.generate_private_key(ec.SECP256R1())
PEM = _KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()


@pytest.fixture(autouse=True)
def _server_key() -> Iterator[None]:
    keys.private_key.cache_clear()
    with override_settings(VAPID_PRIVATE_KEY=PEM):
        yield
    keys.private_key.cache_clear()


@pytest.fixture(name="push_service")
def fixture_push_service() -> Iterator[responses.RequestsMock]:
    """Catches every POST to the fake endpoint; tests set the answer."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


@pytest.fixture(name="browser")
def fixture_browser() -> push_browser.Browser:
    return push_browser.new()
