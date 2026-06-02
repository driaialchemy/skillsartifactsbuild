"""
Calibration Dashboard - System accuracy, bias detection, and threshold tuning
"""
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from collections import defaultdict

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
def load_calibration_report(run_id=None):
    """Load calibration report for a specific run or latest."""
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
def load_run_manifest(run_id):
    manifest_path = RUNS_DIR / run_id / "run_manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))

@st.cache_data
def load_stage_metadata(run_id, stage_number):
    stage_files = list((RUNS_DIR / run_id).glob(f"stage_{stage_number:02d}_*.json"))
    if not stage_files:
        return None
    return json.loads(stage_files[0].read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------
def analyze_bias(calibration):
    """Detect system bias from error distribution."""
    if not calibration:
        return None

    error_dist = calibration.get("error_distribution", {})
    overreactions = error_dist.get("overreaction", 0)
    underreactions = error_dist.get("underreaction", 0)

    bias_type = None
    if overreactions > underreactions * 2:
        bias_type = "system too aggressive"
    elif underreactions > overreactions * 2:
        bias_type = "system too conservative"

    return {
        "overreactions": overreactions,
        "underreactions": underreactions,
        "bias_type": bias_type,
        "bias_ratio": overreactions / max(underreactions, 1)
    }

def get_threshold_health(run_id):
    """Get current threshold configuration."""
    manifest = load_run_manifest(run_id)
    if not manifest:
        return None

    thresholds = manifest.get("config", {}).get("thresholds", {})
    return thresholds

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Calibration Dashboard",
        page_icon="🎯",
        layout="wide"
    )

    st.title("🎯 Calibration Dashboard")
    st.caption("System accuracy, bias detection, and threshold recommendations")

    # Load trace index
    trace_index = load_trace_index()
    all_runs = trace_index.get("runs", {})
    latest_by_type = trace_index.get("latest_by_type", {})

    if not all_runs:
        st.warning("No pipeline runs found.")
        return

    # Run selector
    run_ids = sorted(all_runs.keys(), reverse=True)
    latest_baseline = latest_by_type.get("baseline", run_ids[0])

    selected_run = st.selectbox(
        "Select Pipeline Run",
        run_ids,
        index=run_ids.index(latest_baseline) if latest_baseline in run_ids else 0,
        format_func=lambda x: f"{x} ({all_runs[x]['run_type']}) - {all_runs[x]['status']}"
    )

    # Load calibration data
    calibration = load_calibration_report(selected_run)

    if not calibration:
        st.warning(f"No calibration report found for run: {selected_run}")
        return

    st.divider()

    # Overall metrics
    st.header("System Performance")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_rows = calibration.get("total_rows", 0)
        st.metric("Total Items", total_rows)

    with col2:
        total_exceptions = calibration.get("total_exceptions", 0)
        exception_rate = total_exceptions / total_rows if total_rows else 0
        st.metric("Exception Rate", f"{exception_rate:.1%}", delta=f"{total_exceptions} items")

    with col3:
        overall_acc = calibration.get("overall_accuracy", 0)
        st.metric("Decision Accuracy", f"{overall_acc:.1%}")

    with col4:
        error_dist = calibration.get("error_distribution", {})
        total_errors = sum(v for k, v in error_dist.items() if k != "none")
        st.metric("Total Errors", total_errors)

    st.divider()

    # Error distribution
    st.header("Error Distribution")

    error_dist = calibration.get("error_distribution", {})

    col1, col2 = st.columns([1, 2])

    with col1:
        error_df = pd.DataFrame([
            {"Error Type": k.replace("_", " ").title(), "Count": v}
            for k, v in error_dist.items()
        ])
        st.dataframe(error_df, use_container_width=True, hide_index=True)

    with col2:
        st.bar_chart(error_df.set_index("Error Type"), height=300)

    st.divider()

    # Bias detection
    st.header("Bias Analysis")

    bias = analyze_bias(calibration)
    bias_flags = calibration.get("bias_flags", [])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Overreactions", bias["overreactions"])

    with col2:
        st.metric("Underreactions", bias["underreactions"])

    with col3:
        st.metric("Bias Ratio", f"{bias['bias_ratio']:.2f}x")

    if bias["bias_type"]:
        st.warning(f"**Bias Detected:** {bias['bias_type']}")

    if bias_flags:
        st.error("**System Bias Flags:**")
        for flag in bias_flags:
            st.markdown(f"- {flag}")

    st.divider()

    # Accuracy by recommendation
    st.header("Accuracy by Recommendation")

    acc_by_rec = calibration.get("accuracy_by_recommendation", {})

    if acc_by_rec:
        rec_data = []
        for rec, data in acc_by_rec.items():
            rec_data.append({
                "Recommendation": rec.title(),
                "Accuracy": f"{data['accuracy']:.1%}",
                "Avg Decision Confidence": f"{data['average_decision_confidence']:.3f}",
                "Avg Confidence Gap": f"{data['average_confidence_gap']:.3f}"
            })

        st.dataframe(rec_data, use_container_width=True, hide_index=True)

        # Highlight low accuracy recommendations
        for rec, data in acc_by_rec.items():
            if data["accuracy"] < 0.7:
                st.warning(f"⚠️ **{rec.title()}** has low accuracy ({data['accuracy']:.1%}) - consider threshold adjustment")

    st.divider()

    # Threshold recommendations
    st.header("Threshold Recommendations")

    threshold_recs = calibration.get("threshold_recommendations", [])

    if threshold_recs:
        for idx, rec in enumerate(threshold_recs, 1):
            st.markdown(f"{idx}. {rec}")
    else:
        st.success("No threshold adjustments recommended. System is well-calibrated.")

    st.divider()

    # Current threshold configuration
    st.header("Current Thresholds")

    thresholds = get_threshold_health(selected_run)

    if thresholds:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Exception Detection")
            st.markdown(f"- **Low Confidence**: `{thresholds.get('low_confidence', '?')}`")
            st.markdown(f"- **Change Ratio**: `{thresholds.get('change_ratio', '?')}`")
            st.markdown(f"- **Volatility**: `{thresholds.get('volatility', '?')}`")
            st.markdown(f"- **Band Ratio**: `{thresholds.get('band_ratio', '?')}`")

        # Get memo generation thresholds from stage 3
        stage3 = load_stage_metadata(selected_run, 3)
        if stage3:
            memo_thresholds = stage3.get("thresholds_used", {})

            with col2:
                st.subheader("Memo Generation")
                for key, value in memo_thresholds.items():
                    st.markdown(f"- **{key.replace('_', ' ').title()}**: `{value}`")

    st.divider()

    # Recommendation simulator
    st.header("Threshold Tuning Simulator")

    st.info("Adjust thresholds to see potential impact on exception rate (simulation only - does not modify system)")

    col1, col2 = st.columns(2)

    with col1:
        new_low_conf = st.slider(
            "Low Confidence Threshold",
            min_value=0.0,
            max_value=1.0,
            value=thresholds.get("low_confidence", 0.55),
            step=0.05
        )

        new_change_ratio = st.slider(
            "Change Ratio Threshold",
            min_value=0.0,
            max_value=1.0,
            value=thresholds.get("change_ratio", 0.25),
            step=0.05
        )

    with col2:
        new_volatility = st.slider(
            "Volatility Threshold",
            min_value=0.0,
            max_value=1.0,
            value=thresholds.get("volatility", 0.25),
            step=0.05
        )

        new_band_ratio = st.slider(
            "Band Ratio Threshold",
            min_value=0.0,
            max_value=1.0,
            value=thresholds.get("band_ratio", 0.35),
            step=0.05
        )

    if st.button("💾 Export Threshold Configuration"):
        new_config = {
            "low_confidence": new_low_conf,
            "change_ratio": new_change_ratio,
            "volatility": new_volatility,
            "band_ratio": new_band_ratio
        }

        st.json(new_config)
        st.success("Copy this configuration to update pipeline thresholds")

if __name__ == "__main__":
    main()
