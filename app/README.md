# AI Demand Planning Analyst - Observability Dashboard

Interactive local dashboard for inspecting pipeline execution traces, metadata, and operational metrics.

## Quick Start

```bash
# From project root
streamlit run app/Home.py
```

The dashboard will open in your browser at `http://localhost:8501`.

## Dashboard Pages

### 🏠 Home
**Purpose**: Pipeline health overview and quick navigation

**Features**:
- Recent runs summary table
- Success rate and average duration metrics
- Latest baseline insights (exceptions, accuracy, bias flags)
- Quick action buttons to explore specific runs

**Use When**: You want a high-level view of system health

---

### 🔍 Trace Explorer
**Purpose**: Deep dive into pipeline execution metadata

**Features**:
- Browse all pipeline runs with detailed filters
- View run manifests and configuration
- Inspect stage-by-stage execution timeline
- Download human-readable summaries
- View raw JSON metadata with syntax highlighting

**Use When**:
- Debugging a specific run
- Understanding stage-level metrics (duration, row counts, thresholds)
- Auditing input file hashes for reproducibility
- Exporting run summaries for reports

**Navigation**:
1. Select run from dropdown
2. Explore tabs:
   - **Overview**: Run metadata, config, reproducibility commands
   - **Stages**: Timeline view with inputs, outputs, metrics, thresholds
   - **Summary**: Human-readable markdown report
   - **Raw Metadata**: JSON viewer for all metadata files

---

### 📈 Confidence Analysis
**Purpose**: Visualize confidence scores, gaps, and calibration

**Features**:
- Confidence distribution histograms
- Confidence by recommendation breakdown
- Confidence gap analysis (from calibration)
- Error type distribution
- Low confidence item explorer with adjustable threshold

**Use When**:
- Investigating why certain items have low decision confidence
- Understanding calibration gaps between system and planner
- Analyzing error patterns (overreaction vs underreaction)
- Finding items that need threshold tuning

**Key Metrics**:
- **Confidence Score**: System's forecast confidence (0-1)
- **Decision Confidence**: Predicted planner agreement (0-1)
- **Confidence Gap**: Difference between predicted and actual agreement

---

### 🎯 Calibration Dashboard
**Purpose**: System accuracy, bias detection, and threshold tuning

**Features**:
- Overall system performance metrics
- Error distribution visualization
- Bias detection (aggressive vs conservative)
- Accuracy by recommendation type
- Threshold recommendations from calibration
- Interactive threshold tuning simulator
- Export threshold configurations

**Use When**:
- System shows bias flags in calibration reports
- Accuracy drops below acceptable levels
- You need to adjust exception detection thresholds
- Planning threshold changes for next pipeline run

**Critical Alerts**:
- Accuracy < 70% for any recommendation type → threshold adjustment needed
- Overreaction/underreaction ratio > 2x → system bias detected

---

### ✅ Planner Review
**Purpose**: Interactive exception review and decision recording

**Features**:
- Exception queue filtered by priority tier
- Item detail view with sales charts and memos
- Four-button decision workflow (Accept/Override/Investigate/Escalate)
- Audit log with decision timestamps and error classification
- Session statistics (accuracy, action distribution, error types)
- Export feedback to JSON

**Use When**:
- Reviewing exceptions flagged by the system
- Recording planner decisions for calibration
- Comparing system recommendations vs planner judgment

**Workflow**:
1. Select item from queue (auto-sorted by priority tier)
2. Review: forecast, confidence, memo, sales history
3. Decide: Accept/Override/Investigate/Escalate
4. (Optional) Export feedback for next calibration run

**Decision Rules**:
- **Accept**: System recommendation is correct
- **Override**: (≥10 chars reason) Planner overrules system
- **Investigate**: (≥10 chars reason) Needs more analysis
- **Escalate**: (optional reason) Escalate to senior planner

---

## Data Sources

The dashboard reads from the following directories:

```
data/
├── traces/
│   └── trace_index.json              # Fast run lookup
├── runs/{run_id}/
│   ├── run_manifest.json              # Run-level metadata
│   ├── stage_XX_name.json             # Stage-level metadata
│   └── summary.md                     # Human-readable summary
├── forecasts_ranked.json              # Latest ranked forecasts
├── forecasts_with_memos.json          # Forecasts with decision memos
├── forecasts_with_feedback.json       # Forecasts with planner feedback
└── calibration_report.json            # Latest calibration report
```

**Note**: The dashboard is read-only except for the Planner Review page, which writes to `planner_decisions.json`.

---

## Common Workflows

### 1. Debugging a Failed Run
1. Go to **Home** → Recent Runs table
2. Click failed run ID
3. Navigate to **Trace Explorer**
4. Check **Stages** tab for error details
5. View **Raw Metadata** for full error context

### 2. Investigating Low Accuracy
1. Go to **Calibration Dashboard**
2. Check **Error Distribution** for patterns
3. Review **Accuracy by Recommendation**
4. Note threshold recommendations
5. Use **Threshold Tuning Simulator** to test adjustments
6. Export new threshold config

### 3. Analyzing Confidence Issues
1. Go to **Confidence Analysis**
2. Check **Confidence Distribution** histograms
3. Identify low confidence items with slider
4. Cross-reference with **Confidence Gap** analysis
5. Export list of problematic items

### 4. Reviewing Exceptions
1. Go to **Planner Review**
2. Filter by priority tier (start with critical)
3. Review item details and memo
4. Make decisions (Accept/Override/Investigate/Escalate)
5. Check **Session Stats** tab for accuracy
6. Export feedback when done

---

## Reproducibility

Every run displayed in the Trace Explorer includes reproducibility instructions:

```bash
export PIPELINE_RUN_ID=20260509-150917-42-baseline
export PIPELINE_SEED=42
python scripts/run_pipeline.py --type baseline --seed 42
```

This guarantees deterministic reproduction of any run.

---

## Troubleshooting

### "No pipeline runs found"
- Run the pipeline: `python scripts/run_pipeline.py --type baseline`
- Check `data/traces/trace_index.json` exists
- Verify `data/runs/` directory contains run folders

### "No calibration report found"
- Ensure pipeline completed stage 6 (calibrate_system)
- Check for `data/calibration_report.json`
- Verify run includes `stage_06_calibrate_system.json`

### "No forecast data found"
- Run full pipeline to generate `forecasts_ranked.json`
- Check `data/forecasts_with_memos.json` exists

### Page not loading
- Refresh browser (Ctrl+R)
- Clear Streamlit cache: Click "⋮" menu → "Clear cache"
- Restart Streamlit: Ctrl+C and re-run `streamlit run app/Home.py`

---

For more information, see:
- **Implementation Summary**: `docs/IMPLEMENTATION_SUMMARY.md`
- **Metadata Schema**: `docs/METADATA_FOUNDATION.md`
- **Quick Reference**: `docs/METADATA_QUICK_REFERENCE.md`
