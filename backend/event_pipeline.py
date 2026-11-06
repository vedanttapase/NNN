"""Connect tracked person observations to the event engine and the store.

One CameraEventPipeline per camera. The camera worker calls process() once per processed
frame with the frame it actually read and the tracks YOLO+tracker produced for that frame.
Nothing is synthesized here: an event exists only if a configured rule fired on a real track.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Sequence

import numpy as np
import cv2
from event_engine import TrackObservation, build_rule
from product_store import Store

IncidentCallback = Callable[[dict], None]


class PipelineError(RuntimeError):
    pass


def check_frame(frame) -> None:
    if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise PipelineError("frame must be a BGR uint8 array of shape (H, W, 3)")


def encode_jpeg(frame: np.ndarray, quality: int = 90) -> bytes:
    check_frame(frame)
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise PipelineError("JPEG encoding of the frame failed")
    return buffer.tobytes()


class CameraEventPipeline:
    def __init__(self, store: Store, camera_id: str, on_incident: IncidentCallback | None = None) -> None:
        self.store = store
        self.camera_id = camera_id
        self.on_incident = on_incident
        self._rules: list[tuple[int, object]] = []
        self.reload()

    def reload(self) -> None:
        """Rebuild rule state from the database. Call after rules change. Resets dwell and count state."""
        loaded = []
        for row in self.store.enabled_rules_for_camera(self.camera_id):
            rule = build_rule(row["rule_type"], row["name"], row["config"], row["severity"])
            loaded.append((row["id"], rule))
        self._rules = loaded

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def process(self, frame: np.ndarray, tracks: Sequence[TrackObservation], *,
                timestamp: float, observed_at: str | None = None) -> list[dict]:
        """Evaluate every enabled rule on this frame. Returns the incidents created (may be empty)."""
        check_frame(frame)
        if not self._rules:
            return []
        when = observed_at or datetime.now(timezone.utc).isoformat()
        track_list = list(tracks)
        triggered: list[tuple[int, dict]] = []
        for rule_id, rule in self._rules:
            for event in rule.evaluate(self.camera_id, timestamp, track_list):
                triggered.append((rule_id, event))
        if not triggered:
            return []
        jpeg = encode_jpeg(frame)
        created = []
        for rule_id, event in triggered:
            incident = self.store.record_triggered_event(
                rule_id=rule_id, event=event, jpeg=jpeg, observed_at=when)
            created.append(incident)
            if self.on_incident is not None:
                self.on_incident(incident)
        return created
