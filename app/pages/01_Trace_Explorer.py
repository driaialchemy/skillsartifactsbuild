"""
Trace Explorer - Deep dive into pipeline execution metadata
"""
import json
import streamlit as st
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.parent
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
def load_stage_metadata(run_id, stage_number):
    # Find stage file - search for stage_XX_*.json pattern
    stage_files = list((RUNS_DIR / run_id).glob(f"stage_{stage_number:02d}_*.json"))
    if not stage_files:
        return None
    return json.loads(stage_files[0].read_text(encoding="utf-8"))

@st.cache_data
def load_summary_markdown(run_id):
    summary_path = RUNS_DIR / run_id / "summary.md"
    if not summary_path.exists():
        return None
    return summary_path.read_text(encoding="utf-8")

@st.cache_data
def get_all_stage_files(run_id):
    """Get all stage metadata files for a run."""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        return []
    return sorted(run_dir.glob("stage_*.json"))

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def render_status_badge(status):
    color_map = {"success": "🟢", "failed": "🔴", "partial": "🟡"}
    return color_map.get(status, "⚪")

def format_duration(seconds):
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    return f"{seconds:.2f}s"

def render_json_viewer(data, title="JSON Data"):
    """Render JSON with syntax highlighting."""
    with st.expander(f"📄 {title}", expanded=False):
        st.json(data)

def render_stage_card(stage_data):
    """Render a stage metadata card."""
    stage_name = stage_data.get("stage_name", "Unknown")
    duration = stage_data.get("duration_seconds", 0)
    status = stage_data.get("status", "unknown")
    metrics = stage_data.get("metrics", {})

    st.markdown(f"### Stage {stage_data.get('stage_number', '?')}: {stage_name}")
    st.caption(f"{render_status_badge(status)} {status} · {format_duration(duration)}")

    # Inputs and outputs
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Inputs:**")
        for inp in stage_data.get("inputs", []):
            st.markdown(f"- `{inp.get('file')}` ({inp.get('row_count', '?')} rows)")

    with col2:
        st.markdown("**Outputs:**")
        for out in stage_data.get("outputs", []):
            fields = out.get("fields_added", [])
            fields_str = f" +{fields}" if fields else ""
            st.markdown(f"- `{out.get('file')}` ({out.get('row_count', '?')} rows){fields_str}")

    # Metrics
    if metrics:
        st.markdown("**Metrics:**")

        # Separate scalar metrics from complex ones (dicts, lists)
        scalar_metrics = {}
        complex_metrics = {}

        for key, value in metrics.items():
            if isinstance(value, (dict, list)):
                complex_metrics[key] = value
            else:
                scalar_metrics[key] = value

        # Display scalar metrics as metric cards
        if scalar_metrics:
            cols = st.columns(min(len(scalar_metrics), 4))
            for idx, (key, value) in enumerate(scalar_metrics.items()):
                with cols[idx % 4]:
                    if isinstance(value, float):
                        st.metric(key, f"{value:.4f}" if value < 1 else f"{value:.2f}")
                    else:
                        st.metric(key, value)

        # Display complex metrics in expandable sections
        if complex_metrics:
            for key, value in complex_metrics.items():
                with st.expander(f"📊 {key}", expanded=False):
                    if isinstance(value, dict):
                        for k, v in value.items():
                            st.markdown(f"- **{k}**: {v}")
                    else:
                        st.json(value)

    # Thresholds
    thresholds = stage_data.get("thresholds_used", {})
    if thresholds:
        with st.expander("⚙️ Thresholds Used", expanded=False):
            for key, value in thresholds.items():
                st.markdown(f"- **{key}**: `{value}`")

    st.divider()

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Trace Explorer",
        page_icon="🔍",
        layout="wide"
    )

    st.title("🔍 Trace Explorer")
    st.caption("Deep dive into pipeline execution metadata")

    # Load trace index
    trace_index = load_trace_index()
    all_runs = trace_index.get("runs", {})

    if not all_runs:
        st.warning("No pipeline runs found.")
        return

    # Run selector
    run_ids = sorted(all_runs.keys(), reverse=True)

    # Check if a run was selected from another page
    if "selected_run_id" in st.session_state and st.session_state["selected_run_id"] in run_ids:
        default_idx = run_ids.index(st.session_state["selected_run_id"])
    else:
        default_idx = 0

    selected_run = st.selectbox(
        "Select Pipeline Run",
        run_ids,
        index=default_idx,
        format_func=lambda x: f"{x} ({all_runs[x]['run_type']}) - {all_runs[x]['status']}"
    )

    if not selected_run:
        return

    # Load run data
    manifest = load_run_manifest(selected_run)

    if not manifest:
        st.error(f"Could not load manifest for run: {selected_run}")
        return

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔧 Stages", "📄 Summary", "🗂️ Raw Metadata"])

    with tab1:
        st.subheader("Run Overview")

        # Metadata cards
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Run Type", manifest["run_type"])
            st.metric("Status", render_status_badge(manifest["status"]) + " " + manifest["status"])

        with col2:
            st.metric("Duration", format_duration(manifest["duration_seconds"]))
            st.metric("Stages Completed", f"{manifest.get('stages_completed', 0)}/7")

        with col3:
            created = datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
            st.metric("Started", created.strftime("%Y-%m-%d"))
            st.metric("Time", created.strftime("%H:%M:%S"))

        with col4:
            seed = manifest.get("config", {}).get("seed", "?")
            st.metric("Seed", seed)
            validation = manifest.get("validation_status", "unknown")
            st.metric("Validation", validation)

        st.divider()

        # Configuration
        st.subheader("Configuration")
        config = manifest.get("config", {})

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Thresholds:**")
            thresholds = config.get("thresholds", {})
            for key, value in thresholds.items():
                st.markdown(f"- **{key}**: `{value}`")

        with col2:
            st.markdown("**Environment:**")
            env = manifest.get("environment", {})
            for key, value in env.items():
                st.markdown(f"- **{key}**: `{value}`")

        st.divider()

        # Reproducibility instructions
        st.subheader("Reproducibility")
        st.code(f"""
export PIPELINE_RUN_ID={selected_run}
export PIPELINE_SEED={seed}
python scripts/run_pipeline.py --type {manifest['run_type']} --seed {seed}
        """.strip(), language="bash")

    with tab2:
        st.subheader("Stage Execution Timeline")

        # Load all stages
        stage_files = get_all_stage_files(selected_run)

        if not stage_files:
            st.info("No stage metadata found.")
        else:
            for stage_file in stage_files:
                stage_data = json.loads(stage_file.read_text(encoding="utf-8"))
                render_stage_card(stage_data)

    with tab3:
        st.subheader("Human-Readable Summary")

        summary_md = load_summary_markdown(selected_run)

        if summary_md:
            st.markdown(summary_md)

            # Download button
            st.download_button(
                "⬇️ Download Summary",
                summary_md,
                file_name=f"{selected_run}_summary.md",
                mime="text/markdown"
            )
        else:
            st.info("No summary.md found for this run.")

    with tab4:
        st.subheader("Raw Metadata Files")

        # Run manifest
        render_json_viewer(manifest, f"Run Manifest: {selected_run}")

        # All stage files
        for stage_file in get_all_stage_files(selected_run):
            stage_data = json.loads(stage_file.read_text(encoding="utf-8"))
            stage_name = stage_data.get("stage_name", "unknown")
            stage_num = stage_data.get("stage_number", "?")
            render_json_viewer(stage_data, f"Stage {stage_num}: {stage_name}")

if __name__ == "__main__":
    main()
