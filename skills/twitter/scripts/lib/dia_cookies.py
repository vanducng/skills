"""Decrypt the Dia browser's `Cookies` SQLite to extract auth_token + ct0 for x.com.

macOS-only. Reads the AES key from the `Dia Safe Storage` keychain entry,
PBKDF2-HMAC-SHA1(saltysalt, 1003, 16) → key, AES-CBC with 16-byte space IV.
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

KEYCHAIN_SERVICE = "Dia Safe Storage"
KEYCHAIN_ACCOUNT = "Dia"
SALT = b"saltysalt"
ITERATIONS = 1003
KEY_LEN = 16
IV = b" " * 16
DEFAULT_PROFILE = "Default"


class KeychainError(RuntimeError):
    """Failed to read the AES key from the macOS keychain."""


class BootstrapError(RuntimeError):
    """The needed cookies are not in Dia's store (probably not logged in)."""


class UnsupportedCookieFormat(RuntimeError):
    """Cookie blob has an unrecognized version prefix (e.g. v20 kernel-bound)."""


def _profile_cookies_path(profile: str) -> Path:
    return (
        Path.home()
        / "Library/Application Support/Dia/User Data"
        / profile
        / "Cookies"
    )


def get_aes_key() -> bytes:
    """Read the keychain password and derive the AES key."""
    try:
        proc = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-wa",
                KEYCHAIN_ACCOUNT,
                "-s",
                KEYCHAIN_SERVICE,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise KeychainError("`security` CLI not found — macOS only") from exc
    except subprocess.CalledProcessError as exc:
        raise KeychainError(
            "could not read 'Dia Safe Storage' keychain entry. "
            "macOS may show a 'Dia wants to use Safe Storage' prompt — "
            "click 'Always Allow' once to grant. "
            f"stderr: {exc.stderr.strip()}"
        ) from exc
    password = proc.stdout.strip().encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=KEY_LEN,
        salt=SALT,
        iterations=ITERATIONS,
    )
    return kdf.derive(password)


def read_cookies_db(profile: str = DEFAULT_PROFILE) -> list[tuple[str, bytes]]:
    """Return [(name, encrypted_value), ...] rows for x.com / twitter.com.

    Copies the live SQLite to a tempfile to avoid WAL lock contention with Dia.
    """
    src = _profile_cookies_path(profile)
    if not src.exists():
        raise FileNotFoundError(
            f"Dia cookies DB not found at {src} — wrong --profile? "
            f"(known profiles live under ~/Library/Application Support/Dia/User Data/)"
        )
    tmp = tempfile.NamedTemporaryFile(
        prefix="dia-cookies-", suffix=".sqlite", delete=False
    )
    tmp.close()
    try:
        shutil.copy2(src, tmp.name)
        # Some installs ship a -wal sidecar; copy it too if present so the
        # main DB read sees the latest committed state.
        for suffix in ("-wal", "-shm"):
            sidecar = src.with_name(src.name + suffix)
            if sidecar.exists():
                shutil.copy2(sidecar, tmp.name + suffix)
        conn = sqlite3.connect(tmp.name)
        try:
            cur = conn.execute(
                "SELECT name, encrypted_value FROM cookies "
                "WHERE host_key IN ('.x.com', '.twitter.com') "
                "AND name IN ('auth_token', 'ct0')"
            )
            return list(cur.fetchall())
        finally:
            conn.close()
    finally:
        for path in (tmp.name, tmp.name + "-wal", tmp.name + "-shm"):
            try:
                Path(path).unlink()
            except FileNotFoundError:
                pass


def decrypt(blob: bytes, key: bytes) -> str:
    """AES-CBC decrypt a Chromium-style v10/v11 cookie blob."""
    if blob[:3] in (b"v10", b"v11"):
        body = blob[3:]
    elif blob[:3] == b"v20":
        raise UnsupportedCookieFormat(
            "Dia cookie uses v20 (kernel-bound) format — not supported on this path. "
            "Use `twitter login` instead."
        )
    else:
        body = blob
    cipher = Cipher(algorithms.AES(key), modes.CBC(IV))
    decryptor = cipher.decryptor()
    raw = decryptor.update(body) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plain = unpadder.update(raw) + unpadder.finalize()
    # Chromium prefixes the value with a 32-byte SHA-256 of the host as of v10+
    # for integrity. Trim if present (heuristic: the real cookie value is
    # printable ASCII; the prefix is binary).
    if len(plain) > 32 and not plain[:1].isalnum():
        candidate = plain[32:]
        try:
            return candidate.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return plain.decode("utf-8")


def extract(profile: str = DEFAULT_PROFILE) -> dict:
    """End-to-end: keychain → AES key → SQLite read → decrypt → dict."""
    key = get_aes_key()
    rows = read_cookies_db(profile)
    if not rows:
        raise BootstrapError(
            "no auth_token / ct0 cookies for x.com found in Dia. "
            "Open x.com in Dia and log in, then rerun."
        )
    out: dict = {}
    for name, blob in rows:
        out[name] = decrypt(blob, key)
    missing = [k for k in ("auth_token", "ct0") if k not in out]
    if missing:
        raise BootstrapError(
            f"missing cookies after decrypt: {missing}. "
            "Log in to x.com in Dia, then rerun."
        )
    return out


__all__ = [
    "KeychainError",
    "BootstrapError",
    "UnsupportedCookieFormat",
    "get_aes_key",
    "read_cookies_db",
    "decrypt",
    "extract",
    "DEFAULT_PROFILE",
]
