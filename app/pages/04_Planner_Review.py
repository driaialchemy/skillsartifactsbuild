"""
Planner Review Console - Interactive exception review and decision recording

This page preserves the original planner review functionality with enhanced metadata tracking.
"""
import json
import streamlit as st
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from review_session_manager import ReviewSession
from queue_manager import QUEUE_TYPES, apply_queue_filter, get_queue_stats
from annotation_taxonomy import (
    OVERRIDE_TAGS, FAILURE_TAXONOMY, DISAGREEMENT_REASON_CATEGORIES,
    CONFIDENCE_LEVELS, SEVERITY_LEVELS, get_all_override_tags
)
from annotation_manager import AnnotationManager
from summary_generator import (
    generate_session_summary, generate_daily_summary,
    generate_reviewer_activity, generate_override_audit,
    generate_disagreement_analysis, save_summary
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.parent
FORECASTS_PATH = PROJECT_ROOT / "data" / "forecasts_ranked.json"
DECISIONS_PATH = PROJECT_ROOT / "data" / "planner_decisions.json"
EXPORT_PATH = PROJECT_ROOT / "data" / "planner_feedback_export.json"

# ---------------------------------------------------------------------------
# Data loading and persistence
# ---------------------------------------------------------------------------
@st.cache_data
def load_forecasts():
    return json.loads(FORECASTS_PATH.read_text(encoding="utf-8"))

def load_decisions():
    if not DECISIONS_PATH.exists():
        return []
    return json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))

def save_decisions(decisions):
    DECISIONS_PATH.write_text(json.dumps(decisions, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Logic from simulate_planner_feedback.py
# ---------------------------------------------------------------------------
def classify_error(recommendation, planner_action, decision_match):
    if decision_match:
        return "none"
    if recommendation == "accept" and planner_action != "accept":
        return "underreaction"
    if recommendation != "accept" and planner_action == "accept":
        return "overreaction"
    return "judgment_difference"

def build_decision_record(item, action, reason, review_duration_seconds=0):
    planner_action = action.lower()
    recommendation = item.get("recommendation", "accept")
    decision_match = planner_action == recommendation
    confidence_gap = abs(float(item.get("decision_confidence", 0)) - int(decision_match))
    error_type = classify_error(recommendation, planner_action, decision_match)

    # Build base record (backward compatible)
    record = {
        "item_id": item["item_id"],
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "planner_action": planner_action,
        "decision_match": decision_match,
        "confidence_gap": confidence_gap,
        "error_type": error_type,
        "reason": reason,
    }

    # Add optional decision metadata if session is active or annotations exist
    session = st.session_state.get("review_session")
    queue_type = st.session_state.get("queue_selector", "all_exceptions")

    # Check for structured annotations in session state
    item_id = item["item_id"]
    override_tags = st.session_state.get(f"override_tags_{item_id}", [])
    failure_category = st.session_state.get(f"failure_category_{item_id}", "")
    failure_subcategory = st.session_state.get(f"failure_subcategory_{item_id}", "")
    severity = st.session_state.get(f"severity_{item_id}", "")
    disagreement_type = st.session_state.get(f"disagreement_type_{item_id}", "")
    disagreement_reason = st.session_state.get(f"disagreement_reason_{item_id}", "")
    confidence_in_override = st.session_state.get(f"confidence_in_override_{item_id}", "")

    # Build metadata if we have session or annotations
    has_annotations = any([
        override_tags, failure_category, disagreement_type
    ])

    if session or has_annotations or review_duration_seconds > 0:
        metadata = {
            "schema_version": "1.0",
            "review_duration_seconds": round(review_duration_seconds, 1)
        }

        # Add session context if session is active
        if session:
            metadata["session_id"] = session.session_id
            metadata["reviewer_id"] = session.reviewer_id
            metadata["review_queue_type"] = queue_type

        # Add structured annotations if present
        if override_tags:
            metadata["override_tags"] = override_tags

        if failure_category:
            metadata["failure_taxonomy"] = {
                "category": failure_category,
                "subcategory": failure_subcategory if failure_subcategory else None,
                "severity": severity if severity else None
            }

        if disagreement_type and error_type != "none":
            metadata["disagreement_classification"] = {
                "type": disagreement_type,
                "reason_category": disagreement_reason if disagreement_reason else None,
                "confidence_in_override": confidence_in_override if confidence_in_override else None
            }

        record["decision_metadata"] = metadata

    return record

def export_feedback(forecasts, decisions):
    decision_map = {d["item_id"]: d for d in decisions}
    enriched = []
    for item in forecasts:
        if item["item_id"] not in decision_map:
            continue
        d = decision_map[item["item_id"]]
        enriched_item = dict(item)
        enriched_item["planner_action"] = d["planner_action"]
        enriched_item["decision_match"] = d["decision_match"]
        enriched_item["confidence_gap"] = d["confidence_gap"]
        enriched_item["error_type"] = d["error_type"]
        enriched.append(enriched_item)
    EXPORT_PATH.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
    return EXPORT_PATH

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def render_queue_item(item, decided_ids):
    if item["item_id"] in decided_ids:
        return False
    tier = item.get("priority_tier", "")
    reasons_short = " · ".join(item.get("exception_reasons", []))[:60]
    st.button(
        f"**{item['item_id']}** · {item['category']} · {tier}\n{reasons_short}",
        key=f"queue_{item['item_id']}",
        use_container_width=True,
        on_click=lambda: st.session_state.update({"selected_id": item["item_id"]}),
    )
    return True

def render_detail(item, decisions):
    # Track when this item was selected for review duration calculation
    item_id = item["item_id"]
    if f"item_selected_at_{item_id}" not in st.session_state:
        st.session_state[f"item_selected_at_{item_id}"] = datetime.now(timezone.utc)

    st.subheader(item["item_id"])
    st.caption(f"{item['category']} · {item['store_id']}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Point Forecast", item["point_forecast"])
    col2.metric("Prior Forecast", item["prior_forecast"])
    col3.metric("Confidence", f"{item['confidence_score']:.2f}")
    col4.metric("Range", f"{item['lower_bound']}–{item['upper_bound']}")

    # Enhanced metadata display
    st.markdown("**Exception Reasons**")
    for reason in item.get("exception_reasons", []):
        st.markdown(f"- {reason}")

    # Show priority information
    if item.get("priority_tier") and item.get("priority_tier") != "none":
        st.markdown(f"**Priority Tier:** `{item['priority_tier']}`")
        if item.get("priority_score"):
            st.markdown(f"**Priority Score:** `{item['priority_score']:.2f}`")

    # Recommendation and decision confidence
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Recommendation:** `{item.get('recommendation', 'accept').upper()}`")
    with col2:
        decision_conf = item.get("decision_confidence", 0)
        st.markdown(f"**Decision Confidence:** `{decision_conf:.3f}`")

    st.info(item.get("planner_memo", ""))

    st.markdown("**Recent Sales (28 days)**")
    sales = item.get("recent_sales", [])
    if sales:
        st.line_chart(sales, height=120)

    # Structured Annotations Panel (Optional)
    with st.expander("📝 Add Structured Annotations (Optional)", expanded=False):
        st.caption("Add structured metadata to help improve the system over time")

        # Override Tags
        st.markdown("**Override Tags**")
        st.caption("Why are you making this decision? (select all that apply)")
        all_tags = get_all_override_tags()
        selected_tags = st.multiselect(
            "Tags",
            options=all_tags,
            key=f"override_tags_{item_id}",
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Failure Taxonomy
        st.markdown("**Failure Taxonomy** (if system got it wrong)")
        col1, col2, col3 = st.columns(3)

        with col1:
            failure_category = st.selectbox(
                "Category",
                options=[""] + list(FAILURE_TAXONOMY.keys()),
                key=f"failure_category_{item_id}"
            )

        with col2:
            if failure_category:
                failure_subcategory = st.selectbox(
                    "Subcategory",
                    options=[""] + FAILURE_TAXONOMY[failure_category],
                    key=f"failure_subcategory_{item_id}"
                )
            else:
                st.selectbox("Subcategory", options=[""], disabled=True)

        with col3:
            if failure_category:
                severity = st.selectbox(
                    "Severity",
                    options=[""] + SEVERITY_LEVELS,
                    key=f"severity_{item_id}"
                )
            else:
                st.selectbox("Severity", options=[""], disabled=True)

        st.markdown("---")

        # Disagreement Classification (only if not matching)
        recommendation = item.get("recommendation", "accept")
        st.markdown("**Disagreement Classification** (if you disagree with the system)")

        col1, col2, col3 = st.columns(3)

        with col1:
            error_types = ["underreaction", "overreaction", "judgment_difference"]
            disagreement_type = st.selectbox(
                "Type",
                options=[""] + error_types,
                key=f"disagreement_type_{item_id}"
            )

        with col2:
            if disagreement_type:
                available_reasons = DISAGREEMENT_REASON_CATEGORIES.get(disagreement_type, [])
                disagreement_reason = st.selectbox(
                    "Reason",
                    options=[""] + available_reasons,
                    key=f"disagreement_reason_{item_id}"
                )
            else:
                st.selectbox("Reason", options=[""], disabled=True)

        with col3:
            if disagreement_type:
                confidence = st.selectbox(
                    "Your Confidence",
                    options=[""] + CONFIDENCE_LEVELS,
                    key=f"confidence_in_override_{item_id}"
                )
            else:
                st.selectbox("Your Confidence", options=[""], disabled=True)

    st.markdown("---")
    st.markdown("**Decision** (Override/Investigate require ≥10 chars)")
    reason = st.text_area("Reason", key="reason_input", height=80, placeholder="Required for Override/Investigate, optional for Escalate")

    col1, col2, col3, col4 = st.columns(4)
    if col1.button("Accept", use_container_width=True):
        commit_decision(item, "accept", "", decisions)
    if col2.button("Override", disabled=len(reason.strip()) < 10, use_container_width=True):
        commit_decision(item, "override", reason.strip(), decisions)
    if col3.button("Investigate", disabled=len(reason.strip()) < 10, use_container_width=True):
        commit_decision(item, "investigate", reason.strip(), decisions)
    if col4.button("Escalate", use_container_width=True):
        commit_decision(item, "escalate", reason.strip(), decisions)

def commit_decision(item, action, reason, decisions):
    # Calculate review duration if item_selected_at timestamp exists
    review_duration = 0
    if f"item_selected_at_{item['item_id']}" in st.session_state:
        selected_at = st.session_state[f"item_selected_at_{item['item_id']}"]
        review_duration = (datetime.now(timezone.utc) - selected_at).total_seconds()

    record = build_decision_record(item, action, reason, review_duration)

    # Check if annotations were used
    has_annotations = "decision_metadata" in record and any([
        record["decision_metadata"].get("override_tags"),
        record["decision_metadata"].get("failure_taxonomy"),
        record["decision_metadata"].get("disagreement_classification")
    ])

    # Update record to track annotation usage
    if has_annotations and "decision_metadata" in record:
        record["decision_metadata"]["has_annotations"] = True

    decisions.append(record)
    save_decisions(decisions)

    # Record decision in active session
    session = st.session_state.get("review_session")
    if session:
        # Add has_annotations flag to decision for session tracking
        decision_with_flag = dict(record)
        if has_annotations:
            decision_with_flag["has_annotations"] = True
        session.record_decision(decision_with_flag)

    # Clear selected item and annotation state
    st.session_state["selected_id"] = None

    # Clear annotation fields for this item
    item_id = item["item_id"]
    keys_to_clear = [
        f"override_tags_{item_id}",
        f"failure_category_{item_id}",
        f"failure_subcategory_{item_id}",
        f"severity_{item_id}",
        f"disagreement_type_{item_id}",
        f"disagreement_reason_{item_id}",
        f"confidence_in_override_{item_id}",
        f"item_selected_at_{item_id}"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Planner Review Console", page_icon="✅", layout="wide")

    # Session Management in Sidebar
    with st.sidebar:
        st.markdown("### Review Session")

        reviewer_id = st.text_input(
            "Reviewer ID",
            value=st.session_state.get("reviewer_id", "default_reviewer"),
            key="reviewer_id_input"
        )
        st.session_state["reviewer_id"] = reviewer_id

        if "review_session" not in st.session_state:
            queue_type = st.session_state.get("queue_selector", "all_exceptions")
            if st.button("Start Session", use_container_width=True):
                # Get initial queue size
                forecasts_temp = load_forecasts()
                exceptions_temp = [f for f in forecasts_temp if f.get("is_exception")]
                decided_ids_temp = {d["item_id"] for d in load_decisions()}
                initial_queue = apply_queue_filter(forecasts_temp, queue_type, decided_ids_temp)

                st.session_state["review_session"] = ReviewSession(
                    reviewer_id,
                    queue_type,
                    len(initial_queue)
                )
                st.session_state["session_start_time"] = datetime.now(timezone.utc)
                st.rerun()
        else:
            session = st.session_state["review_session"]
            st.success(f"Active Session")
            st.caption(f"**ID**: `{session.session_id}`")
            st.caption(f"**Reviewer**: {session.reviewer_id}")
            st.caption(f"**Queue**: {session.queue_type}")
            st.caption(f"**Items Reviewed**: {len(session.decisions)}")

            if st.button("End Session", use_container_width=True):
                session_file = session.save(PROJECT_ROOT / "data")
                st.success(f"Session saved!")
                st.caption(f"File: {session_file.name}")
                del st.session_state["review_session"]
                if "session_start_time" in st.session_state:
                    del st.session_state["session_start_time"]
                st.rerun()

    st.title("✅ Planner Review Console")
    st.caption("Interactive exception review and decision recording")

    forecasts = load_forecasts()
    decisions = load_decisions()
    decided_ids = {d["item_id"] for d in decisions}
    exceptions = [f for f in forecasts if f.get("is_exception")]
    queue = [f for f in exceptions if f["item_id"] not in decided_ids]

    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Items", len(forecasts))
    with col2:
        st.metric("Exceptions", len(exceptions))
    with col3:
        st.metric("Queue Remaining", len(queue))
    with col4:
        completion = (len(exceptions) - len(queue)) / len(exceptions) if exceptions else 0
        st.metric("Completion", f"{completion:.0%}")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Review Queue", "📜 Audit Log", "📊 Session Stats", "📈 Review Analytics"])

    with tab1:
        col_queue, col_detail = st.columns([1, 2])

        with col_queue:
            st.markdown(f"**Exception Queue** · {len(queue)} remaining")
            if not queue:
                st.success("All exception items reviewed")
            else:
                # Queue Selector (replaces tier filter)
                queue_type = st.selectbox(
                    "Review Queue",
                    options=list(QUEUE_TYPES.keys()),
                    format_func=lambda x: f"{QUEUE_TYPES[x]['icon']} {QUEUE_TYPES[x]['name']}",
                    key="queue_selector"
                )
                st.caption(QUEUE_TYPES[queue_type].get('description', ''))

                # Apply queue filter
                filtered_queue = apply_queue_filter(forecasts, queue_type, decided_ids)

                st.caption(f"Showing {len(filtered_queue)} items")

                for item in filtered_queue:
                    render_queue_item(item, decided_ids)

        with col_detail:
            if "selected_id" not in st.session_state or not st.session_state["selected_id"]:
                if filtered_queue:
                    st.session_state["selected_id"] = filtered_queue[0]["item_id"]

            selected_id = st.session_state.get("selected_id")
            selected = next((f for f in forecasts if f["item_id"] == selected_id), None)

            if selected and selected["item_id"] not in decided_ids:
                render_detail(selected, decisions)
            elif not filtered_queue:
                st.success(f"Queue cleared · {len(decisions)} decisions recorded")
            else:
                st.info("Select an item from the queue")

    with tab2:
        st.markdown(f"**Audit Log** · {len(decisions)} decisions")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("📥 Export Feedback", use_container_width=True):
                export_path = export_feedback(forecasts, decisions)
                st.success(f"Exported to {export_path.relative_to(PROJECT_ROOT)}")

        with col2:
            # Generate Session Summary
            if st.button("📄 Generate Session Summary", use_container_width=True):
                session = st.session_state.get("review_session")
                if session:
                    summary_content = generate_session_summary(session.finalize())
                    summary_path = PROJECT_ROOT / "data" / "review_summaries" / "daily" / f"{session.session_id}_summary.md"
                    save_summary(summary_content, summary_path)
                    st.success(f"Summary saved to {summary_path.relative_to(PROJECT_ROOT)}")
                else:
                    st.warning("No active session. Start a session to generate summaries.")

        with col3:
            if st.button("🗑️ Clear All Decisions", use_container_width=True):
                if st.session_state.get("confirm_clear"):
                    DECISIONS_PATH.write_text("[]", encoding="utf-8")
                    st.session_state["confirm_clear"] = False
                    st.rerun()
                else:
                    st.session_state["confirm_clear"] = True
                    st.warning("Click again to confirm deletion")

        if decisions:
            for d in sorted(decisions, key=lambda x: x["timestamp"], reverse=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{d['timestamp']}** · {d['item_id']} · `{d['planner_action']}`")
                    if d.get("reason"):
                        st.caption(d["reason"])
                with col2:
                    if d.get("decision_match"):
                        st.success("✓ Match")
                    else:
                        st.error(f"✗ {d.get('error_type', 'mismatch')}")
                st.markdown("---")
        else:
            st.info("No decisions logged yet")

    with tab3:
        st.subheader("Session Statistics")

        if decisions:
            # Calculate stats
            total_decisions = len(decisions)
            matches = sum(1 for d in decisions if d["decision_match"])
            accuracy = matches / total_decisions if total_decisions else 0

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Decisions", total_decisions)
                st.metric("Matches", matches)
                st.metric("Accuracy", f"{accuracy:.1%}")

            with col2:
                # Action distribution
                action_counts = {}
                for d in decisions:
                    action = d["planner_action"]
                    action_counts[action] = action_counts.get(action, 0) + 1

                st.markdown("**Action Distribution:**")
                for action, count in sorted(action_counts.items()):
                    st.markdown(f"- {action.title()}: {count}")

            with col3:
                # Error type distribution
                error_counts = {}
                for d in decisions:
                    error = d.get("error_type", "none")
                    error_counts[error] = error_counts.get(error, 0) + 1

                st.markdown("**Error Types:**")
                for error, count in sorted(error_counts.items()):
                    st.markdown(f"- {error.replace('_', ' ').title()}: {count}")

        else:
            st.info("Make decisions to see session statistics")

    with tab4:
        st.subheader("Review Analytics")

        if not decisions:
            st.info("No decisions yet. Analytics will appear after you make decisions.")
        else:
            # Extract annotations
            ann_manager = AnnotationManager(PROJECT_ROOT / "data")
            ann_stats = ann_manager.get_annotation_statistics(decisions)

            # Display annotation coverage
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Decisions", ann_stats["total_decisions"])
            with col2:
                st.metric("With Annotations", ann_stats["decisions_with_annotations"])
            with col3:
                st.metric("Coverage Rate", f"{ann_stats['coverage_rate'] * 100:.1f}%")

            st.markdown("---")

            # Extract all annotations for analysis
            from collections import Counter
            all_annotations = ann_manager.extract_annotations(decisions)

            if all_annotations:
                # Override Tags Analysis
                st.markdown("### Override Tags")
                all_tags = []
                for ann in all_annotations:
                    all_tags.extend(ann.get("override_tags", []))

                if all_tags:
                    tag_counts = Counter(all_tags)
                    top_tags = tag_counts.most_common(10)

                    import pandas as pd
                    tag_df = pd.DataFrame(top_tags, columns=["Tag", "Count"])
                    st.bar_chart(tag_df.set_index("Tag"))
                else:
                    st.info("No override tags used yet")

                st.markdown("---")

                # Failure Taxonomy Analysis
                st.markdown("### Failure Taxonomy")
                failure_categories = []
                for ann in all_annotations:
                    taxonomy = ann.get("failure_taxonomy")
                    if taxonomy and taxonomy.get("category"):
                        failure_categories.append(taxonomy["category"])

                if failure_categories:
                    category_counts = Counter(failure_categories)
                    cat_df = pd.DataFrame(category_counts.items(), columns=["Category", "Count"])
                    st.bar_chart(cat_df.set_index("Category"))
                else:
                    st.info("No failure taxonomy annotations yet")

                st.markdown("---")

                # Disagreement Type Analysis
                st.markdown("### Disagreement Types")
                disagreement_types = []
                for ann in all_annotations:
                    disagree = ann.get("disagreement_classification")
                    if disagree and disagree.get("type"):
                        disagreement_types.append(disagree["type"])

                if disagreement_types:
                    disagree_counts = Counter(disagreement_types)

                    # Create pie chart data
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        disagree_df = pd.DataFrame(disagree_counts.items(), columns=["Type", "Count"])
                        st.bar_chart(disagree_df.set_index("Type"))
                    with col2:
                        st.markdown("**Distribution:**")
                        total = sum(disagree_counts.values())
                        for dtype, count in disagree_counts.most_common():
                            pct = (count / total * 100)
                            st.markdown(f"- {dtype}: {pct:.1f}%")
                else:
                    st.info("No disagreement classifications yet")

                st.markdown("---")

                # Top Reasons Summary
                st.markdown("### Top Override Reasons")
                if all_tags:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Most Common Tags:**")
                        for tag, count in tag_counts.most_common(5):
                            st.markdown(f"- {tag}: {count}")

                    with col2:
                        st.markdown("**Tag Categories:**")
                        # Parse categories from tags
                        categories = []
                        for tag in all_tags:
                            if "/" in tag:
                                cat = tag.split("/")[0]
                                categories.append(cat)

                        if categories:
                            cat_counts = Counter(categories)
                            for cat, count in cat_counts.most_common():
                                st.markdown(f"- {cat}: {count}")

            else:
                st.info("No structured annotations yet. Use the annotation panel when reviewing items to see analytics here.")

            st.markdown("---")

            # Generate Governance Reports
            st.markdown("### Governance Reports")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📋 Generate Override Audit", use_container_width=True):
                    audit_content = generate_override_audit(decisions)
                    audit_path = PROJECT_ROOT / "data" / "review_summaries" / "governance" / "override_audit.md"
                    save_summary(audit_content, audit_path)
                    st.success(f"Audit saved to {audit_path.relative_to(PROJECT_ROOT)}")

            with col2:
                if st.button("📊 Generate Disagreement Analysis", use_container_width=True):
                    analysis_content = generate_disagreement_analysis(decisions)
                    analysis_path = PROJECT_ROOT / "data" / "review_summaries" / "governance" / "disagreement_analysis.md"
                    save_summary(analysis_content, analysis_path)
                    st.success(f"Analysis saved to {analysis_path.relative_to(PROJECT_ROOT)}")

if __name__ == "__main__":
    main()
