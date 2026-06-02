# Metadata Foundation Layer - README

## Quick Start

### Run the Pipeline
```bash
python scripts/run_pipeline.py --type baseline
```

### View Results
```bash
# Latest baseline run
LATEST=$(jq -r '.latest_by_type.baseline' data/traces/trace_index.json)

# View summary
cat "data/runs/$LATEST/summary.md"

# View specific metrics
jq '.metrics' "data/runs/$LATEST/stage_02_detect_exceptions.json"
```

## What This Does

The Metadata Foundation Layer adds **complete execution traceability** to the AI demand planning pipeline without changing any existing behavior.

### For Each Pipeline Run You Get:

1. **Run Manifest** - Overall execution metadata
   - Status, duration, timestamp
   - Configuration used (seed, thresholds)
   - Environment details

2. **Stage Metadata** (7 files) - Per-stage details
   - Inputs/outputs with MD5 hashes
   - Metrics (exception rates, accuracy, etc.)
   - Thresholds used
   - Execution duration

3. **Human Summary** - Readable overview
   - Stage execution table
   - Key metrics summary
   - Reproducibility instructions

4. **Trace Index** - Fast lookup
   - Latest run by type
   - All historical runs

## Directory Structure

```
data/
├── runs/
│   └── 20260509-150917-42-baseline/    # Each run gets its own directory
│       ├── run_manifest.json           # Run-level metadata
│       ├── stage_01_generate_forecasts.json
│       ├── stage_02_detect_exceptions.json
│       ├── ... (7 stage files total)
│       └── summary.md                  # Human-readable
├── traces/
│   └── trace_index.json                # Fast run lookup
└── [existing files unchanged]
    ├── forecasts.json
    └── forecasts_ranked.json
```

## Documentation

- **[Full Documentation](METADATA_FOUNDATION.md)** - Complete reference
- **[Quick Reference](METADATA_QUICK_REFERENCE.md)** - Common commands
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - What was built

## Key Features

✓ **Deterministic run IDs** - Reproducible with same seed
✓ **Complete metrics** - 20+ metrics captured per run
✓ **MD5 verification** - Input integrity checking
✓ **Zero breaking changes** - Existing code/data unchanged
✓ **Human + machine readable** - Markdown + JSON

## Example: Query Pipeline Accuracy

```bash
# Get accuracy from latest baseline
LATEST=$(jq -r '.latest_by_type.baseline' data/traces/trace_index.json)
jq '.metrics.overall_accuracy' "data/runs/$LATEST/stage_06_calibrate_system.json"

# Output: 0.86
```

## Example: Reproduce a Run

```bash
# From any run's summary.md or manifest
export PIPELINE_RUN_ID=20260509-150917-42-baseline
export PIPELINE_SEED=42

python scripts/generate_forecasts.py
python scripts/detect_exceptions.py
# ... all stages
```

## Verification

```bash
# Run comprehensive verification
python scripts/verify_metadata_foundation.py

# Should output: SUCCESS: Metadata Foundation Layer is correctly implemented!
```

## Status

**Implementation**: ✓ Complete (Phases 1-2)
**Scripts Instrumented**: 7/7 (all pipeline stages)
**Verification**: ✓ All checks passing

## Next Steps (Not Yet Implemented)

- **Phase 3**: Item-level evolution tracking
- **Phase 4**: Health dashboard and drift detection
- **Phase 5**: Diagnostic script integration
- **Phase 6**: Advanced observability and alerts

## Need Help?

1. Check [Quick Reference](METADATA_QUICK_REFERENCE.md) for common tasks
2. Read [Full Documentation](METADATA_FOUNDATION.md) for details
3. Run `python scripts/verify_metadata_foundation.py` to check setup
