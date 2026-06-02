"""Metadata Foundation Layer - Minimal helper for pipeline observability."""
import json
import hashlib
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class MetadataContext:
    """Context manager for stage execution metadata collection."""

    def __init__(self, run_id: str, stage_number: int, stage_name: str, script_path: str):
        self.run_id = run_id
        self.stage_number = stage_number
        self.stage_name = stage_name
        self.script_path = script_path
        self.stage_id = f"{run_id}-stage{stage_number}-{stage_name}"
        self.started_at = None
        self.metrics = {}
        self.thresholds = {}
        self.inputs = []
        self.outputs = []
        self.status = "success"

    def __enter__(self):
        self.started_at = datetime.now(timezone.utc)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now(timezone.utc) - self.started_at).total_seconds()

        if exc_type is not None:
            self.status = "failed"

        stage_metadata = {
            "schema_version": "1.0",
            "stage_id": self.stage_id,
            "run_id": self.run_id,
            "stage_number": self.stage_number,
            "stage_name": self.stage_name,
            "started_at": self.started_at.isoformat(),
            "duration_seconds": round(duration, 2),
            "status": self.status,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metrics": self.metrics,
            "thresholds_used": self.thresholds,
        }

        # Write stage metadata
        run_dir = Path(f"data/runs/{self.run_id}")
        run_dir.mkdir(parents=True, exist_ok=True)
        stage_file = run_dir / f"stage_{self.stage_number:02d}_{self.stage_name}.json"
        stage_file.write_text(json.dumps(stage_metadata, indent=2), encoding="utf-8")

        return False  # Don't suppress exceptions

    def log_metric(self, name: str, value: Any):
        """Log a metric for this stage."""
        self.metrics[name] = value

    def log_threshold(self, name: str, value: Any):
        """Log a threshold used in this stage."""
        self.thresholds[name] = value

    def log_input(self, file_path: str, row_count: Optional[int] = None):
        """Log an input file."""
        path = Path(file_path)
        if path.exists():
            content = path.read_bytes()
            md5_hash = hashlib.md5(content).hexdigest()
            input_info = {
                "file": str(file_path),
                "md5_hash": md5_hash,
            }
            if row_count is not None:
                input_info["row_count"] = row_count
            self.inputs.append(input_info)

    def log_output(self, file_path: str, row_count: Optional[int] = None, fields_added: Optional[list] = None):
        """Log an output file."""
        output_info = {"file": str(file_path)}
        if row_count is not None:
            output_info["row_count"] = row_count
        if fields_added:
            output_info["fields_added"] = fields_added
        self.outputs.append(output_info)


def get_current_run_id() -> str:
    """Get run ID from environment variable or generate one."""
    run_id = os.environ.get("PIPELINE_RUN_ID")
    if run_id:
        return run_id

    # Generate run_id if not set
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    seed = os.environ.get("PIPELINE_SEED", "42")
    run_type = os.environ.get("PIPELINE_RUN_TYPE", "baseline")
    return f"{timestamp}-{seed}-{run_type}"


def init_run(run_id: str, run_type: str = "baseline", seed: int = 42, config: dict = None, policy_version: str = None):
    """Initialize a pipeline run."""
    run_dir = Path(f"data/runs/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "run_type": run_type,
        "pipeline_version": "0.5.0",
        "policy_version": policy_version or os.environ.get("POLICY_VERSION", "v1.0.0"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "config": {
            "seed": seed,
            **(config or {}),
        },
        "environment": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.system().lower(),
        }
    }

    manifest_file = run_dir / "run_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return run_dir


def finalize_run(run_id: str, status: str = "success"):
    """Finalize a pipeline run and generate summary."""
    run_dir = Path(f"data/runs/{run_id}")
    manifest_file = run_dir / "run_manifest.json"

    if not manifest_file.exists():
        return

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["status"] = status

    # Calculate duration
    created = datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
    completed = datetime.fromisoformat(manifest["completed_at"].replace("Z", "+00:00"))
    manifest["duration_seconds"] = round((completed - created).total_seconds(), 2)

    # Count stages
    stage_files = list(run_dir.glob("stage_*.json"))
    manifest["stages_completed"] = len(stage_files)

    # Write updated manifest
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Generate summary
    generate_summary(run_id, manifest, stage_files)

    # Update trace index
    update_trace_index(run_id, manifest)


def generate_summary(run_id: str, manifest: dict, stage_files: list):
    """Generate human-readable summary.md."""
    run_dir = Path(f"data/runs/{run_id}")

    lines = [
        f"# Pipeline Run Summary: {run_id}",
        "",
        "## Run Metadata",
        f"- **Run ID**: {run_id}",
        f"- **Type**: {manifest.get('run_type', 'unknown')}",
        f"- **Status**: {manifest.get('status', 'unknown')}",
        f"- **Started**: {manifest.get('created_at', 'unknown')}",
        f"- **Duration**: {manifest.get('duration_seconds', 0):.2f}s",
        "",
        "## Configuration",
        f"- **Seed**: {manifest.get('config', {}).get('seed', 'unknown')}",
    ]

    # Add thresholds if present
    config = manifest.get('config', {})
    if 'thresholds' in config:
        lines.append("- **Thresholds**:")
        for k, v in config['thresholds'].items():
            lines.append(f"  - {k}: {v}")

    lines.extend(["", "## Stage Execution"])

    # Sort stage files by stage number
    sorted_stages = sorted(stage_files, key=lambda p: int(p.stem.split('_')[1]))

    for stage_file in sorted_stages:
        stage_data = json.loads(stage_file.read_text(encoding="utf-8"))
        lines.append(f"\n### Stage {stage_data['stage_number']}: {stage_data['stage_name']}")
        lines.append(f"- **Status**: {stage_data['status']}")
        lines.append(f"- **Duration**: {stage_data['duration_seconds']:.2f}s")

        if stage_data.get('metrics'):
            lines.append("- **Metrics**:")
            for k, v in stage_data['metrics'].items():
                if isinstance(v, float):
                    lines.append(f"  - {k}: {v:.4f}")
                else:
                    lines.append(f"  - {k}: {v}")

        if stage_data.get('outputs'):
            lines.append("- **Outputs**:")
            for output in stage_data['outputs']:
                lines.append(f"  - {output['file']}")

    lines.extend([
        "",
        "## Reproducibility",
        "```bash",
        f"export PIPELINE_RUN_ID={run_id}",
        f"export PIPELINE_SEED={manifest.get('config', {}).get('seed', 42)}",
        "python scripts/generate_forecasts.py",
        "python scripts/detect_exceptions.py",
        "python scripts/generate_memos.py",
        "python scripts/score_and_rank.py",
        "```",
        ""
    ])

    summary_file = run_dir / "summary.md"
    summary_file.write_text("\n".join(lines), encoding="utf-8")


def update_trace_index(run_id: str, manifest: dict):
    """Update trace index with latest run."""
    traces_dir = Path("data/traces")
    traces_dir.mkdir(parents=True, exist_ok=True)
    index_file = traces_dir / "trace_index.json"

    if index_file.exists():
        index = json.loads(index_file.read_text(encoding="utf-8"))
    else:
        index = {"schema_version": "1.0", "runs": {}}

    index["runs"][run_id] = {
        "run_type": manifest.get("run_type"),
        "status": manifest.get("status"),
        "created_at": manifest.get("created_at"),
        "duration_seconds": manifest.get("duration_seconds"),
    }

    # Track latest run by type
    if "latest_by_type" not in index:
        index["latest_by_type"] = {}

    run_type = manifest.get("run_type", "baseline")
    index["latest_by_type"][run_type] = run_id

    index_file.write_text(json.dumps(index, indent=2), encoding="utf-8")
