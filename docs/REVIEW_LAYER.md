# Human-in-the-Loop Review Layer

## Overview

The Human-in-the-Loop Review Layer transforms human review decisions into structured metadata artifacts that can be used for system improvement, governance, and calibration. The design is **fully backward compatible** with existing workflows while adding powerful new capabilities.

## Key Features

### 1. Session Tracking
- Track review sessions with unique IDs
- Capture reviewer identity and session context
- Record review duration and metrics
- Generate session summaries automatically

### 2. Queue Management
Six specialized review queues with automatic filtering:

| Queue | Icon | Description |
|-------|------|-------------|
| **Priority Exceptions** | 🚨 | Critical and high-priority items requiring immediate attention |
| **Low Confidence** | ⚠️ | Items where the system has low confidence (< 0.4) |
| **High-Risk Auto-Accepts** | 🔍 | Accepted items with high risk or low confidence |
| **Random Sample QA** | 🎲 | Randomly sampled items for quality assurance |
| **Escalated Returns** | ↩️ | Previously escalated items returning for re-review |
| **All Exceptions** | 📋 | All flagged exceptions (default view) |

### 3. Structured Annotations

Optional metadata capture system with three taxonomies:

#### Override Tags
Why are you making this decision?
- **Data Quality**: outlier, missing data, supplier disruption, etc.
- **Seasonal Adjustment**: holiday shift, weather event, local event
- **Business Knowledge**: category manager input, new product launch, competitor action
- **Model Limitation**: low history, volatility not captured, trend reversal
- **Risk Adjustment**: stockout prevention, excess inventory risk

#### Failure Taxonomy
What went wrong with the system?
- **Data Quality**: outlier, missing feature, data lag, measurement error
- **Model Error**: underconfident correct, overconfident wrong, systematic bias
- **Decision Logic**: wrong threshold, missing exception rule
- **Context Missing**: business rule not encoded, domain knowledge gap

#### Disagreement Classification
Why do you disagree with the system?
- **Underreaction**: planner saw risk model missed, advance information, model too confident
- **Overreaction**: model too sensitive, exception rule too broad, planner risk tolerant
- **Judgment Difference**: risk tolerance, action preference, business context

### 4. Review Analytics

Real-time analytics and visualizations:
- Override tag frequency analysis
- Failure taxonomy distribution
- Disagreement type breakdown
- Annotation coverage metrics
- Top override reasons

### 5. Governance Reporting

Automated governance reports:
- **Override Audit**: All overrides with reasons and patterns
- **Disagreement Analysis**: System vs. planner disagreement patterns
- **Session Summaries**: Per-session review activity
- **Daily Summaries**: Aggregated daily review metrics
- **Reviewer Activity**: Per-reviewer performance and patterns

## File Structure

```
data/
├── planner_decisions.json              # All decisions (backward compatible)
├── planner_feedback_export.json        # Calibration export (unchanged)
│
├── review_sessions/                    # Session tracking
│   ├── session_index.json
│   └── session-{timestamp}-{reviewer}.json
│
├── review_annotations/                 # Annotation indexing
│   ├── annotation_index.json
│   └── annotations_export.json
│
└── review_summaries/                   # Generated reports
    ├── daily/
    │   └── {YYYY-MM-DD}_review_summary.md
    ├── by_reviewer/
    │   └── {reviewer_id}_activity.md
    └── governance/
        ├── override_audit.md
        └── disagreement_analysis.md

app/lib/                                # Core libraries
├── review_session_manager.py           # Session lifecycle management
├── queue_manager.py                    # Queue filtering and sorting
├── annotation_taxonomy.py              # Structured taxonomies
├── annotation_manager.py               # Annotation indexing
└── summary_generator.py                # Report generation

scripts/
├── generate_review_sample.py           # QA sampling
└── generate_daily_review_summary.py    # Daily summary generation
```

## Usage Guide

### Starting a Review Session

1. Open the Planner Review page
2. In the sidebar, enter your Reviewer ID
3. Click "Start Session"
4. The session will track all your reviews

### Reviewing Items

1. Select a queue from the dropdown:
   - Start with **Priority Exceptions** for critical items
   - Use **Low Confidence** for items needing extra attention
   - Use **Random Sample QA** for quality checks

2. Select an item from the queue

3. Review the forecast details:
   - Point forecast, confidence, range
   - Exception reasons
   - Priority tier and score
   - System recommendation
   - Planner memo

4. (Optional) Add structured annotations:
   - Click "Add Structured Annotations"
   - Select override tags (why you're deciding)
   - Choose failure taxonomy (if system wrong)
   - Classify disagreement (if you disagree)

5. Make your decision:
   - **Accept**: Agree with the forecast
   - **Override**: Disagree (requires ≥10 char reason)
   - **Investigate**: Need more information (requires ≥10 char reason)
   - **Escalate**: Send to higher authority (optional reason)

### Ending a Session

1. Click "End Session" in the sidebar
2. Session data is saved automatically
3. Generate a session summary from the Audit Log tab

### Generating Reports

#### Session Summary
- Go to **Audit Log** tab
- Click "📄 Generate Session Summary"
- Summary saved to `data/review_summaries/daily/`

#### Governance Reports
- Go to **Review Analytics** tab
- Click "📋 Generate Override Audit" or "📊 Generate Disagreement Analysis"
- Reports saved to `data/review_summaries/governance/`

#### Daily Summary
Run from command line:
```bash
python scripts/generate_daily_review_summary.py 2026-05-09
```

### Viewing Analytics

Go to the **Review Analytics** tab to see:
- Annotation coverage rate
- Override tag distribution
- Failure taxonomy breakdown
- Disagreement type analysis
- Top override reasons

## Decision Record Schema

### Backward Compatible Base Record

All existing fields are preserved:

```json
{
  "item_id": "HOUSEHOLD_1_012",
  "timestamp": "2026-05-09T22:39:27Z",
  "planner_action": "override",
  "decision_match": false,
  "confidence_gap": 0.89,
  "error_type": "underreaction",
  "reason": "Supplier disruption expected"
}
```

### Enhanced Record with Metadata

New optional `decision_metadata` field:

```json
{
  "item_id": "HOUSEHOLD_1_012",
  "timestamp": "2026-05-09T22:39:27Z",
  "planner_action": "override",
  "decision_match": false,
  "confidence_gap": 0.89,
  "error_type": "underreaction",
  "reason": "Supplier disruption expected",

  "decision_metadata": {
    "schema_version": "1.0",
    "session_id": "session-20260509-223900-user123",
    "reviewer_id": "user123",
    "review_queue_type": "priority_exceptions",
    "review_duration_seconds": 45.2,

    "override_tags": [
      "data_quality/supplier_disruption",
      "business_knowledge/category_manager_input"
    ],

    "failure_taxonomy": {
      "category": "context_missing",
      "subcategory": "external_factor_unknown",
      "severity": "medium"
    },

    "disagreement_classification": {
      "type": "underreaction",
      "reason_category": "planner_saw_risk_model_missed",
      "confidence_in_override": "high"
    }
  }
}
```

## Scripts

### Generate QA Sample

Create a stratified random sample for quality assurance:

```bash
python scripts/generate_review_sample.py
```

This generates:
- `data/forecasts_with_qa_sample.json` - Forecasts with `_sampled_for_qa` metadata
- `data/review_summaries/qa_sample_report.md` - Sample distribution report

Use the **Random Sample QA** queue to review these items.

### Generate Daily Summary

Aggregate all sessions for a date:

```bash
python scripts/generate_daily_review_summary.py 2026-05-09
```

Generates `data/review_summaries/daily/2026-05-09_review_summary.md`

## Integration with Calibration

The review layer feeds back into the calibration system:

1. **Decision Records** → `planner_feedback_export.json` (unchanged)
2. **Annotations** → `annotation_index.json` (new, for detailed analysis)
3. **Session Data** → Session summaries (new, for governance)

### Using Annotations for Calibration

```python
from app.lib.annotation_manager import AnnotationManager

# Load annotations
ann_manager = AnnotationManager(Path("data"))
decisions = json.loads(Path("data/planner_decisions.json").read_text())

# Build annotation index
index = ann_manager.build_annotation_index(decisions)

# Analyze failure patterns
failure_dist = index["summary_statistics"]["failure_taxonomy_distribution"]
print("Top failure categories:", failure_dist["by_category"])

# Filter decisions by specific failure type
data_quality_failures = [
    ann for ann in index["annotations"]
    if ann.get("failure_taxonomy", {}).get("category") == "data_quality"
]

# Use for targeted model improvements
for failure in data_quality_failures:
    print(f"Item {failure['item_id']}: {failure['failure_taxonomy']}")
```

## Backward Compatibility

### Legacy Decisions Work Unchanged

Existing code that reads/writes decisions continues to work:

```python
# This still works perfectly
decisions = json.loads(Path("data/planner_decisions.json").read_text())
for d in decisions:
    print(f"{d['item_id']}: {d['planner_action']}")
```

### Graceful Degradation

- Sessions are **optional** - can review without starting a session
- Annotations are **optional** - can skip all annotation panels
- Old decision records without `decision_metadata` work fine
- New records with `decision_metadata` are backward compatible

## Best Practices

### 1. Use Sessions for Focused Work

Start a session when:
- Clearing a specific queue (e.g., priority exceptions)
- Doing a QA review batch
- Working on a specific time block

Don't start a session for:
- Quick single-item checks
- Exploratory browsing

### 2. Add Annotations Strategically

Use annotations when:
- You override the system (helps identify improvement areas)
- The system made a clear error (helps categorize failures)
- You have unique knowledge not in the data (helps encode business rules)

Skip annotations when:
- Time is critical and you need to clear queue fast
- The decision is straightforward and matches the system

### 3. Generate Reports Regularly

- **Session summaries**: After each focused review session
- **Daily summaries**: At end of day or next morning
- **Governance reports**: Weekly or monthly for stakeholders

### 4. Review Analytics to Improve

Use the Review Analytics tab to:
- Identify common override patterns
- Spot systematic model failures
- Train new reviewers on common issues
- Guide model improvement priorities

## Troubleshooting

### Session Not Saving

**Problem**: End Session button doesn't create file

**Solution**: Check that `data/review_sessions/` directory exists and is writable

### Queue Shows No Items

**Problem**: Queue selector shows 0 items

**Solution**:
- Check if you're using the right queue type
- Verify forecasts have the required metadata (`priority_tier`, `decision_confidence`, etc.)
- Try "All Exceptions" queue to see all items

### Annotations Not Appearing in Analytics

**Problem**: Review Analytics shows "No annotations yet"

**Solution**:
- Verify you're using the annotation panel (expand "Add Structured Annotations")
- Check that decisions were saved after adding annotations
- Reload the page to refresh analytics

### Reports Missing Data

**Problem**: Generated reports show incomplete data

**Solution**:
- Ensure decisions have been exported: Click "Export Feedback" in Audit Log
- Check that session was ended properly before generating summary
- Verify report file path is correct and directory is writable

## Future Enhancements

Potential Phase 7+ features:

1. **Calibration Feedback Loop**: Automatically adjust model based on annotation patterns
2. **Inter-Reviewer Agreement**: Track agreement between multiple reviewers
3. **Reviewer Training Mode**: Guided training with feedback for new reviewers
4. **Anomaly Detection**: Flag unusual review patterns for quality control
5. **Batch Operations**: Bulk accept/override with shared annotations
6. **Custom Queues**: User-defined queue filters and sorting

## Support

For issues, questions, or suggestions:
1. Check this documentation
2. Review example session summaries in `data/review_summaries/`
3. Examine decision records in `data/planner_decisions.json`
4. Consult governance reports for usage patterns

---

**Version**: 1.0.0
**Last Updated**: 2026-05-09
**Status**: Production Ready
