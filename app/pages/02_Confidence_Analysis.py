"""
Confidence Analysis - Visualize confidence scores, gaps, and evolution
"""
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from data_loading import load_json_payload

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.parent
TRACE_INDEX_PATH = PROJECT_ROOT / "data" / "traces" / "trace_index.json"
RUNS_DIR = PROJECT_ROOT / "data" / "runs"
DATA_DIR = PROJECT_ROOT / "data"

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
@st.cache_data
def load_trace_index():
    if not TRACE_INDEX_PATH.exists():
        return {"schema_version": "1.0", "runs": {}, "latest_by_type": {}}
    return json.loads(TRACE_INDEX_PATH.read_text(encoding="utf-8"))

@st.cache_data
def load_forecasts_with_memos():
    """Load the forecast data with decision confidence."""
    path = DATA_DIR / "forecasts_with_memos.json"
    if not path.exists():
        return None
    return load_json_payload(path, data_key="forecasts")

@st.cache_data
def load_calibration_report(run_id=None):
    """Load calibration report."""
    if run_id:
        path = RUNS_DIR / run_id / "calibration_report.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))

    # Fall back to root calibration
    path = DATA_DIR / "calibration_report.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None

@st.cache_data
def load_forecasts_with_feedback():
    """Load forecasts with planner feedback for error analysis."""
    path = DATA_DIR / "forecasts_with_feedback.json"
    if not path.exists():
        return None
    return load_json_payload(path, data_key="forecasts")

# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------
def analyze_confidence_distribution(forecasts):
    """Analyze distribution of confidence scores."""
    confidence_scores = [f["confidence_score"] for f in forecasts]
    decision_confidences = [f.get("decision_confidence", 0) for f in forecasts]

    return {
        "confidence_scores": confidence_scores,
        "decision_confidences": decision_confidences,
        "avg_confidence": sum(confidence_scores) / len(confidence_scores),
        "avg_decision_confidence": sum(decision_confidences) / len(decision_confidences),
    }

def analyze_confidence_by_recommendation(forecasts):
    """Break down confidence by recommendation type."""
    by_rec = defaultdict(list)
    for f in forecasts:
        rec = f.get("recommendation", "accept")
        by_rec[rec].append({
            "confidence_score": f["confidence_score"],
            "decision_confidence": f.get("decision_confidence", 0)
        })
    return dict(by_rec)

def analyze_confidence_gaps(calibration):
    """Extract confidence gap analysis from calibration report."""
    if not calibration:
        return None

    acc_by_rec = calibration.get("accuracy_by_recommendation", {})
    gaps = []

    for rec, data in acc_by_rec.items():
        gaps.append({
            "recommendation": rec,
            "accuracy": data["accuracy"],
            "avg_decision_confidence": data["average_decision_confidence"],
            "avg_confidence_gap": data["average_confidence_gap"]
        })

    return sorted(gaps, key=lambda x: x["avg_confidence_gap"], reverse=True)

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Confidence Analysis",
        page_icon="📈",
        layout="wide"
    )

    st.title("📈 Confidence Analysis")
    st.caption("Visualize confidence scores, gaps, and calibration")

    # Load data
    forecasts = load_forecasts_with_memos()
    calibration = load_calibration_report()
    feedback_data = load_forecasts_with_feedback()

    if not forecasts:
        st.warning("No forecast data found. Run the pipeline first.")
        st.code("python scripts/run_pipeline.py --type baseline", language="bash")
        return

    st.divider()

    # Overview metrics
    st.header("Confidence Overview")

    dist = analyze_confidence_distribution(forecasts)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Avg Confidence Score", f"{dist['avg_confidence']:.3f}")

    with col2:
        st.metric("Avg Decision Confidence", f"{dist['avg_decision_confidence']:.3f}")

    with col3:
        if calibration:
            overall_acc = calibration.get("overall_accuracy", 0)
            st.metric("Overall Accuracy", f"{overall_acc:.1%}")

    with col4:
        if calibration:
            avg_gap = sum(
                data["average_confidence_gap"]
                for data in calibration.get("accuracy_by_recommendation", {}).values()
            ) / max(len(calibration.get("accuracy_by_recommendation", {})), 1)
            st.metric("Avg Confidence Gap", f"{avg_gap:.3f}")

    st.divider()

    # Distribution charts
    st.header("Confidence Distribution")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Forecast Confidence Score")
        confidence_df = pd.DataFrame({
            "Confidence Score": dist["confidence_scores"]
        })
        st.bar_chart(confidence_df["Confidence Score"].value_counts().sort_index(), height=300)

    with col2:
        st.subheader("Decision Confidence")
        decision_df = pd.DataFrame({
            "Decision Confidence": dist["decision_confidences"]
        })
        st.bar_chart(decision_df["Decision Confidence"].value_counts().sort_index(), height=300)

    st.divider()

    # Confidence by recommendation
    st.header("Confidence by Recommendation")

    by_rec = analyze_confidence_by_recommendation(forecasts)

    rec_data = []
    for rec, items in by_rec.items():
        avg_conf = sum(i["confidence_score"] for i in items) / len(items)
        avg_dec_conf = sum(i["decision_confidence"] for i in items) / len(items)
        rec_data.append({
            "Recommendation": rec.title(),
            "Count": len(items),
            "Avg Confidence": f"{avg_conf:.3f}",
            "Avg Decision Confidence": f"{avg_dec_conf:.3f}"
        })

    st.dataframe(rec_data, use_container_width=True, hide_index=True)

    # Chart
    chart_data = pd.DataFrame([
        {"Recommendation": r["Recommendation"], "Metric": "Confidence", "Value": float(r["Avg Confidence"])}
        for r in rec_data
    ] + [
        {"Recommendation": r["Recommendation"], "Metric": "Decision Confidence", "Value": float(r["Avg Decision Confidence"])}
        for r in rec_data
    ])

    st.bar_chart(chart_data.pivot(index="Recommendation", columns="Metric", values="Value"), height=300)

    st.divider()

    # Confidence gaps (from calibration)
    if calibration:
        st.header("Confidence Gap Analysis")

        gaps = analyze_confidence_gaps(calibration)

        if gaps:
            gap_df = pd.DataFrame(gaps)
            gap_df["accuracy"] = gap_df["accuracy"].apply(lambda x: f"{x:.1%}")
            gap_df["avg_decision_confidence"] = gap_df["avg_decision_confidence"].apply(lambda x: f"{x:.3f}")
            gap_df["avg_confidence_gap"] = gap_df["avg_confidence_gap"].apply(lambda x: f"{x:.3f}")

            st.dataframe(gap_df.rename(columns={
                "recommendation": "Recommendation",
                "accuracy": "Accuracy",
                "avg_decision_confidence": "Avg Decision Confidence",
                "avg_confidence_gap": "Avg Confidence Gap"
            }), use_container_width=True, hide_index=True)

            # Visualize gaps
            st.subheader("Confidence Gap by Recommendation")
            gap_chart_data = pd.DataFrame([
                {"Recommendation": g["recommendation"].title(), "Confidence Gap": g["avg_confidence_gap"]}
                for g in gaps
            ])
            st.bar_chart(gap_chart_data.set_index("Recommendation"), height=300)

    st.divider()

    # Error type distribution (if feedback available)
    if feedback_data:
        st.header("Error Analysis")

        error_counts = defaultdict(int)
        for item in feedback_data:
            error_type = item.get("error_type", "none")
            error_counts[error_type] += 1

        error_df = pd.DataFrame([
            {"Error Type": et.replace("_", " ").title(), "Count": count}
            for et, count in error_counts.items()
        ])

        col1, col2 = st.columns([1, 2])

        with col1:
            st.dataframe(error_df, use_container_width=True, hide_index=True)

        with col2:
            st.bar_chart(error_df.set_index("Error Type"), height=300)

    st.divider()

    # Low confidence items
    st.header("Low Confidence Items")

    low_conf_threshold = st.slider(
        "Confidence Threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.55,
        step=0.05
    )

    low_conf_items = [f for f in forecasts if f["confidence_score"] < low_conf_threshold]

    st.metric("Items Below Threshold", f"{len(low_conf_items)}/{len(forecasts)}")

    if low_conf_items:
        low_conf_df = pd.DataFrame([
            {
                "Item ID": item["item_id"],
                "Confidence": f"{item['confidence_score']:.3f}",
                "Decision Confidence": f"{item.get('decision_confidence', 0):.3f}",
                "Recommendation": item.get("recommendation", "accept").title(),
                "Priority Tier": item.get("priority_tier", "none")
            }
            for item in low_conf_items[:50]  # Show first 50
        ])

        st.dataframe(low_conf_df, use_container_width=True, hide_index=True)

        if len(low_conf_items) > 50:
            st.info(f"Showing first 50 of {len(low_conf_items)} low confidence items.")

if __name__ == "__main__":
    main()
