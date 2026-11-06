"""Create the first user (or any additional user) from the command line.

Run from backend\ :   python create_admin.py

The password is typed at a hidden prompt and is never echoed, logged or stored in plain text.
"""

from __future__ import annotations

import getpass
import sys

import settings
from product_store import ProductError, Store


def main() -> int:
    store = Store(settings.DATABASE_PATH, settings.BACKUP_DIR, settings.EVIDENCE_DIR,
                  camera_secret_key=settings.CAMERA_SECRET_KEY)
    username = input("Username (3-64 letters, digits, . _ -): ").strip()
    role = input("Role [admin/operator/viewer] (admin): ").strip().lower() or "admin"
    password = getpass.getpass("Password (at least 12 characters): ")
    if password != getpass.getpass("Repeat password: "):
        print("Passwords do not match. Nothing was created.")
        return 1
    try:
        user = store.create_user(username, password, role)
    except ProductError as exc:
        print(f"Not created: {exc}")
        return 1
    print(f"Created user '{user['username']}' with role '{user['role']}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
