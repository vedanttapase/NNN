# SURAKSHA NETRA

This repository contains the SURAKSHA NETRA development source: a FastAPI backend, camera-worker and CV modules, event rules, evidence storage, authentication, WebSocket updates, and a Next.js monitoring dashboard.

## Current status

This is a development snapshot, not a production-certified public-safety system. The complete source has been imported from the supplied archive. Hardware-dependent camera and YOLO behavior, Windows end-to-end checks, frontend production build, and live deployment must still be validated on the target environment.

## Repository map

- `backend/`: FastAPI services, SQLite persistence, camera registry and workers, authentication, event engine, evidence, WebSockets, and tests.
- `backend/suraksha_netra_cv/`: computer-vision detector package and detector tests.
- `app/`, `components/`, `public/`: Next.js dashboard and assets.
- `scripts/`: Windows verification utilities.
- `PROJECT_STATUS.md`: implemented and unverified milestones.
- `PROJECT_AUDIT.md`: audit findings and caveats.
- `WINDOWS_SETUP.md`: local Windows setup and run instructions.
- `VALIDATION_RESULTS.md`: automated validation record.
- `SOURCE_IMPORT_MANIFEST.md`: per-file source hashes for the imported archive.

## Quick start

1. Follow `WINDOWS_SETUP.md` to create the Python environment, install backend dependencies, and configure the frontend.
2. Copy `backend/.env.example` to `backend/.env`.
3. Generate a new Fernet key and set `CAMERA_SECRET_KEY` in the local `.env`. Never commit it.
4. Create an operator/admin account using the documented admin bootstrap command.
5. Start the backend and frontend using the commands in `WINDOWS_SETUP.md`.

## Security and operational limits

- Do not commit `backend/.env`, camera credentials, database files, model weights, or encryption keys.
- Camera frames and alerts must be grounded in actual stream data; a registered camera is not necessarily live.
- Computer-vision events are assistive signals and require human review. Do not infer criminality or intent from a person's appearance.
- Validate camera hardware, model weights, Windows startup, and deployment on the actual target system before operational use.
