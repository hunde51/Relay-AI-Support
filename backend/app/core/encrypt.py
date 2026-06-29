"""Symmetric encryption for OAuth tokens at rest.

Uses Fernet (AES-128-CBC + HMAC-SHA256) with a key derived from
EMAIL_ENCRYPTION_KEY (or JWT_SECRET as fallback).
"""
from base64 import urlsafe_b64decode, urlsafe_b64encode

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings


def _derive_key() -> bytes:
    raw = (settings.EMAIL_ENCRYPTION_KEY or settings.JWT_SECRET).encode()
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"relayai-email-token-encryption",
    )
    return urlsafe_b64encode(hkdf.derive(raw))


_fernet: Fernet | None = None


def _get_cipher() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_key())
    return _fernet


def encrypt_token(plain: str) -> str:
    """Encrypt a plaintext token string. Returns a base64-encoded ciphertext."""
    return _get_cipher().encrypt(plain.encode()).decode()


def decrypt_token(cipher: str) -> str:
    """Decrypt a ciphertext token string back to plaintext."""
    return _get_cipher().decrypt(cipher.encode()).decode()
