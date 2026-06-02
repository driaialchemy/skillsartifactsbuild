# Metadata Foundation Layer - Documentation

## Overview

The Metadata Foundation Layer provides comprehensive observability and reproducibility tracking for the AI Demand Planning Analyst pipeline. It captures run-level, stage-level, and configuration metadata without modifying existing pipeline behavior.

**Status**: Phases 1-2 Complete (all 7 stages instrumented)

## Quick Start

### Running the Pipeline

```bash
# Run baseline pipeline with metadata capture
python scripts/run_pipeline.py --type baseline

# Run with different seed
python scripts/run_pipeline.py --type baseline --seed 123

# Skip validation
python scripts/run_pipeline.py --type baseline --skip-validation
```

### Viewing Results

```bash
# View the latest baseline run summary
cat data/runs/$(ls -t data/runs | grep baseline | head -1)/summary.md

# View run manifest
cat data/runs/$(ls -t data/runs | grep baseline | head -1)/run_manifest.json

# View specific stage metadata
cat data/runs/<run_id>/stage_02_detect_exceptions.json
```

## Architecture

### Directory Structure

```
data/
├── runs/                              # All run metadata
│   ├── 20260509-150917-42-baseline/  # Run directory
│   │   ├── run_manifest.json         # Run-level metadata
│   │   ├── stage_01_generate_forecasts.json
│   │   ├── stage_02_detect_exceptions.json
│   │   ├── stage_03_generate_memos.json
│   │   ├── stage_04_score_and_rank.json
│   │   ├── stage_05_simulate_planner_feedback.json
│   │   ├── stage_06_calibrate_system.json
│   │   ├── stage_07_validate_pipeline.json
│   │   └── summary.md                # Human-readable summary
│   └── ...
├── traces/
│   └── trace_index.json              # Fast lookup index
└── [existing data files unchanged]
    ├── forecasts.json
    ├── forecasts_with_exceptions.json
    ├── forecasts_with_memos.json
    └── forecasts_ranked.json
```

### Metadata Schema

#### Run Manifest (`run_manifest.json`)

```json
{
  "schema_version": "1.0",
  "run_id": "20260509-150917-42-baseline",
  "run_type": "baseline",
  "pipeline_version": "0.5.0",
  "created_at": "2026-05-09T22:09:17.932249+00:00",
  "completed_at": "2026-05-09T22:09:18.823456+00:00",
  "duration_seconds": 0.89,
  "status": "success",
  "config": {
    "seed": 42,
    "thresholds": {
      "low_confidence": 0.55,
      "change_ratio": 0.25,
      "volatility": 0.25,
      "band_ratio": 0.35
    }
  },
  "stages_completed": 7,
  "environment": {
    "python_version": "3.11.9",
    "platform": "windows"
  }
}
```

#### Stage Metadata (`stage_0N_name.json`)

```json
{
  "schema_version": "1.0",
  "stage_id": "20260509-150917-42-baseline-stage2-detect_exceptions",
  "run_id": "20260509-150917-42-baseline",
  "stage_number": 2,
  "stage_name": "detect_exceptions",
  "started_at": "2026-05-09T22:09:18.123456+00:00",
  "duration_seconds": 0.01,
  "status": "success",
  "inputs": [
    {
      "file": "data\\forecasts.json",
      "md5_hash": "c908db14473ba8f6000a76cd0c266a22",
      "row_count": 50
    }
  ],
  "outputs": [
    {
      "file": "data\\forecasts_with_exceptions.json",
      "row_count": 50,
      "fields_added": ["is_exception", "exception_reasons"]
    }
  ],
  "metrics": {
    "exceptions_detected": 16,
    "exception_rate": 0.32,
    "reason_counts": {
      "Low confidence": 9,
      "Forecast changed": 8,
      "Recent sales volatility": 0,
      "Wide confidence band": 10
    }
  },
  "thresholds_used": {
    "low_confidence_threshold": 0.55,
    "change_ratio_threshold": 0.25,
    "volatility_threshold": 0.25,
    "band_ratio_threshold": 0.35
  }
}
```

#### Trace Index (`trace_index.json`)

```json
{
  "schema_version": "1.0",
  "runs": {
    "20260509-150917-42-baseline": {
      "run_type": "baseline",
      "status": "success",
      "created_at": "2026-05-09T22:09:17.932249+00:00",
      "duration_seconds": 0.89
    }
  },
  "latest_by_type": {
    "baseline": "20260509-150917-42-baseline"
  }
}
```

## Using Metadata in Scripts

### Basic Usage

```python
from metadata_foundation import MetadataContext, get_current_run_id

def main():
    run_id = get_current_run_id()

    with MetadataContext(run_id, stage_number=2,
                         stage_name="detect_exceptions",
                         script_path="scripts/detect_exceptions.py") as ctx:
        # Log thresholds
        ctx.log_threshold("low_confidence_threshold", 0.55)

        # Your existing logic here
        data = process_data()

        # Log metrics
        ctx.log_metric("exceptions_detected", count)
        ctx.log_output("data/output.json", row_count=len(data))
```

### Manual Run Execution

```bash
# Set run ID manually
export PIPELINE_RUN_ID=20260509-120000-42-manual

# Run individual scripts
python scripts/generate_forecasts.py
python scripts/detect_exceptions.py
# ...
```

## Pipeline Stages

| Stage | Script | Purpose | Key Metrics |
|-------|--------|---------|-------------|
| 1 | `generate_forecasts.py` | Generate forecast data | forecasts_generated, low_confidence_count |
| 2 | `detect_exceptions.py` | Flag exceptions | exceptions_detected, exception_rate, reason_counts |
| 3 | `generate_memos.py` | Generate decision memos | memos_generated, recommendation_distribution |
| 4 | `score_and_rank.py` | Score and rank forecasts | tier_distribution, total_ranked |
| 5 | `simulate_planner_feedback.py` | Simulate planner actions | decision_matches, accuracy, error_type_distribution |
| 6 | `calibrate_system.py` | Generate calibration report | overall_accuracy, avg_confidence_gap, bias_flags_count |
| 7 | `validate_pipeline_data.py` | Validate data integrity | files_validated, total_rows_validated, validation_errors |

## Querying Metadata

### Python Examples

```python
import json
from pathlib import Path

# Load trace index
trace_index = json.loads(Path("data/traces/trace_index.json").read_text())

# Get latest baseline run
latest_baseline_id = trace_index["latest_by_type"]["baseline"]
print(f"Latest baseline run: {latest_baseline_id}")

# Load run manifest
manifest_path = f"data/runs/{latest_baseline_id}/run_manifest.json"
manifest = json.loads(Path(manifest_path).read_text())
print(f"Overall accuracy: {manifest['config']}")

# Load stage metadata
stage_path = f"data/runs/{latest_baseline_id}/stage_02_detect_exceptions.json"
stage = json.loads(Path(stage_path).read_text())
print(f"Exceptions detected: {stage['metrics']['exceptions_detected']}")
```

### Shell Examples

```bash
# Find all successful runs
jq '.runs | to_entries | map(select(.value.status == "success")) | .[].key' \
  data/traces/trace_index.json

# Get exception rate from latest baseline
LATEST=$(jq -r '.latest_by_type.baseline' data/traces/trace_index.json)
jq '.metrics.exception_rate' "data/runs/$LATEST/stage_02_detect_exceptions.json"

# Compare accuracy across runs
for run in data/runs/*/; do
  RUN_ID=$(basename "$run")
  ACCURACY=$(jq '.metrics.overall_accuracy' "$run/stage_06_calibrate_system.json" 2>/dev/null)
  echo "$RUN_ID: $ACCURACY"
done
```

## Reproducibility

Every run captures all information needed for exact reproduction:

```bash
# From summary.md or run_manifest.json
export PIPELINE_RUN_ID=20260509-150917-42-baseline
export PIPELINE_SEED=42

# Run all stages
python scripts/generate_forecasts.py
python scripts/detect_exceptions.py
python scripts/generate_memos.py
python scripts/score_and_rank.py
python scripts/simulate_planner_feedback.py
python scripts/calibrate_system.py
```

## Run Types

- **baseline**: Standard pipeline execution (default)
- **stress**: Stress test scenarios
- **noise-mild**: Mild noise injection
- **noise-moderate**: Moderate noise injection
- **noise-targeted**: Targeted noise injection
- **test**: Test/development runs

## Key Features

### Deterministic Run IDs

Run IDs are deterministic for the same seed and timestamp:
- Format: `{YYYYMMDD}-{HHMMSS}-{SEED}-{run_type}`
- Example: `20260509-150917-42-baseline`

### MD5 Hash Verification

Input files are MD5-hashed for integrity verification:
```python
# Verify input hasn't changed
stage = json.loads(Path("data/runs/.../stage_02_detect_exceptions.json").read_text())
expected_hash = stage["inputs"][0]["md5_hash"]
actual_hash = hashlib.md5(Path("data/forecasts.json").read_bytes()).hexdigest()
assert expected_hash == actual_hash
```

### Zero Breaking Changes

The metadata layer is completely additive:
- Existing `data/*.json` files unchanged
- Streamlit app requires no modifications
- All metadata stored in `data/runs/` and `data/traces/`

## Future Extensions (Not Yet Implemented)

### Phase 3: Item Evolution Tracking
- Track field changes across stages
- Capture tier transitions with reasons
- Monitor confidence evolution

### Phase 4: Advanced Summaries
- Health dashboard (rolling 24h view)
- Anomaly detection
- Drift analysis

### Phase 5: Diagnostic Integration
- Link analysis scripts to runs
- Track ranking stability across runs
- Performance trend analysis

## Troubleshooting

### Run ID Not Set

If you see `run_id not found` errors:
```bash
export PIPELINE_RUN_ID=$(python -c "from datetime import datetime; print(datetime.now().strftime('%Y%m%d-%H%M%S') + '-42-baseline')")
```

### Missing Metadata Files

If metadata files aren't being created:
1. Check that `PIPELINE_RUN_ID` is set
2. Verify `data/runs/` directory exists
3. Check file permissions

### Stage Failures

If a stage fails:
1. Check the stage's `status` in metadata
2. Review error logs
3. Verify input file integrity using MD5 hashes

## API Reference

### MetadataContext

```python
class MetadataContext:
    """Context manager for stage execution metadata collection."""

    def __init__(self, run_id: str, stage_number: int,
                 stage_name: str, script_path: str):
        """Initialize metadata context."""

    def log_metric(self, name: str, value: Any):
        """Log a metric for this stage."""

    def log_threshold(self, name: str, value: Any):
        """Log a threshold used in this stage."""

    def log_input(self, file_path: str, row_count: Optional[int] = None):
        """Log an input file with MD5 hash."""

    def log_output(self, file_path: str, row_count: Optional[int] = None,
                   fields_added: Optional[list] = None):
        """Log an output file."""
```

### Helper Functions

```python
def get_current_run_id() -> str:
    """Get run ID from environment variable or generate one."""

def init_run(run_id: str, run_type: str = "baseline",
             seed: int = 42, config: dict = None):
    """Initialize a pipeline run."""

def finalize_run(run_id: str, status: str = "success"):
    """Finalize a pipeline run and generate summary."""
```

## Best Practices

1. **Always use the orchestrator** for full pipeline runs
2. **Set meaningful run types** for easy filtering
3. **Review summary.md** after each run
4. **Check validation status** before using results
5. **Compare runs** using trace index queries

## Support

For issues or questions:
- Review this documentation
- Check `summary.md` for run-specific details
- Examine stage metadata for detailed metrics
- Consult the plan document for design rationale
