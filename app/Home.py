"""
AI Demand Planning Analyst - Operational Observability Dashboard

Main landing page with pipeline health overview and quick navigation.
"""
import json
import streamlit as st
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
TRACE_INDEX_PATH = PROJECT_ROOT / "data" / "traces" / "trace_index.json"
RUNS_DIR = PROJECT_ROOT / "data" / "runs"

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
@st.cache_data
def load_trace_index():
    if not TRACE_INDEX_PATH.exists():
        return {"schema_version": "1.0", "runs": {}, "latest_by_type": {}}
    return json.loads(TRACE_INDEX_PATH.read_text(encoding="utf-8"))

@st.cache_data
def load_run_manifest(run_id):
    manifest_path = RUNS_DIR / run_id / "run_manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))

@st.cache_data
def load_calibration_report(run_id):
    # Try run-specific calibration first
    calib_path = RUNS_DIR / run_id / "calibration_report.json"
    if calib_path.exists():
        return json.loads(calib_path.read_text(encoding="utf-8"))
    # Fall back to root data/ directory
    calib_path = PROJECT_ROOT / "data" / "calibration_report.json"
    if calib_path.exists():
        return json.loads(calib_path.read_text(encoding="utf-8"))
    return None

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def render_status_badge(status):
    color_map = {"success": "🟢", "failed": "🔴", "partial": "🟡"}
    return color_map.get(status, "⚪")

def render_run_type_badge(run_type):
    emoji_map = {
        "baseline": "📊",
        "test": "🧪",
        "stress": "⚡",
        "noise-mild": "🌫️",
        "noise-moderate": "☁️",
        "noise-targeted": "🌩️",
    }
    return emoji_map.get(run_type, "📁")

def format_duration(seconds):
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    return f"{seconds:.2f}s"

def render_metric_card(label, value, delta=None, help_text=None):
    st.metric(label=label, value=value, delta=delta, help=help_text)

# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="AI Demand Planning - Observability Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("📊 AI Demand Planning Analyst")
    st.caption("Operational Observability Dashboard")

    # Load trace index
    trace_index = load_trace_index()
    all_runs = trace_index.get("runs", {})
    latest_by_type = trace_index.get("latest_by_type", {})

    if not all_runs:
        st.warning("No pipeline runs found. Run the pipeline to generate metadata.")
        st.code("python scripts/run_pipeline.py --type baseline", language="bash")
        return

    # Sidebar: Quick navigation
    with st.sidebar:
        st.header("Navigation")
        st.page_link("Home.py", label="🏠 Home", icon="🏠")
        st.page_link("pages/01_Trace_Explorer.py", label="🔍 Trace Explorer", icon="🔍")
        st.page_link("pages/02_Confidence_Analysis.py", label="📈 Confidence Analysis", icon="📈")
        st.page_link("pages/03_Calibration_Dashboard.py", label="🎯 Calibration", icon="🎯")
        st.page_link("pages/04_Planner_Review.py", label="✅ Planner Review", icon="✅")

        st.divider()
        st.caption(f"Total Runs: {len(all_runs)}")

    # Overview metrics
    st.header("Pipeline Health Overview")

    # Latest runs by type
    col1, col2, col3, col4 = st.columns(4)

    latest_baseline = latest_by_type.get("baseline")
    latest_test = latest_by_type.get("test")

    with col1:
        if latest_baseline:
            run_data = all_runs[latest_baseline]
            st.metric(
                "Latest Baseline",
                render_status_badge(run_data["status"]) + " " + run_data["status"].title(),
                delta=format_duration(run_data["duration_seconds"])
            )
        else:
            st.metric("Latest Baseline", "—")

    with col2:
        if latest_test:
            run_data = all_runs[latest_test]
            st.metric(
                "Latest Test",
                render_status_badge(run_data["status"]) + " " + run_data["status"].title(),
                delta=format_duration(run_data["duration_seconds"])
            )
        else:
            st.metric("Latest Test", "—")

    with col3:
        success_count = sum(1 for r in all_runs.values() if r["status"] == "success")
        success_rate = success_count / len(all_runs) if all_runs else 0
        st.metric("Success Rate", f"{success_rate:.1%}", delta=f"{success_count}/{len(all_runs)}")

    with col4:
        avg_duration = sum(r["duration_seconds"] for r in all_runs.values()) / len(all_runs)
        st.metric("Avg Duration", format_duration(avg_duration))

    st.divider()

    # Recent runs table
    st.subheader("Recent Runs")

    runs_list = []
    for run_id, run_data in sorted(all_runs.items(), key=lambda x: x[1]["created_at"], reverse=True)[:10]:
        manifest = load_run_manifest(run_id)

        # Get exception and accuracy metrics if available
        exception_count = "—"
        accuracy = "—"

        if manifest:
            stages_completed = manifest.get("stages_completed", 0)

            # Try to get exception count from stage 2
            stage2_path = RUNS_DIR / run_id / "stage_02_detect_exceptions.json"
            if stage2_path.exists():
                stage2 = json.loads(stage2_path.read_text(encoding="utf-8"))
                exception_count = stage2.get("metrics", {}).get("exceptions_detected", "—")

            # Try to get accuracy from calibration
            calib = load_calibration_report(run_id)
            if calib:
                accuracy = f"{calib.get('overall_accuracy', 0):.1%}"

        runs_list.append({
            "Run ID": run_id,
            "Type": render_run_type_badge(run_data["run_type"]) + " " + run_data["run_type"],
            "Status": render_status_badge(run_data["status"]) + " " + run_data["status"],
            "Duration": format_duration(run_data["duration_seconds"]),
            "Exceptions": exception_count,
            "Accuracy": accuracy,
            "Created": datetime.fromisoformat(run_data["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        })

    st.dataframe(runs_list, use_container_width=True, hide_index=True)

    st.divider()

    # Quick insights from latest baseline
    if latest_baseline:
        st.subheader(f"Latest Baseline Insights: {latest_baseline}")

        manifest = load_run_manifest(latest_baseline)
        calib = load_calibration_report(latest_baseline)

        if manifest and calib:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_exceptions = calib.get("total_exceptions", 0)
                total_rows = calib.get("total_rows", 0)
                exception_rate = total_exceptions / total_rows if total_rows else 0
                st.metric("Exception Rate", f"{exception_rate:.1%}", delta=f"{total_exceptions}/{total_rows}")

            with col2:
                accuracy = calib.get("overall_accuracy", 0)
                st.metric("Decision Accuracy", f"{accuracy:.1%}")

            with col3:
                error_dist = calib.get("error_distribution", {})
                overreactions = error_dist.get("overreaction", 0)
                st.metric("Overreactions", overreactions)

            with col4:
                bias_flags = calib.get("bias_flags", [])
                st.metric("Bias Flags", len(bias_flags))

            # Show bias flags if any
            if bias_flags:
                st.warning("**System Bias Detected:**")
                for flag in bias_flags:
                    st.markdown(f"- {flag}")

            # Show threshold recommendations
            threshold_recs = calib.get("threshold_recommendations", [])
            if threshold_recs:
                with st.expander("📋 Threshold Recommendations", expanded=False):
                    for rec in threshold_recs:
                        st.markdown(f"- {rec}")

    st.divider()

    # Quick actions
    st.subheader("Quick Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔍 Explore Latest Baseline", use_container_width=True):
            if latest_baseline:
                st.session_state["selected_run_id"] = latest_baseline
                st.switch_page("pages/01_Trace_Explorer.py")

    with col2:
        if st.button("📈 View Confidence Trends", use_container_width=True):
            st.switch_page("pages/02_Confidence_Analysis.py")

    with col3:
        if st.button("✅ Review Exceptions", use_container_width=True):
            st.switch_page("pages/04_Planner_Review.py")

if __name__ == "__main__":
    main()
