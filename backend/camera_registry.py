"""Camera registry persistence.

Camera records live in SQLite. RTSP sources are stored encrypted; only the
credential-free source_display form is exposed through the API.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet

from secrets_box import (
    decrypt_source,
    encrypt_source,
    load_fernet,
    redact_source,
    validate_source,
)

STATE_REGISTERED = "registered"
STATE_STREAMING = "streaming"
LEGACY_TABLE = "cameras_legacy_plaintext"

CAMERA_SCHEMA = """
CREATE TABLE IF NOT EXISTS cameras (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_encrypted TEXT NOT NULL,
    source_display TEXT NOT NULL,
    zone TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'registered',
    created_at TEXT NOT NULL
)
"""

INSERT_CAMERA = (
    "INSERT INTO cameras(id, name, source_encrypted, source_display, zone, state, created_at) "
    "VALUES(?, ?, ?, ?, ?, ?, ?)"
)


class CameraValidationError(ValueError):
    """Registration input is invalid. The message never contains the submitted source."""


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_camera_schema(conn: sqlite3.Connection, secret_key: str | None) -> None:
    """Create the cameras table, migrating a legacy plaintext table if one exists."""
    columns = _table_columns(conn, "cameras")
    if columns and "source_encrypted" not in columns:
        _migrate_plaintext_cameras(conn, secret_key)
        return
    conn.execute(CAMERA_SCHEMA)
    conn.commit()


def _migrate_plaintext_cameras(conn: sqlite3.Connection, secret_key: str | None) -> None:
    legacy_rows = conn.execute("SELECT id, name, source, zone, created_at FROM cameras").fetchall()
    fernet = load_fernet(secret_key) if legacy_rows else None
    conn.execute("BEGIN")
    try:
        conn.execute(f"ALTER TABLE cameras RENAME TO {LEGACY_TABLE}")
        conn.execute(CAMERA_SCHEMA)
        for row in legacy_rows:
            source = row[2]
            conn.execute(
                INSERT_CAMERA,
                (row[0], row[1], encrypt_source(fernet, source), redact_source(source), row[3], STATE_REGISTERED, row[4]),
            )
        conn.execute(f"DROP TABLE {LEGACY_TABLE}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    conn.execute("VACUUM")


def register_camera(conn: sqlite3.Connection, fernet: Fernet, *, name: str, source: str, zone: str) -> dict[str, Any]:
    try:
        normalized = validate_source(source)
    except ValueError as exc:
        raise CameraValidationError(str(exc)) from exc
    camera_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        INSERT_CAMERA,
        (camera_id, name, encrypt_source(fernet, normalized), redact_source(normalized), zone, STATE_REGISTERED, created_at),
    )
    conn.commit()
    return public_camera(get_camera_row(conn, camera_id))


def get_camera_row(conn: sqlite3.Connection, camera_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,)).fetchone()


def list_cameras(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM cameras ORDER BY created_at DESC").fetchall()
    return [public_camera(row) for row in rows]


def public_camera(row: sqlite3.Row) -> dict[str, Any]:
    """API representation. Contains no credentials or fabricated runtime values."""
    data = dict(row)
    return {
        "id": data["id"],
        "name": data["name"],
        "zone": data["zone"],
        "state": data["state"],
        "source_display": data["source_display"],
        "is_streaming": data["state"] == STATE_STREAMING,
        "people": None,
        "created_at": data["created_at"],
    }


def decrypt_camera_source(fernet: Fernet, row: sqlite3.Row) -> str:
    """Internal use only. Never place the result in a response or log."""
    return decrypt_source(fernet, dict(row)["source_encrypted"])
