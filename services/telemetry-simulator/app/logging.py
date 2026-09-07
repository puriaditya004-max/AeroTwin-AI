from datetime import datetime, timezone
import json
import logging
from typing import Any


logger = logging.getLogger("m1-telemetry-simulator")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def log_event(event: str, **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "m1-telemetry-simulator",
        **fields,
        "event": event,
    }
    logger.info(json.dumps(payload, default=str, sort_keys=True))
