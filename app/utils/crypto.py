"""
Crypto utilities — bcrypt password hashing & verification.

Supports both bcrypt ($2b$) and legacy werkzeug (scrypt/pbkdf2) hashes
for backward compatibility with existing user records.
"""

import bcrypt
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
