"""The server's VAPID key (notifications.keys)."""

from collections.abc import Iterator
import pathlib
import stat

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
import pytest

from notifications import keys
from notifications import webpush
from tests.medium.notifications.conftest import PEM


@pytest.fixture(name="data_dir")
def fixture_data_dir(tmp_path: pathlib.Path) -> Iterator[pathlib.Path]:
    keys.private_key.cache_clear()
    with override_settings(VAPID_PRIVATE_KEY="", DATA_DIR=tmp_path / "data"):
        yield tmp_path / "data"
    keys.private_key.cache_clear()


def test_the_configured_key_is_used() -> None:
    configured = serialization.load_pem_private_key(PEM.encode(), None)
    assert keys.public_key() == webpush.b64url(
        webpush.public_bytes(configured.public_key())  # type: ignore[arg-type]
    )
    assert len(keys.fingerprint()) == 16


def test_without_one_a_key_is_made_once_and_kept(
    data_dir: pathlib.Path,
) -> None:
    first = keys.public_key()
    path = data_dir / "vapid.pem"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    keys.private_key.cache_clear()
    assert keys.public_key() == first


def test_a_key_another_process_made_first_is_read(
    data_dir: pathlib.Path,
) -> None:
    data_dir.mkdir()
    (data_dir / "vapid.pem").write_text(PEM)
    with override_settings(VAPID_PRIVATE_KEY=PEM):
        keys.private_key.cache_clear()
        expected = keys.public_key()
    keys.private_key.cache_clear()
    assert keys.public_key() == expected


def test_a_key_that_isnt_a_pem_is_refused() -> None:
    keys.private_key.cache_clear()
    with override_settings(VAPID_PRIVATE_KEY="nonsense"):
        with pytest.raises(ImproperlyConfigured, match="isn't a PEM"):
            keys.private_key()


def test_a_key_on_another_curve_is_refused() -> None:
    other = ec.generate_private_key(ec.SECP384R1()).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    keys.private_key.cache_clear()
    with override_settings(VAPID_PRIVATE_KEY=other.decode()):
        with pytest.raises(ImproperlyConfigured, match="P-256"):
            keys.private_key()
