"""The server's VAPID key, which signs every push.

From REELTIME_VAPID_PRIVATE_KEY (a PEM, or REELTIME_VAPID_PRIVATE_KEY_FILE)
when set, else made on first use and kept in the data directory as
vapid.pem. Devices subscribe with its public half; a new key means
every device has to turn notifications on again.
"""

import functools
import hashlib
import os
import pathlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from notifications import webpush

FILE_NAME = "vapid.pem"


def _pem(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _read(pem: bytes) -> ec.EllipticCurvePrivateKey:
    try:
        key = serialization.load_pem_private_key(pem, password=None)
    except ValueError as exc:
        raise ImproperlyConfigured("The VAPID key isn't a PEM key.") from exc
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(
        key.curve, ec.SECP256R1
    ):
        raise ImproperlyConfigured("The VAPID key must be a P-256 key.")
    return key


def _from_file(path: pathlib.Path) -> ec.EllipticCurvePrivateKey:
    """Reads the key file, making it first if there is none.

    Two processes starting at once both try to create it; the one that
    loses reads the winner's.
    """
    try:
        handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return _read(path.read_bytes())
    key = ec.generate_private_key(ec.SECP256R1())
    with os.fdopen(handle, "wb") as out:
        out.write(_pem(key))
    return key


@functools.cache
def private_key() -> ec.EllipticCurvePrivateKey:
    """The VAPID private key."""
    configured: str = settings.VAPID_PRIVATE_KEY
    if configured:
        return _read(configured.encode())
    directory = pathlib.Path(settings.DATA_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    return _from_file(directory / FILE_NAME)


def public_key() -> str:
    """The public half, base64url, for the browser's subscribe call."""
    return webpush.b64url(webpush.public_bytes(private_key().public_key()))


def fingerprint() -> str:
    """Names the key, so devices subscribed with another are recognised."""
    return hashlib.sha256(public_key().encode()).hexdigest()[:16]
