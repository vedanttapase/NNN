"""Minimal .env loader (no third-party dependency).

Values already present in the process environment always win, so a
PowerShell $env:CAMERA_SECRET_KEY overrides the file.

The file must be UTF-8. Windows PowerShell 5.1 > and Out-File write UTF-16,
and some editors add a byte-order mark; the UTF-8 BOM is accepted, UTF-16 is
rejected with an explicit message instead of a confusing parse error.

SURAKSA_ENV_FILE, if set, replaces the default backend/.env path.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_FILE_OVERRIDE = "SURAKSA_ENV_FILE"
_UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")


def resolve_env_file(default: Path) -> Path:
    override = os.environ.get(ENV_FILE_OVERRIDE, "").strip()
    return Path(override) if override else default


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(_UTF16_BOMS):
        raise ValueError(
            f"{path.name} is UTF-16 encoded. Save it as UTF-8 (for example: "
            "Set-Content -Encoding utf8 or an editor's 'UTF-8' option)."
        )
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path.name} is not valid UTF-8") from exc


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_no, raw in enumerate(_read_text(path).splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key or not key.replace("_", "").isalnum():
            raise ValueError(f"{path.name}:{line_no}: expected KEY=VALUE")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def load_env_file(path: Path) -> list[str]:
    """Load into os.environ without overriding existing variables. Returns the keys set."""
    if not path.is_file():
        return []
    loaded = []
    for key, value in parse_env_file(path).items():
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded
