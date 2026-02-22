"""
Crypto utilities — bcrypt password hashing & Fernet symmetric encryption.

Password hashing:
  Supports both bcrypt ($2b$) and legacy werkzeug (scrypt/pbkdf2) hashes
  for backward compatibility with existing user records.

Symmetric encryption (S4-02 — Cloud ALM secret storage):
  `encrypt_secret` / `decrypt_secret` use Fernet (AES-128-CBC + HMAC-SHA256)
  keyed by the ENCRYPTION_KEY environment variable.

  Why Fernet:
  - Authenticated encryption — tamper detection built in.
  - URL-safe base64 output — fits in TEXT columns.
  - Key rotation: re-encrypt with new key, no schema change.

  WARNING: ENCRYPTION_KEY must be a 32-byte URL-safe base64 key generated via:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  Store it in the environment — never hard-code or commit it.
"""

import os

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from werkzeug.security import check_password_hash


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt (12 rounds)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain-text password against its hash.

    Handles both bcrypt ($2b$/$2a$) and legacy werkzeug (scrypt/pbkdf2) formats.
    """
    if not password_hash:
        return False

    # Bcrypt hashes start with $2b$ or $2a$
    if password_hash.startswith(("$2b$", "$2a$")):
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )

    # Fall back to werkzeug hash verification (legacy onboarding hashes)
    return check_password_hash(password_hash, plain_password)


# ── Fernet symmetric encryption (Cloud ALM secret storage) ───────────────────


def _get_fernet() -> Fernet:
    """Return a Fernet instance keyed by the ENCRYPTION_KEY env var.

    Raises RuntimeError if ENCRYPTION_KEY is not set — fail loud at startup
    rather than silently storing plaintext secrets.
    """
    raw_key = os.getenv("ENCRYPTION_KEY")
    if not raw_key:
        raise RuntimeError(
            "ENCRYPTION_KEY environment variable is not set. "
            "Generate one with: python -c \""
            "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext secret and return URL-safe base64 ciphertext.

    Used to store CloudALMConfig.client_secret (and any other integration
    credentials) at rest.  Output is safe for TEXT database columns.

    Args:
        plaintext: The secret to encrypt (e.g. OAuth2 client_secret).

    Returns:
        Fernet-encrypted, URL-safe base64-encoded string.

    Raises:
        RuntimeError: If ENCRYPTION_KEY is not set.
    """
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted ciphertext back to plaintext.

    Args:
        ciphertext: Value previously returned by encrypt_secret().

    Returns:
        Original plaintext string.

    Raises:
        RuntimeError: If ENCRYPTION_KEY is not set.
        cryptography.fernet.InvalidToken: If ciphertext is tampered or
            encrypted with a different key.
    """
    return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
