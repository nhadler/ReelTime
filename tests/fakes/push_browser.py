"""A browser's side of Web Push, for tests: keys, and reading a push."""

import dataclasses
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from notifications import webpush

ENDPOINT = "https://web.push.apple.com/QAbc123"


@dataclasses.dataclass
class Browser:
    """A subscribed browser: its key pair and auth secret."""

    key: ec.EllipticCurvePrivateKey
    auth: bytes
    endpoint: str = ENDPOINT

    @property
    def p256dh(self) -> str:
        return webpush.b64url(webpush.public_bytes(self.key.public_key()))

    @property
    def secret(self) -> str:
        return webpush.b64url(self.auth)

    def subscription(self) -> dict[str, object]:
        """What PushSubscription.toJSON() gives."""
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh, "auth": self.secret},
        }

    def read(self, body: bytes | str | None) -> bytes:
        """Decrypts a push body (aes128gcm, one record)."""
        assert isinstance(body, bytes)
        salt = body[:16]
        length = body[20]
        sender = body[21 : 21 + length]
        sealed = body[21 + length :]
        shared = self.key.exchange(ec.ECDH(), webpush.load_public(sender))
        receiver = webpush.public_bytes(self.key.public_key())

        def hkdf(salt_: bytes, ikm: bytes, info: bytes, size: int) -> bytes:
            return HKDF(
                algorithm=hashes.SHA256(), length=size, salt=salt_, info=info
            ).derive(ikm)

        ikm = hkdf(
            self.auth, shared, b"WebPush: info\x00" + receiver + sender, 32
        )
        cek = hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
        nonce = hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
        plain = AESGCM(cek).decrypt(nonce, sealed, None)
        assert plain.endswith(b"\x02")
        return plain[:-1]


def new(endpoint: str = ENDPOINT) -> Browser:
    """A browser with fresh keys."""
    return Browser(
        ec.generate_private_key(ec.SECP256R1()), os.urandom(16), endpoint
    )
