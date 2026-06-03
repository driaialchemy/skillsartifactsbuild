"""JSON loading helpers shared by the Streamlit app pages."""

import json
from pathlib import Path
from typing import Any


def unwrap_metadata_payload(payload: Any, data_key: str | None = None) -> Any:
    """Return data from either a raw JSON payload or a metadata-wrapped payload."""
    if not isinstance(payload, dict) or "_metadata" not in payload:
        return payload

    if data_key and data_key in payload:
        return payload[data_key]

    for key, value in payload.items():
        if key != "_metadata":
            return value

    return []


def load_json_payload(path: Path, data_key: str | None = None) -> Any:
    """Load JSON and normalize optional pipeline metadata wrappers."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return unwrap_metadata_payload(payload, data_key=data_key)
