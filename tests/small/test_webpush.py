"""Web Push encryption and VAPID signing (notifications.webpush)."""

import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import utils
import pytest

from notifications import webpush
from tests.fakes import push_browser

# RFC 8291, Appendix A.
PLAINTEXT = b"When I grow up, I want to be a watermelon"
SENDER_PRIVATE = "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"
SENDER_PUBLIC = (
    "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8"
    "wEqKK6PBru3jl7A8"
)
RECEIVER_PUBLIC = (
    "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8p"
    "ZGH6SRpkNtoIAiw4"
)
AUTH = "BTBZMqHH6r4Tts7J_aSIgg"
SALT = "DGv6ra1nlYgDCS1FRnbzlw"
MESSAGE = (
    "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZII"
    "gDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXzt"
    "LVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN"
)


def _sender() -> ec.EllipticCurvePrivateKey:
    secret = int.from_bytes(webpush.unb64url(SENDER_PRIVATE), "big")
    return ec.derive_private_key(secret, ec.SECP256R1())


def test_the_rfc_example_encrypts_to_the_rfc_message() -> None:
    sender = _sender()
    assert webpush.b64url(webpush.public_bytes(sender.public_key())) == (
        SENDER_PUBLIC
    )
    body = webpush.encrypt(
        PLAINTEXT,
        webpush.unb64url(RECEIVER_PUBLIC),
        webpush.unb64url(AUTH),
        sender=sender,
        salt=webpush.unb64url(SALT),
    )
    assert webpush.b64url(body) == MESSAGE


def test_a_browser_reads_what_was_encrypted_for_it() -> None:
    browser = push_browser.new()
    body = webpush.encrypt(
        b"hello", webpush.unb64url(browser.p256dh), browser.auth
    )
    assert browser.read(body) == b"hello"
    again = webpush.encrypt(
        b"hello", webpush.unb64url(browser.p256dh), browser.auth
    )
    assert again != body  # a new salt and key each time


def test_a_message_too_long_for_one_push_is_refused() -> None:
    browser = push_browser.new()
    receiver = webpush.unb64url(browser.p256dh)
    assert webpush.encrypt(b"x" * webpush.MAX_PAYLOAD, receiver, browser.auth)
    with pytest.raises(webpush.PayloadTooLargeError):
        webpush.encrypt(
            b"x" * (webpush.MAX_PAYLOAD + 1), receiver, browser.auth
        )


@pytest.mark.parametrize("text", ["not base64!", "é"])
def test_unreadable_base64url_is_refused(text: str) -> None:
    with pytest.raises(ValueError, match="not base64url"):
        webpush.unb64url(text)


def test_base64url_reads_with_or_without_padding() -> None:
    assert webpush.unb64url("YQ") == webpush.unb64url("YQ==") == b"a"


@pytest.mark.parametrize(
    "point", [b"", b"\x04" + b"\x00" * 63, b"\x03" + b"\x00" * 64]
)
def test_a_key_that_isnt_an_uncompressed_point_is_refused(point: bytes) -> None:
    with pytest.raises(ValueError):
        webpush.load_public(point)


def test_a_point_off_the_curve_is_refused() -> None:
    with pytest.raises(ValueError):
        webpush.load_public(b"\x04" + b"\x01" * 64)


def test_the_vapid_header_is_a_signed_token_for_the_push_service() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    header = webpush.vapid(
        key,
        "https://web.push.apple.com/QAbc?x=1",
        "https://reeltime.example",
        now=1_000_000,
    )
    token, public = header.removeprefix("vapid t=").split(", k=")
    assert webpush.unb64url(public) == webpush.public_bytes(key.public_key())
    head, claims, signature = token.split(".")
    assert json.loads(webpush.unb64url(head)) == {"typ": "JWT", "alg": "ES256"}
    assert json.loads(webpush.unb64url(claims)) == {
        "aud": "https://web.push.apple.com",
        "exp": 1_000_000 + 12 * 60 * 60,
        "sub": "https://reeltime.example",
    }
    raw = webpush.unb64url(signature)
    assert len(raw) == 64
    der = utils.encode_dss_signature(
        int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
    )
    key.public_key().verify(
        der, f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256())
    )
    with pytest.raises(InvalidSignature):
        key.public_key().verify(
            der, f"{head}.x{claims}".encode(), ec.ECDSA(hashes.SHA256())
        )


def test_the_vapid_token_uses_the_clock_by_default() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    token = webpush.vapid(key, "https://fcm.googleapis.com/a", "mailto:a@b.c")
    claims = json.loads(webpush.unb64url(token.split(".")[1]))
    assert claims["exp"] > 1_700_000_000
