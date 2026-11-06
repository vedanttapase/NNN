"""Single source of configuration for the API and the admin command.

Reads backend/.env (or SURAKSHA_ENV_FILE) with the same loader as before. Real environment
variables win over the file. Nothing here prints or logs secret values.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "suraksha_netra_cv"))
sys.path.insert(0, str(ROOT))

from env_loader import load_env_file, resolve_env_file  # noqa: E402

load_env_file(resolve_env_file(ROOT / ".env"))


def _path(env_name: str, default_relative: str) -> Path:
    value = os.getenv(env_name, "").strip()
    path = Path(value) if value else Path(default_relative)
    return path if path.is_absolute() else ROOT / path


DATABASE_PATH = _path("DATABASE_PATH", "suraksha_netra.db")
BACKUP_DIR = ROOT / "backups"
EVIDENCE_DIR = _path("EVIDENCE_DIR", "evidence")
CAMERA_SECRET_KEY = os.getenv("CAMERA_SECRET_KEY") or None
MODEL_NAME = os.getenv("MODEL_NAME", "yolov8n")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
INFERENCE_STRIDE = max(1, int(os.getenv("INFERENCE_STRIDE", "1")))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
