import json
import streamlit as st
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
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

def build_decision_record(item, action, reason):
    planner_action = action.lower()
    recommendation = item.get("recommendation", "accept")
    decision_match = planner_action == recommendation
    confidence_gap = abs(float(item.get("decision_confidence", 0)) - int(decision_match))
    error_type = classify_error(recommendation, planner_action, decision_match)
    return {
        "item_id": item["item_id"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "planner_action": planner_action,
        "decision_match": decision_match,
        "confidence_gap": confidence_gap,
        "error_type": error_type,
        "reason": reason,
    }

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
    st.subheader(item["item_id"])
    st.caption(f"{item['category']} · {item['store_id']}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Point Forecast", item["point_forecast"])
    col2.metric("Prior Forecast", item["prior_forecast"])
    col3.metric("Confidence", f"{item['confidence_score']:.2f}")
    col4.metric("Range", f"{item['lower_bound']}–{item['upper_bound']}")

    st.markdown("**Exception Reasons**")
    for reason in item.get("exception_reasons", []):
        st.markdown(f"- {reason}")

    st.info(item.get("planner_memo", ""))

    st.markdown("**Recent Sales (28 days)**")
    sales = item.get("recent_sales", [])
    if sales:
        st.line_chart(sales, height=120)

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
    record = build_decision_record(item, action, reason)
    decisions.append(record)
    save_decisions(decisions)
    st.session_state["reason_input"] = ""
    st.session_state["selected_id"] = None
    st.rerun()

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Planner Review Console", layout="wide")
    st.title("Planner Review Console")

    forecasts = load_forecasts()
    decisions = load_decisions()
    decided_ids = {d["item_id"] for d in decisions}
    exceptions = [f for f in forecasts if f.get("is_exception")]
    queue = [f for f in exceptions if f["item_id"] not in decided_ids]

    tab1, tab2 = st.tabs(["Review Queue", "Audit Log"])

    with tab1:
        col_queue, col_detail = st.columns([1, 2])

        with col_queue:
            st.markdown(f"**Exception Queue** · {len(queue)} remaining")
            if not queue:
                st.success("All exception items reviewed")
            else:
                for item in queue:
                    render_queue_item(item, decided_ids)

        with col_detail:
            if "selected_id" not in st.session_state or not st.session_state["selected_id"]:
                if queue:
                    st.session_state["selected_id"] = queue[0]["item_id"]

            selected_id = st.session_state.get("selected_id")
            selected = next((f for f in forecasts if f["item_id"] == selected_id), None)

            if selected and selected["item_id"] not in decided_ids:
                render_detail(selected, decisions)
            elif not queue:
                st.success(f"Queue cleared · {len(decisions)} decisions recorded")
            else:
                st.info("Select an item from the queue")

    with tab2:
        st.markdown(f"**Audit Log** · {len(decisions)} decisions")
        if st.button("Export Feedback"):
            export_path = export_feedback(forecasts, decisions)
            st.success(f"Exported to {export_path.relative_to(PROJECT_ROOT)}")

        if decisions:
            for d in sorted(decisions, key=lambda x: x["timestamp"], reverse=True):
                st.markdown(f"**{d['timestamp']}** · {d['item_id']} · `{d['planner_action']}`")
                if d.get("reason"):
                    st.caption(d["reason"])
                st.markdown("---")
        else:
            st.info("No decisions logged yet")

if __name__ == "__main__":
    main()
