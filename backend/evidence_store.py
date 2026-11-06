"""Evidence file storage for incident snapshots.

Filenames are server-generated; paths are confined to the evidence directory;
only JPEG/PNG magic bytes are accepted; writes are atomic.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MAX_BYTES = 10 * 1024 * 1024
_SAFE_LABEL = re.compile(r"[^A-Za-z0-9_-]+")
_MAGIC = {
    b"\xff\xd8\xff": ("jpg", "image/jpeg"),
    b"\x89PNG\r\n\x1a\n": ("png", "image/png"),
}


class EvidenceError(ValueError):
    """Evidence could not be stored or located."""


def detect_image_type(data: bytes) -> tuple[str, str]:
    for magic, info in _MAGIC.items():
        if data.startswith(magic):
            return info
    raise EvidenceError("evidence must be a JPEG or PNG image")


def _label(value: str, max_len: int = 40) -> str:
    cleaned = _SAFE_LABEL.sub("_", str(value)).strip("_")
    return (cleaned or "x")[:max_len]


def build_filename(camera_id: str, event_type: str, extension: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}_{_label(camera_id)}_{_label(event_type)}_{uuid.uuid4().hex}.{extension}"


def resolve_inside(base_dir: Path, relative_name: str) -> Path:
    """Resolve a stored relative name and refuse anything that escapes base_dir."""
    if not relative_name or "/" in relative_name or "\\" in relative_name or relative_name.startswith("."):
        raise EvidenceError("invalid evidence name")
    base = base_dir.resolve()
    candidate = (base / relative_name).resolve()
    if os.path.commonpath([str(base), str(candidate)]) != str(base):
        raise EvidenceError("invalid evidence name")
    return candidate


def save_evidence(base_dir: Path, data: bytes, *, camera_id: str, event_type: str,
                  max_bytes: int = DEFAULT_MAX_BYTES, now: datetime | None = None) -> dict:
    if not isinstance(data, (bytes, bytearray)) or len(data) == 0:
        raise EvidenceError("evidence is empty")
    if len(data) > max_bytes:
        raise EvidenceError(f"evidence exceeds the {max_bytes}-byte limit")
    extension, mime = detect_image_type(bytes(data[:16]))
    base_dir.mkdir(parents=True, exist_ok=True)
    name = build_filename(camera_id, event_type, extension, now)
    target = resolve_inside(base_dir, name)
    tmp = target.with_name(target.name + f".{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()
    return {"name": name, "mime_type": mime, "size_bytes": len(data)}


def read_evidence(base_dir: Path, name: str) -> tuple[bytes, str]:
    path = resolve_inside(base_dir, name)
    if not path.is_file():
        raise EvidenceError("evidence not found")
    data = path.read_bytes()
    _, mime = detect_image_type(data[:16])
    return data, mime


def purge_older_than(base_dir: Path, retention_days: int, *, now: float | None = None) -> list[str]:
    """Delete only generated evidence files older than retention_days."""
    if retention_days < 1:
        raise EvidenceError("retention_days must be at least 1")
    if not base_dir.is_dir():
        return []
    cutoff = (now if now is not None else time.time()) - retention_days * 86400
    pattern = re.compile(r"^\d{8}T\d{6}Z_[A-Za-z0-9_-]+_[A-Za-z0-9_-]+_[0-9a-f]{32}\.(jpg|png)$")
    deleted: list[str] = []
    for entry in base_dir.iterdir():
        if not entry.is_file() or not pattern.match(entry.name):
            continue
        if entry.stat().st_mtime < cutoff:
            entry.unlink()
            deleted.append(entry.name)
    return deleted
