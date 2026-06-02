import json
import random
import sys
from pathlib import Path

from metadata_foundation import MetadataContext, get_current_run_id

# Add scripts directory to path for utilities
sys.path.insert(0, str(Path(__file__).parent))
from add_run_metadata import load_with_fallback, save_with_metadata

INPUT_PATH = Path("data/forecasts_ranked.json")
OUTPUT_PATH = Path("data/forecasts_with_feedback.json")
SEED = 42

ACTION_RULES = {
    "escalate": (("escalate", 0.90), ("investigate", 0.10)),
    "override": (("override", 0.70), ("accept", 0.30)),
    "investigate": (("investigate", 0.60), ("override", 0.40)),
    "accept": (("accept", 0.85), ("investigate", 0.15)),
}


def choose_action(row):
    if not row.get("is_exception"):
        return "accept"
    primary, fallback = ACTION_RULES[row["recommendation"]]
    return primary[0] if random.random() < primary[1] else fallback[0]


def classify_error(recommendation, planner_action, decision_match):
    if decision_match:
        return "none"
    if recommendation == "accept" and planner_action != "accept":
        return "underreaction"
    if recommendation != "accept" and planner_action == "accept":
        return "overreaction"
    return "judgment_difference"


def enrich_row(row, source_run_id, source_policy_version):
    updated = dict(row)
    planner_action = choose_action(row)
    decision_match = planner_action == row["recommendation"]
    updated["planner_action"] = planner_action
    updated["decision_match"] = decision_match
    updated["confidence_gap"] = abs(float(row["decision_confidence"]) - int(decision_match))
    updated["error_type"] = classify_error(
        row["recommendation"], planner_action, decision_match
    )
    # Add source tracking
    updated["source_run_id"] = source_run_id
    updated["source_policy_version"] = source_policy_version
    return updated


def main():
    run_id = get_current_run_id()

    with MetadataContext(run_id, stage_number=5, stage_name="simulate_planner_feedback",
                         script_path="scripts/simulate_planner_feedback.py") as ctx:
        ctx.log_threshold("seed", SEED)
        ctx.log_threshold("action_rules", ACTION_RULES)

        random.seed(SEED)

        # Load with metadata fallback
        rows, input_metadata = load_with_fallback(INPUT_PATH)
        ctx.log_input(str(INPUT_PATH), row_count=len(rows))

        # Get source tracking from input metadata
        source_run_id = input_metadata.get("run_id", run_id)
        source_policy_version = input_metadata.get("policy_version", "v1.0.0")

        enriched = [enrich_row(row, source_run_id, source_policy_version) for row in rows]

        # Save with metadata wrapper
        save_with_metadata(enriched, OUTPUT_PATH, run_id=run_id, policy_version=source_policy_version)

        matches = sum(row["decision_match"] for row in enriched)
        mismatches = len(enriched) - matches
        error_type_counts = {}
        for row in enriched:
            et = row["error_type"]
            error_type_counts[et] = error_type_counts.get(et, 0) + 1

        ctx.log_output(str(OUTPUT_PATH), row_count=len(enriched),
                      fields_added=["planner_action", "decision_match", "confidence_gap", "error_type"])
        ctx.log_metric("decision_matches", matches)
        ctx.log_metric("decision_mismatches", mismatches)
        ctx.log_metric("accuracy", matches / len(enriched) if enriched else 0)
        ctx.log_metric("error_type_distribution", error_type_counts)

        print(f"Wrote {len(enriched)} forecasts to {OUTPUT_PATH}")
        print(f"Decision matches: {matches}")
        print(f"Decision mismatches: {mismatches}")
        for row in enriched[:5]:
            print(
                f"{row['item_id']}: rec={row['recommendation']} "
                f"planner={row['planner_action']} match={row['decision_match']}"
            )


if __name__ == "__main__":
    main()
