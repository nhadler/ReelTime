"""Web Push: encrypting a message and signing the request (RFC 8291, 8292).

Pure functions over bytes and keys, so they're small-tested against the
RFC's own example. Sending is in notifications.outbox.
"""

import base64
import json
import os
import time
import urllib.parse

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# One record holds the whole message (RFC 8188's record size).
RECORD_SIZE = 4096
# A push service takes at least 4096 bytes of body; the header and the
# tag take 86 + 16 + 1 of them.
MAX_PAYLOAD = RECORD_SIZE - 103
# How long a VAPID token is good for; Apple refuses more than a day.
TOKEN_LIFETIME = 12 * 60 * 60


class PayloadTooLargeError(ValueError):
    """The message doesn't fit one push."""


def b64url(data: bytes) -> str:
    """Base64url without padding, as Web Push writes keys."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64url(text: str) -> bytes:
    """Reads base64url with or without padding.

    Raises:
        ValueError: It isn't base64url.
    """
    padded = text + "=" * (-len(text) % 4)
    try:
        return base64.b64decode(
            padded.encode("ascii"), altchars=b"-_", validate=True
        )
    except (UnicodeEncodeError, ValueError) as exc:
        raise ValueError("not base64url") from exc


def public_bytes(key: ec.EllipticCurvePublicKey) -> bytes:
    """A P-256 public key as the 65-byte uncompressed point."""
    return key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )


def load_public(point: bytes) -> ec.EllipticCurvePublicKey:
    """Reads a 65-byte uncompressed P-256 point.

    Raises:
        ValueError: It isn't one.
    """
    if len(point) != 65 or point[0] != 4:
        raise ValueError("not an uncompressed P-256 point")
    return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), point)


def _hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=length, salt=salt, info=info
    ).derive(ikm)


def encrypt(
    payload: bytes,
    receiver: bytes,
    auth: bytes,
    *,
    sender: ec.EllipticCurvePrivateKey | None = None,
    salt: bytes | None = None,
) -> bytes:
    """Encrypts a message for one browser (aes128gcm, one record).

    Args:
        payload: The message.
        receiver: The browser's public key (p256dh), 65 bytes.
        auth: The browser's auth secret, 16 bytes.
        sender: A one-off key pair; a new one by default (tests pass the
            RFC's).
        salt: 16 random bytes; new ones by default.

    Returns:
        The request body: the header, then the ciphertext.

    Raises:
        PayloadTooLargeError: The message is longer than MAX_PAYLOAD.
        ValueError: The receiver's key isn't a P-256 point.
    """
    if len(payload) > MAX_PAYLOAD:
        raise PayloadTooLargeError(f"{len(payload)} bytes")
    receiver_key = load_public(receiver)
    sender = sender or ec.generate_private_key(ec.SECP256R1())
    salt = salt if salt is not None else os.urandom(16)
    sender_public = public_bytes(sender.public_key())
    shared = sender.exchange(ec.ECDH(), receiver_key)
    ikm = _hkdf(
        auth, shared, b"WebPush: info\x00" + receiver + sender_public, 32
    )
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    # 0x02 marks the last (only) record.
    sealed = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    header = (
        salt
        + RECORD_SIZE.to_bytes(4, "big")
        + bytes([len(sender_public)])
        + sender_public
    )
    return header + sealed


def audience(endpoint: str) -> str:
    """The push service's origin, which a VAPID token is for."""
    parts = urllib.parse.urlsplit(endpoint)
    return f"{parts.scheme}://{parts.netloc}"


def vapid(
    key: ec.EllipticCurvePrivateKey,
    endpoint: str,
    subject: str,
    *,
    now: float | None = None,
) -> str:
    """The Authorization header for a push to `endpoint` (RFC 8292).

    Args:
        key: The server's VAPID private key.
        endpoint: Where the push goes.
        subject: How the push service can reach whoever runs the server:
            an https URL or a mailto: address.
        now: The time, in seconds since the epoch.
    """
    issued = int(time.time() if now is None else now)
    header = b64url(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    claims = b64url(
        json.dumps(
            {
                "aud": audience(endpoint),
                "exp": issued + TOKEN_LIFETIME,
                "sub": subject,
            },
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{claims}".encode("ascii")
    der = key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(der)
    signature = b64url(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    public = b64url(public_bytes(key.public_key()))
    return f"vapid t={header}.{claims}.{signature}, k={public}"
