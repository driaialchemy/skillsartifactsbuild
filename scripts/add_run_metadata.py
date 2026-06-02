"""Utility for injecting run metadata into pipeline output files."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union


def inject_metadata(
    data: Union[List, Dict],
    run_id: str = None,
    policy_version: str = None,
    pipeline_version: str = "0.5.0",
    additional_metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Wrap data with metadata header.

    Args:
        data: The data to wrap (list of forecasts, decisions, etc.)
        run_id: Run identifier
        policy_version: Policy version used
        pipeline_version: Pipeline version
        additional_metadata: Additional metadata fields

    Returns:
        Dictionary with _metadata and data
    """
    if run_id is None:
        run_id = os.environ.get("PIPELINE_RUN_ID", "unknown")

    if policy_version is None:
        policy_version = os.environ.get("POLICY_VERSION", "v1.0.0")

    metadata = {
        "run_id": run_id,
        "policy_version": policy_version,
        "pipeline_version": pipeline_version,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

    if additional_metadata:
        metadata.update(additional_metadata)

    # Determine data key based on data type
    if isinstance(data, list):
        # Check if it looks like forecasts
        if data and "item_id" in data[0]:
            data_key = "forecasts"
        elif data and "session_id" in data[0]:
            data_key = "sessions"
        else:
            data_key = "data"
    else:
        data_key = "data"

    return {
        "_metadata": metadata,
        data_key: data
    }


def extract_data(wrapped_data: Dict[str, Any]) -> Union[List, Dict]:
    """
    Extract data from metadata-wrapped structure.

    Args:
        wrapped_data: Data with _metadata wrapper

    Returns:
        The unwrapped data
    """
    if "_metadata" not in wrapped_data:
        # Not wrapped, return as-is
        return wrapped_data

    # Find the data key (should be the non-metadata key)
    for key in wrapped_data:
        if key != "_metadata":
            return wrapped_data[key]

    return []


def get_metadata(wrapped_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata from wrapped structure.

    Args:
        wrapped_data: Data with _metadata wrapper

    Returns:
        Metadata dictionary or empty dict if not wrapped
    """
    return wrapped_data.get("_metadata", {})


def load_with_fallback(file_path: Path) -> tuple:
    """
    Load JSON file with metadata extraction.

    Args:
        file_path: Path to JSON file

    Returns:
        Tuple of (data, metadata_dict)
    """
    content = json.loads(file_path.read_text(encoding="utf-8"))

    if isinstance(content, dict) and "_metadata" in content:
        # Wrapped format
        metadata = content["_metadata"]
        data = extract_data(content)
    else:
        # Legacy format without metadata
        metadata = {}
        data = content

    return data, metadata


def save_with_metadata(
    data: Union[List, Dict],
    file_path: Path,
    run_id: str = None,
    policy_version: str = None,
    additional_metadata: Dict[str, Any] = None
):
    """
    Save data with metadata wrapper.

    Args:
        data: Data to save
        file_path: Path to save to
        run_id: Run identifier
        policy_version: Policy version
        additional_metadata: Additional metadata
    """
    wrapped = inject_metadata(
        data,
        run_id=run_id,
        policy_version=policy_version,
        additional_metadata=additional_metadata
    )

    file_path.write_text(json.dumps(wrapped, indent=2), encoding="utf-8")


if __name__ == "__main__":
    # Test the utility
    test_data = [
        {"item_id": "TEST_001", "value": 100},
        {"item_id": "TEST_002", "value": 200}
    ]

    wrapped = inject_metadata(test_data, run_id="test-run-123", policy_version="v1.0.0")
    print("Wrapped data:")
    print(json.dumps(wrapped, indent=2))

    print("\n\nExtracted data:")
    print(json.dumps(extract_data(wrapped), indent=2))

    print("\n\nExtracted metadata:")
    print(json.dumps(get_metadata(wrapped), indent=2))
