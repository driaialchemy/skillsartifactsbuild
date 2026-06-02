# Metadata Foundation - Quick Reference

## Common Commands

### Run Pipeline
```bash
# Standard baseline run
python scripts/run_pipeline.py --type baseline

# With custom seed
python scripts/run_pipeline.py --type baseline --seed 123

# Different run types
python scripts/run_pipeline.py --type stress
python scripts/run_pipeline.py --type noise-mild
python scripts/run_pipeline.py --type test
```

### View Results
```bash
# Latest baseline run summary
ls -t data/runs/*baseline* | head -1 | xargs -I {} cat {}/summary.md

# Latest run ID
jq -r '.latest_by_type.baseline' data/traces/trace_index.json

# All runs
ls data/runs/

# Trace index
cat data/traces/trace_index.json
```

### Query Metrics
```bash
# Exception rate from latest run
LATEST=$(jq -r '.latest_by_type.baseline' data/traces/trace_index.json)
jq '.metrics.exception_rate' "data/runs/$LATEST/stage_02_detect_exceptions.json"

# Overall accuracy
jq '.metrics.overall_accuracy' "data/runs/$LATEST/stage_06_calibrate_system.json"

# Tier distribution
jq '.metrics.tier_distribution' "data/runs/$LATEST/stage_04_score_and_rank.json"
```

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Run manifest | `data/runs/{run_id}/run_manifest.json` | Run-level metadata |
| Stage metadata | `data/runs/{run_id}/stage_0N_name.json` | Stage-level metrics |
| Summary | `data/runs/{run_id}/summary.md` | Human-readable summary |
| Trace index | `data/traces/trace_index.json` | Run lookup index |

## Key Metrics by Stage

### Stage 1: Generate Forecasts
- `forecasts_generated`: Total forecasts created
- `low_confidence_count`: Count of low-confidence forecasts

### Stage 2: Detect Exceptions
- `exceptions_detected`: Total exceptions flagged
- `exception_rate`: Percentage of exceptions
- `reason_counts`: Breakdown by exception type

### Stage 3: Generate Memos
- `memos_generated`: Total memos created
- `recommendation_distribution`: Count by recommendation type

### Stage 4: Score and Rank
- `tier_distribution`: Count by priority tier
- `total_ranked`: Total items ranked

### Stage 5: Simulate Feedback
- `decision_matches`: Planner agreement count
- `accuracy`: Decision accuracy rate
- `error_type_distribution`: Error breakdown

### Stage 6: Calibrate System
- `overall_accuracy`: System-wide accuracy
- `avg_confidence_gap`: Average confidence gap
- `bias_flags_count`: Number of bias flags
- `error_distribution`: Error type counts

### Stage 7: Validate Pipeline
- `files_validated`: Successfully validated files
- `total_rows_validated`: Total rows checked
- `validation_errors`: Error count

## Python Snippets

### Load Latest Run
```python
import json
from pathlib import Path

# Get latest baseline run ID
trace_index = json.loads(Path("data/traces/trace_index.json").read_text())
run_id = trace_index["latest_by_type"]["baseline"]

# Load manifest
manifest = json.loads(Path(f"data/runs/{run_id}/run_manifest.json").read_text())
print(f"Run: {run_id}")
print(f"Status: {manifest['status']}")
print(f"Duration: {manifest['duration_seconds']}s")
```

### Load Stage Metrics
```python
# Load specific stage
stage = json.loads(Path(f"data/runs/{run_id}/stage_02_detect_exceptions.json").read_text())
print(f"Exception rate: {stage['metrics']['exception_rate']:.2%}")
```

### Compare Runs
```python
runs = trace_index["runs"]
for run_id, info in runs.items():
    if info["run_type"] == "baseline" and info["status"] == "success":
        stage = json.loads(Path(f"data/runs/{run_id}/stage_06_calibrate_system.json").read_text())
        accuracy = stage["metrics"]["overall_accuracy"]
        print(f"{run_id}: {accuracy:.4f}")
```

## Run ID Format

Format: `{YYYYMMDD}-{HHMMSS}-{SEED}-{run_type}`

Examples:
- `20260509-150917-42-baseline`
- `20260509-151000-42-stress`
- `20260509-151200-123-test`

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `PIPELINE_RUN_ID` | Current run identifier | `20260509-150917-42-baseline` |
| `PIPELINE_SEED` | Random seed | `42` |
| `PIPELINE_RUN_TYPE` | Run type | `baseline` |

## Thresholds Captured

All thresholds used by each stage are captured in stage metadata:

- **Stage 2 (Detect Exceptions)**:
  - `low_confidence_threshold`: 0.55
  - `change_ratio_threshold`: 0.25
  - `volatility_threshold`: 0.25
  - `band_ratio_threshold`: 0.35

- **Stage 3 (Generate Memos)**:
  - `low_confidence_threshold`: 0.6
  - `big_change_threshold`: 0.30
  - `volatility_threshold`: 0.40
  - `wide_band_threshold`: 0.50
  - `multi_flag_penalty`: 0.3
  - `single_flag_penalty`: 0.1

- **Stage 4 (Score and Rank)**:
  - `weights`: {change: 34.0, volatility: 24.0, band: 16.0, low_confidence: 12.0}
  - `diminishing_returns`: [1.0, 0.6, 0.3, 0.2]

- **Stage 6 (Calibrate System)**:
  - `calibration_gap_threshold`: 0.4

## Troubleshooting

### Problem: No metadata files created
**Solution**: Ensure `PIPELINE_RUN_ID` is set:
```bash
export PIPELINE_RUN_ID=$(date +%Y%m%d-%H%M%S)-42-baseline
```

### Problem: Can't find latest run
**Solution**: Check trace index:
```bash
cat data/traces/trace_index.json | jq '.latest_by_type'
```

### Problem: Stage failed
**Solution**: Check stage status in metadata:
```bash
jq '.status' data/runs/{run_id}/stage_0N_name.json
```

## Adding Metadata to New Scripts

Minimal 5-line pattern:
```python
from metadata_foundation import MetadataContext, get_current_run_id

def main():
    run_id = get_current_run_id()
    with MetadataContext(run_id, stage_number=N, stage_name="name",
                         script_path="scripts/name.py") as ctx:
        # Existing logic
        ctx.log_metric("metric_name", value)
        ctx.log_output("data/output.json", row_count=len(data))
```
