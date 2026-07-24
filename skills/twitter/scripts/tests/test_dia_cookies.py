"""Unit tests for dia_cookies.decrypt - golden-vector round-trip.

Encrypts a known plaintext with the same params dia_cookies.decrypt expects
(saltysalt + PBKDF2-HMAC-SHA1 × 1003, AES-128-CBC, 16-byte space IV, v10
prefix) and verifies the round-trip.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from lib import dia_cookies


def _derive_key(password: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=dia_cookies.KEY_LEN,
        salt=dia_cookies.SALT,
        iterations=dia_cookies.ITERATIONS,
    )
    return kdf.derive(password)


def _encrypt(plain: str, key: bytes, *, host_prefix: bool = False, version: bytes = b"v10") -> bytes:
    body = plain.encode()
    if host_prefix:
        body = (b"\x00" * 32) + body
    padder = padding.PKCS7(128).padder()
    padded = padder.update(body) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(dia_cookies.IV))
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return version + encrypted


def test_decrypt_roundtrip_v10_no_prefix():
    key = _derive_key(b"test-password")
    blob = _encrypt("hello-cookie-value", key)
    assert dia_cookies.decrypt(blob, key) == "hello-cookie-value"


def test_decrypt_roundtrip_v11_no_prefix():
    key = _derive_key(b"different-password")
    blob = _encrypt("auth_token_value_123", key, version=b"v11")
    assert dia_cookies.decrypt(blob, key) == "auth_token_value_123"


def test_decrypt_strips_32_byte_host_prefix():
    key = _derive_key(b"pw")
    blob = _encrypt("real-cookie", key, host_prefix=True)
    assert dia_cookies.decrypt(blob, key) == "real-cookie"


def test_decrypt_v20_raises_unsupported():
    key = _derive_key(b"pw")
    blob = b"v20" + b"\x00" * 16
    with pytest.raises(dia_cookies.UnsupportedCookieFormat):
        dia_cookies.decrypt(blob, key)


def test_decrypt_handles_long_token_typical_for_ct0():
    key = _derive_key(b"pw")
    ct0 = "a" * 160
    blob = _encrypt(ct0, key, host_prefix=True)
    assert dia_cookies.decrypt(blob, key) == ct0
