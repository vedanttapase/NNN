# SURAKSHA NETRA

This repository contains the current SURAKSHA NETRA project source.

The imported code is a development snapshot, not a production-certified surveillance system. The backend includes service logic, camera-worker code, event rules, evidence handling, FastAPI routes, and WebSocket support. The browser dashboard is not yet integrated with the new backend APIs, and real webcam/RTSP + YOLO operation still requires verification on the target Windows machine.

See:
- `PROJECT_STATUS.md` for implemented vs. unverified functionality.
- `WINDOWS_SETUP.md` for setup and local execution.
- `backend/README.md` for backend details.

Do not commit a local `.env`, camera credentials, database files, or encryption keys.