"""Observable events only. Redaction applies to every persisted payload."""
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path


def redact(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: "[REDACTED]" if re.search(r"key|secret|password|token|authorization", k, re.I)
                else redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        for key, secret in os.environ.items():
            if re.search(r"KEY|SECRET|PASSWORD|TOKEN", key) and len(secret) >= 4:
                value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", value)
        value = re.sub(r"(?i)(bearer\s+)[^\s\"']+", r"\1[REDACTED]", value)
    return value


class TraceRecorder:
    def __init__(self, trace_id, path=None):
        self.trace_id, self.path, self.events = trace_id, path, []

    def record(self, event, **payload):
        row = redact(dict(trace_id=self.trace_id, event=event,
                          timestamp=datetime.now(timezone.utc).isoformat(), **payload))
        self.events.append(row)
        if self.path is not None:
            path = Path(self.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, allow_nan=False) + "\n")
