"""Encryption and redaction for camera source credentials.

RTSP sources can embed credentials. They are encrypted at rest with Fernet using
CAMERA_SECRET_KEY. Only the credential-free display form may leave this module.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from cryptography.fernet import Fernet, InvalidToken

ALLOWED_SCHEMES = ("rtsp", "rtsps")
MAX_SOURCE_LENGTH = 2048
KEY_GENERATION_HINT = (
    'Generate one with: python -c "from cryptography.fernet import Fernet; '
    'print(Fernet.generate_key().decode())"'
)


class SecretConfigError(RuntimeError):
    """The CAMERA_SECRET_KEY is missing or invalid."""


class SecretDecryptError(RuntimeError):
    """A stored camera source cannot be decrypted with the configured key."""


def load_fernet(key: str | None) -> Fernet:
    if not key:
        raise SecretConfigError(f"CAMERA_SECRET_KEY is not set. {KEY_GENERATION_HINT}")
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise SecretConfigError(f"CAMERA_SECRET_KEY is not a valid Fernet key. {KEY_GENERATION_HINT}") from exc


def validate_source(source: str) -> str:
    """Accept an RTSP(S) URL with host or a non-negative integer camera index."""
    if not isinstance(source, str):
        raise ValueError("Camera source must be a string")
    value = source.strip()
    if not value or len(value) > MAX_SOURCE_LENGTH:
        raise ValueError(f"Camera source must be 1-{MAX_SOURCE_LENGTH} characters")
    if value.isdigit():
        return value
    try:
        parts = urlsplit(value)
        parts.port
    except ValueError as exc:
        raise ValueError("Camera source is not a valid URL") from exc
    if parts.scheme.lower() not in ALLOWED_SCHEMES or not parts.hostname:
        raise ValueError("Camera source must be an rtsp:// or rtsps:// URL with a host, or a numeric device index")
    return value


def redact_source(source: str) -> str:
    """Credential-free display form. Drops userinfo and query string."""
    if source.isdigit():
        return f"device:{source}"
    parts = urlsplit(source)
    host = parts.hostname or ""
    try:
        port = parts.port
    except ValueError:
        port = None
    netloc = f"{host}:{port}" if port else host
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def encrypt_source(fernet: Fernet, source: str) -> str:
    return fernet.encrypt(source.encode("utf-8")).decode("ascii")


def decrypt_source(fernet: Fernet, token: str) -> str:
    try:
        return fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise SecretDecryptError(
            "Stored camera credential cannot be decrypted with the configured CAMERA_SECRET_KEY"
        ) from exc
