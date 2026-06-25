"""
TrustNet Security Utilities
Centralised password hashing and verification using bcrypt directly.
No passlib dependency — uses the bcrypt package natively.
"""

import bcrypt
import structlog

logger = structlog.get_logger()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    Returns a UTF-8 decoded bcrypt hash string.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.
    Returns True if they match, False otherwise.
    Safe against timing attacks via bcrypt's constant-time comparison.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as exc:
        logger.warning("security.verify_password_error", error=str(exc))
        return False
