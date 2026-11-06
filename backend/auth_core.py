"""Password hashing and role-based permissions. Standard library only.

Passwords are stored as PBKDF2-HMAC-SHA256 with a per-user random salt and a high
iteration count. Plaintext passwords are never stored, logged or returned.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from enum import Enum

PBKDF2_ITERATIONS = 600_000
HASH_ALGORITHM = "pbkdf2_sha256"
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256


class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(str, Enum):
    VIEW = "view"
    MANAGE_CAMERAS = "manage_cameras"
    MANAGE_RULES = "manage_rules"
    MANAGE_INCIDENTS = "manage_incidents"
    MANAGE_USERS = "manage_users"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset({Permission.VIEW}),
    Role.OPERATOR: frozenset({Permission.VIEW, Permission.MANAGE_INCIDENTS, Permission.MANAGE_CAMERAS}),
    Role.ADMIN: frozenset(Permission),
}


class PasswordPolicyError(ValueError):
    """The password does not meet the policy. The message never includes the password."""


def has_permission(role: Role | str, permission: Permission) -> bool:
    try:
        resolved = Role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS[resolved]


def validate_password_policy(password: str) -> None:
    if not isinstance(password, str):
        raise PasswordPolicyError("password must be a string")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"password must be at most {MAX_PASSWORD_LENGTH} characters")


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    validate_password_policy(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "$".join([
        HASH_ALGORITHM,
        str(iterations),
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    ])


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison. Returns False for any malformed stored value or input."""
    if not isinstance(password, str) or not isinstance(stored, str):
        return False
    if len(password) > MAX_PASSWORD_LENGTH:
        return False
    try:
        algorithm, iterations_text, salt_b64, digest_b64 = stored.split("$")
        if algorithm != HASH_ALGORITHM:
            return False
        iterations = int(iterations_text)
        if iterations < 100_000:
            return False
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(digest_b64, validate=True)
    except (ValueError, TypeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)
