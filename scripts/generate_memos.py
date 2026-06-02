import json
import sys
from pathlib import Path
from statistics import pstdev

sys.path.insert(0, str(Path(__file__).parent))
from metadata_foundation import MetadataContext, get_current_run_id

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from policy_manager import load_policy

from add_run_metadata import load_with_fallback, save_with_metadata

# Load policy configuration
policy = load_policy()
decision_config = policy["decision_generation"]

LOW_CONFIDENCE_THRESHOLD = decision_config["low_confidence_threshold"]
BIG_CHANGE_THRESHOLD = decision_config["big_change_threshold"]
VOLATILITY_THRESHOLD = decision_config["volatility_threshold"]
WIDE_BAND_THRESHOLD = decision_config["wide_band_threshold"]
MULTI_FLAG_PENALTY = decision_config["multi_flag_penalty"]
SINGLE_FLAG_PENALTY = decision_config["single_flag_penalty"]

SUGGESTIONS = {
    "Low confidence": "recent data is sparse or missing",
    "Forecast changed": "recent promotions, price changes, or seasonality shifts are affecting demand",
    "Recent sales volatility": "stockouts, returns, or data-entry errors are distorting recent sales",
    "Wide confidence band": "more historical data would tighten the estimate",
}


def join_phrases(parts):
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def safe_ratio(numerator, denominator):
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_flags(row):
    recent_sales = row.get("recent_sales", [])
    point_forecast = row.get("point_forecast", 0)
    prior_forecast = row.get("prior_forecast", 0)
    confidence_score = row.get("confidence_score", 0.0)
    lower_bound = row.get("lower_bound", 0)
    upper_bound = row.get("upper_bound", 0)

    sales_mean = safe_ratio(sum(recent_sales), len(recent_sales)) if recent_sales else 0.0
    sales_std = pstdev(recent_sales) if recent_sales else 0.0
    change_ratio = safe_ratio(abs(point_forecast - prior_forecast), prior_forecast)
    volatility_ratio = safe_ratio(sales_std, sales_mean)
    band_ratio = safe_ratio(upper_bound - lower_bound, point_forecast)

    return {
        "low_confidence": confidence_score < LOW_CONFIDENCE_THRESHOLD,
        "big_change": change_ratio > BIG_CHANGE_THRESHOLD,
        "volatility": volatility_ratio > VOLATILITY_THRESHOLD,
        "wide_band": band_ratio > WIDE_BAND_THRESHOLD,
    }


def decision_reason(flag_names):
    reason_map = {
        "low_confidence": "low model confidence",
        "big_change": "a large forecast change versus the prior forecast",
        "volatility": "high recent sales volatility",
        "wide_band": "a wide forecast range",
    }
    return join_phrases([reason_map[name] for name in flag_names])


def build_decision(row):
    flags = compute_flags(row)
    flag_names = [name for name, is_on in flags.items() if is_on]
    flag_count = len(flag_names)
    confidence_score = float(row.get("confidence_score", 0.0))

    if flag_count > 1:
        recommendation = "escalate"
        risk_level = "high"
    elif flags["big_change"]:
        recommendation = "override"
        risk_level = "high"
    elif flags["low_confidence"]:
        recommendation = "investigate"
        risk_level = "medium"
    elif flags["volatility"]:
        recommendation = "investigate"
        risk_level = "high"
    elif flags["wide_band"]:
        recommendation = "investigate"
        risk_level = "medium"
    else:
        recommendation = "accept"
        risk_level = "low"

    penalty = 0.0
    if flag_count > 1:
        penalty = MULTI_FLAG_PENALTY
    elif flag_count == 1:
        penalty = SINGLE_FLAG_PENALTY
    decision_confidence = min(1.0, max(0.0, confidence_score - penalty))

    if flag_names:
        recommendation_reason = (
            f"Recommendation: {recommendation} due to {decision_reason(flag_names)}."
        )
    else:
        recommendation_reason = "Recommendation: accept because the forecast signals are stable."

    return {
        "recommendation": recommendation,
        "recommendation_reason": recommendation_reason,
        "decision_confidence": decision_confidence,
        "risk_level": risk_level,
    }


def build_memo(row):
    return row["recommendation_reason"]


def main():
    run_id = get_current_run_id()

    with MetadataContext(run_id, stage_number=3, stage_name="generate_memos",
                         script_path="scripts/generate_memos.py") as ctx:
        # Log policy version
        ctx.log_metric("policy_version", policy["policy_version"])

        ctx.log_threshold("low_confidence_threshold", LOW_CONFIDENCE_THRESHOLD)
        ctx.log_threshold("big_change_threshold", BIG_CHANGE_THRESHOLD)
        ctx.log_threshold("volatility_threshold", VOLATILITY_THRESHOLD)
        ctx.log_threshold("wide_band_threshold", WIDE_BAND_THRESHOLD)
        ctx.log_threshold("multi_flag_penalty", MULTI_FLAG_PENALTY)
        ctx.log_threshold("single_flag_penalty", SINGLE_FLAG_PENALTY)

        input_path = Path("data/forecasts_with_exceptions.json")
        output_path = Path("data/forecasts_with_memos.json")

        # Load with metadata fallback
        rows, input_metadata = load_with_fallback(input_path)
        ctx.log_input(str(input_path), row_count=len(rows))

        enriched = []
        recommendation_counts = {}
        for row in rows:
            updated = dict(row)
            updated.update(build_decision(row))
            updated["planner_memo"] = build_memo(updated)
            enriched.append(updated)
            rec = updated["recommendation"]
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1

        # Save with metadata wrapper
        save_with_metadata(enriched, output_path, run_id=run_id, policy_version=policy["policy_version"])

        ctx.log_output(str(output_path), row_count=len(enriched),
                      fields_added=["recommendation", "recommendation_reason", "decision_confidence", "risk_level", "planner_memo"])
        ctx.log_metric("memos_generated", len(enriched))
        ctx.log_metric("recommendation_distribution", recommendation_counts)

        print(f"Wrote {len(enriched)} forecasts to {output_path}")
        shown = 0
        for row in enriched:
            if row["is_exception"]:
                print(f"{row['item_id']}: {row['planner_memo']}")
                shown += 1
                if shown == 3:
                    break


if __name__ == "__main__":
    main()
