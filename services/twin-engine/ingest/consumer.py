import json
from typing import Any


def decode_stream_payload(message_data: dict[Any, Any]) -> dict[str, Any] | None:
    """Decode the canonical Redis Stream payload field used by M1 -> M2."""
    raw_payload = message_data.get(b"payload") or message_data.get("payload")
    if raw_payload is None:
        return None
    if isinstance(raw_payload, bytes):
        raw_payload = raw_payload.decode("utf-8")
    if isinstance(raw_payload, str):
        return json.loads(raw_payload)
    if isinstance(raw_payload, dict):
        return raw_payload
    raise ValueError(f"Unsupported payload type: {type(raw_payload)!r}")
