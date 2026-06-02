# Dashboard Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Operational Observability Dashboard            │
│                          (Streamlit Multi-Page App)                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ Home.py      │  │ Pages/       │  │ Data Sources │
        │ (Landing)    │  │ (4 pages)    │  │ (JSON files) │
        └──────────────┘  └──────────────┘  └──────────────┘
```

## Page Architecture

```
app/
├── Home.py                    # Landing page
│   ├── Load trace_index.json
│   ├── Display recent runs
│   ├── Show health metrics
│   └── Quick action buttons
│
└── pages/
    ├── 01_Trace_Explorer.py         # Metadata browser
    │   ├── Run selector
    │   ├── 4 tabs:
    │   │   ├── Overview (manifest + config)
    │   │   ├── Stages (timeline + metrics)
    │   │   ├── Summary (markdown)
    │   │   └── Raw Metadata (JSON viewer)
    │   └── Download buttons
    │
    ├── 02_Confidence_Analysis.py    # Charts & analysis
    │   ├── Confidence distribution histograms
    │   ├── Recommendation breakdown
    │   ├── Gap analysis
    │   ├── Error visualization
    │   └── Low confidence explorer
    │
    ├── 03_Calibration_Dashboard.py  # Accuracy & tuning
    │   ├── Performance metrics
    │   ├── Error distribution chart
    │   ├── Bias detection
    │   ├── Accuracy by recommendation
    │   ├── Threshold recommendations
    │   └── Tuning simulator
    │
    └── 04_Planner_Review.py         # Exception review
        ├── Review Queue tab
        │   ├── Tier filtering
        │   └── Item detail view
        ├── Audit Log tab
        │   ├── Decision history
        │   └── Export feedback
        └── Session Stats tab
            ├── Accuracy metrics
            └── Distribution charts
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Pipeline Execution                                           │
│   scripts/run_pipeline.py                                    │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Metadata Generation                                          │
│   scripts/metadata_foundation.py                             │
│   (Context managers capture run/stage metadata)              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Trace Files                                                  │
│   data/runs/{run_id}/                                        │
│   ├── run_manifest.json         (run-level metadata)        │
│   ├── stage_*.json              (stage-level metadata)      │
│   └── summary.md                (human-readable)            │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Trace Index                                                  │
│   data/traces/trace_index.json                               │
│   (Fast lookup: run_id → metadata, latest_by_type)          │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Dashboard Pages                                              │
│   app/Home.py + app/pages/*.py                               │
│   (Load JSON, render charts, provide interactivity)          │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ User Browser                                                 │
│   http://localhost:8501                                      │
│   (Interactive visualizations, filters, export buttons)      │
└─────────────────────────────────────────────────────────────┘
```

## Data Sources

```
data/
├── traces/
│   └── trace_index.json                 # Fast run lookup
│       ├── runs: {run_id → {status, duration, created_at}}
│       └── latest_by_type: {baseline → run_id, test → run_id}
│
├── runs/{run_id}/
│   ├── run_manifest.json                # Run metadata
│   │   ├── run_id, run_type, status
│   │   ├── created_at, completed_at, duration_seconds
│   │   ├── config (seed, thresholds)
│   │   └── environment (python, platform)
│   │
│   ├── stage_01_generate_forecasts.json  # Stage 1 metadata
│   ├── stage_02_detect_exceptions.json   # Stage 2 metadata
│   ├── stage_03_generate_memos.json      # Stage 3 metadata
│   ├── stage_04_score_and_rank.json      # Stage 4 metadata
│   ├── stage_05_simulate_planner_feedback.json  # Stage 5 metadata
│   ├── stage_06_calibrate_system.json    # Stage 6 metadata
│   ├── stage_07_validate_pipeline.json   # Stage 7 metadata
│   └── summary.md                        # Human-readable summary
│
├── forecasts_ranked.json                 # Latest ranked forecasts
├── forecasts_with_memos.json             # With decision memos
├── forecasts_with_feedback.json          # With planner feedback
├── calibration_report.json               # Latest calibration
└── planner_decisions.json                # Planner review decisions
```

## Page-to-Data Mapping

| Page | Primary Data Sources | Secondary Sources |
|------|----------------------|-------------------|
| **Home** | `trace_index.json`, `run_manifest.json` | `stage_02_detect_exceptions.json`, `calibration_report.json` |
| **Trace Explorer** | `run_manifest.json`, `stage_*.json` | `summary.md` |
| **Confidence Analysis** | `forecasts_with_memos.json`, `calibration_report.json` | `forecasts_with_feedback.json` |
| **Calibration Dashboard** | `calibration_report.json`, `run_manifest.json` | `stage_03_generate_memos.json` |
| **Planner Review** | `forecasts_ranked.json` | `planner_decisions.json` (writes) |

## Caching Strategy

All data loaders use Streamlit's `@st.cache_data` decorator:

```python
@st.cache_data
def load_trace_index():
    return json.loads(TRACE_INDEX_PATH.read_text(encoding="utf-8"))
```

**Benefits**:
- Files read once per session
- Instant re-renders on page navigation
- Auto-invalidation on file changes
- Reduced I/O overhead

**Cache Keys**:
- Function name
- Function arguments
- File modification time (auto-detected)

## Navigation Flow

```
┌─────────────┐
│   Home      │ ← Entry point (streamlit run app/Home.py)
└──────┬──────┘
       │
       ├──────────────────────────────────────────┐
       │                                          │
       ▼                                          ▼
┌─────────────────┐                    ┌────────────────────┐
│ Trace Explorer  │◄───────────────────┤ Quick Actions      │
│ (with run_id)   │                    │ - Explore Latest   │
└─────────────────┘                    │ - View Trends      │
                                       │ - Review Queue     │
                                       └────────────────────┘
       │
       ├───────────────┬───────────────┐
       │               │               │
       ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Confidence   │ │ Calibration  │ │ Planner      │
│ Analysis     │ │ Dashboard    │ │ Review       │
└──────────────┘ └──────────────┘ └──────────────┘
```

**State Passing**:
- Home → Trace Explorer: `st.session_state["selected_run_id"]`
- All pages: Access sidebar menu for direct navigation

## Component Breakdown

### Home Page Components

```
┌────────────────────────────────────────────────────┐
│ Header: "AI Demand Planning Analyst"              │
├────────────────────────────────────────────────────┤
│ Sidebar: Navigation menu                          │
├────────────────────────────────────────────────────┤
│ Pipeline Health Overview                          │
│   ┌──────────┬──────────┬──────────┬──────────┐  │
│   │ Latest   │ Latest   │ Success  │ Avg      │  │
│   │ Baseline │ Test     │ Rate     │ Duration │  │
│   └──────────┴──────────┴──────────┴──────────┘  │
├────────────────────────────────────────────────────┤
│ Recent Runs Table (10 rows)                       │
│   [Run ID | Type | Status | Duration | Exceptions | Accuracy | Created] │
├────────────────────────────────────────────────────┤
│ Latest Baseline Insights                          │
│   ┌──────────┬──────────┬──────────┬──────────┐  │
│   │ Exception│ Decision │ Over-    │ Bias     │  │
│   │ Rate     │ Accuracy │ reactions│ Flags    │  │
│   └──────────┴──────────┴──────────┴──────────┘  │
│   [Bias Flags Warning (if any)]                   │
│   [Threshold Recommendations (expandable)]        │
├────────────────────────────────────────────────────┤
│ Quick Actions                                      │
│   [Explore Latest Baseline] [View Trends] [Review]│
└────────────────────────────────────────────────────┘
```

### Trace Explorer Components

```
┌────────────────────────────────────────────────────┐
│ Header: "Trace Explorer"                          │
├────────────────────────────────────────────────────┤
│ Run Selector: [Dropdown with run_id + type + status] │
├────────────────────────────────────────────────────┤
│ Tabs: [Overview | Stages | Summary | Raw Metadata]│
│                                                    │
│ OVERVIEW TAB:                                      │
│   Run Overview (4 columns)                         │
│   Configuration (2 columns: Thresholds + Env)     │
│   Reproducibility (bash code block)               │
│                                                    │
│ STAGES TAB:                                        │
│   Stage Cards (one per stage)                      │
│     - Status badge, duration                       │
│     - Inputs/Outputs table                         │
│     - Metrics (4-column grid)                      │
│     - Thresholds (expandable)                      │
│                                                    │
│ SUMMARY TAB:                                       │
│   Markdown render of summary.md                    │
│   [Download Summary Button]                        │
│                                                    │
│ RAW METADATA TAB:                                  │
│   Expandable JSON viewers (run_manifest + stages) │
└────────────────────────────────────────────────────┘
```

### Confidence Analysis Components

```
┌────────────────────────────────────────────────────┐
│ Header: "Confidence Analysis"                     │
├────────────────────────────────────────────────────┤
│ Confidence Overview (4 columns)                    │
│   [Avg Confidence | Avg Decision Conf | Accuracy | Avg Gap] │
├────────────────────────────────────────────────────┤
│ Confidence Distribution (2 columns)                │
│   [Forecast Confidence Bar Chart | Decision Confidence Bar Chart] │
├────────────────────────────────────────────────────┤
│ Confidence by Recommendation                       │
│   [Table: Rec | Count | Avg Conf | Avg Dec Conf]  │
│   [Stacked Bar Chart]                              │
├────────────────────────────────────────────────────┤
│ Confidence Gap Analysis                            │
│   [Table: Rec | Accuracy | Avg Dec Conf | Avg Gap]│
│   [Gap Bar Chart]                                  │
├────────────────────────────────────────────────────┤
│ Error Analysis                                     │
│   [Table: Error Type | Count]                      │
│   [Bar Chart]                                      │
├────────────────────────────────────────────────────┤
│ Low Confidence Items                               │
│   [Threshold Slider: 0.0 - 1.0]                    │
│   [Count Metric]                                   │
│   [Table: Item ID | Confidence | Dec Conf | Rec | Tier] │
└────────────────────────────────────────────────────┘
```

### Calibration Dashboard Components

```
┌────────────────────────────────────────────────────┐
│ Header: "Calibration Dashboard"                   │
├────────────────────────────────────────────────────┤
│ Run Selector: [Dropdown]                          │
├────────────────────────────────────────────────────┤
│ System Performance (4 columns)                     │
│   [Total Items | Exception Rate | Accuracy | Total Errors] │
├────────────────────────────────────────────────────┤
│ Error Distribution (2 columns)                     │
│   [Table: Error Type | Count]                      │
│   [Bar Chart]                                      │
├────────────────────────────────────────────────────┤
│ Bias Analysis (3 columns)                          │
│   [Overreactions | Underreactions | Bias Ratio]   │
│   [Bias Warning (if detected)]                     │
│   [Bias Flags (if any)]                            │
├────────────────────────────────────────────────────┤
│ Accuracy by Recommendation                         │
│   [Table: Rec | Accuracy | Avg Dec Conf | Avg Gap]│
│   [Low Accuracy Warnings]                          │
├────────────────────────────────────────────────────┤
│ Threshold Recommendations                          │
│   [Numbered list of recommendations]              │
├────────────────────────────────────────────────────┤
│ Current Thresholds (2 columns)                     │
│   [Exception Detection | Memo Generation]         │
├────────────────────────────────────────────────────┤
│ Threshold Tuning Simulator (2 columns)            │
│   [4 Sliders for thresholds]                       │
│   [Export Threshold Configuration Button]         │
│   [JSON display]                                   │
└────────────────────────────────────────────────────┘
```

### Planner Review Components

```
┌────────────────────────────────────────────────────┐
│ Header: "Planner Review Console"                  │
├────────────────────────────────────────────────────┤
│ Quick Stats (4 columns)                            │
│   [Total Items | Exceptions | Queue | Completion] │
├────────────────────────────────────────────────────┤
│ Tabs: [Review Queue | Audit Log | Session Stats]  │
│                                                    │
│ REVIEW QUEUE TAB:                                  │
│   ┌─────────────────┬───────────────────────────┐ │
│   │ Queue (1/3)     │ Detail View (2/3)         │ │
│   │ [Tier Filter]   │ [Item Header]             │ │
│   │ [Item Buttons]  │ [Metrics: 4 columns]      │ │
│   │ ...             │ [Exception Reasons]       │ │
│   │                 │ [Priority Info]           │ │
│   │                 │ [Recommendation + Conf]   │ │
│   │                 │ [Memo]                    │ │
│   │                 │ [Sales Chart]             │ │
│   │                 │ [Reason Text Area]        │ │
│   │                 │ [Accept|Override|Inv|Esc] │ │
│   └─────────────────┴───────────────────────────┘ │
│                                                    │
│ AUDIT LOG TAB:                                     │
│   [Export Feedback | Clear All Decisions]         │
│   [Decision List (newest first)]                  │
│     - Timestamp, Item ID, Action                  │
│     - Reason (if provided)                        │
│     - Match/Mismatch badge                        │
│                                                    │
│ SESSION STATS TAB:                                 │
│   ┌──────────┬──────────┬──────────┐              │
│   │ Total    │ Action   │ Error    │              │
│   │ Decisions│ Dist.    │ Types    │              │
│   │ Matches  │          │          │              │
│   │ Accuracy │          │          │              │
│   └──────────┴──────────┴──────────┘              │
└────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Streamlit | Multi-page web app framework |
| **Data Processing** | Pandas | DataFrames for charts |
| **Visualization** | Streamlit native charts | Bar charts, line charts, metrics |
| **Data Storage** | JSON files | Metadata and pipeline outputs |
| **Caching** | `@st.cache_data` | Performance optimization |
| **State Management** | `st.session_state` | Cross-page context |

## Security & Access

- **Local-Only**: Dashboard runs on `localhost:8501`
- **Read-Only**: All pages read JSON files (except Planner Review)
- **No Authentication**: Assumes trusted local user
- **No Database**: Direct file system access
- **No External APIs**: Self-contained system

## Performance Optimization

| Technique | Implementation | Benefit |
|-----------|----------------|---------|
| **Caching** | `@st.cache_data` on all loaders | Prevents redundant file reads |
| **Lazy Loading** | Files loaded only when page accessed | Faster initial load |
| **Pagination** | First 50 items in large tables | Responsive UI |
| **Expandable Sections** | JSON viewers use `st.expander` | Cleaner UI, faster render |
| **Selective Metrics** | Only compute displayed metrics | Reduced computation |

## Scalability Considerations

| Scenario | Current Limit | Mitigation |
|----------|---------------|------------|
| **Total Runs** | ~100 runs | Trace index is O(1) lookup |
| **Items per Run** | 50-100 items | Pagination in UI |
| **Stage Metadata** | 7 stages/run | Expandable sections |
| **Dashboard Load Time** | <500ms | Caching + selective loading |

## Future Architecture Extensions

### Phase 3: Item Evolution Tracking

```
data/runs/{run_id}/item_evolution.jsonl
│
├── Line 1: {"item_id": "X", "stage": 1, "confidence_score": 0.4}
├── Line 2: {"item_id": "X", "stage": 3, "decision_confidence": 0.1}
└── Line 3: {"item_id": "X", "stage": 4, "priority_tier": "critical"}
```

**Dashboard Integration**: New page "Item Evolution" with timeline visualization

### Phase 4: Health Dashboard

```
data/traces/health_dashboard.md
│
├── Rolling 24h metrics
├── Anomaly flags
└── Drift detection vs baseline
```

**Dashboard Integration**: New section on Home page with alerts

### Phase 6: Batch Comparison

```
Dashboard Page: "Run Comparison"
│
├── Select 2-5 runs
├── Side-by-side metric comparison
└── Trend charts over time
```

## Deployment Notes

**Local Development**:
```bash
streamlit run app/Home.py
```

**Production (if needed)**:
```bash
streamlit run app/Home.py --server.port 8501 --server.address 0.0.0.0
```

**Docker (future)**:
```dockerfile
FROM python:3.11
RUN pip install streamlit pandas
COPY . /app
WORKDIR /app
CMD ["streamlit", "run", "app/Home.py"]
```

---

**For implementation details, see**: `docs/OBSERVABILITY_DASHBOARD.md`
