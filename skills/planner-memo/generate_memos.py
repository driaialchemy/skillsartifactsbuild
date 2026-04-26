import json
import sys
from pathlib import Path

LOW_CONFIDENCE_THRESHOLD = 0.6
BIG_CHANGE_THRESHOLD = 0.30
VOLATILITY_THRESHOLD = 0.40
WIDE_BAND_THRESHOLD = 0.50

REASONS = {
    "multiple": "Multiple forecast signals require planner escalation.",
    "big_change": "The forecast changed sharply versus the prior plan.",
    "low_confidence": "The forecast confidence is too low to accept directly.",
    "volatility": "Recent sales are too volatile to trust directly.",
    "wide_band": "The forecast range is too wide for direct acceptance.",
    "accept": "The forecast can be accepted as generated.",
}


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def recent_sales_stats(row):
    sales = row.get("recent_sales")
    if not isinstance(sales, list) or not sales:
        return 0.0, 0.0
    values = [to_float(value) for value in sales]
    mean_sales = sum(values) / len(values)
    if mean_sales <= 0:
        return mean_sales, 0.0
    variance = sum((value - mean_sales) ** 2 for value in values) / len(values)
    return mean_sales, (variance ** 0.5) / mean_sales


def detect_flags(row):
    point_forecast = to_float(row.get("point_forecast"))
    prior_forecast = to_float(row.get("prior_forecast"))
    lower_bound = to_float(row.get("lower_bound"))
    upper_bound = to_float(row.get("upper_bound"))
    confidence_score = to_float(row.get("confidence_score"))
    _, volatility_ratio = recent_sales_stats(row)
    change_ratio = abs(point_forecast - prior_forecast) / prior_forecast if prior_forecast > 0 else 0.0
    band_ratio = (upper_bound - lower_bound) / point_forecast if point_forecast > 0 else 0.0
    return {
        "low_confidence": confidence_score < LOW_CONFIDENCE_THRESHOLD,
        "big_change": change_ratio > BIG_CHANGE_THRESHOLD,
        "volatility": volatility_ratio > VOLATILITY_THRESHOLD,
        "wide_band": band_ratio > WIDE_BAND_THRESHOLD,
    }


def decide(row):
    confidence_score = to_float(row.get("confidence_score"))
    if not row.get("is_exception"):
        item_id = row.get("item_id", "unknown_item")
        category = row.get("category", "unknown_category")
        return {
            "recommendation": "accept",
            "recommendation_reason": REASONS["accept"],
            "decision_confidence": max(0.0, min(1.0, round(confidence_score, 2))),
            "risk_level": "low",
            "planner_memo": f"{item_id} in {category}: accept. {REASONS['accept']}",
        }
    flags = detect_flags(row)
    true_flags = [name for name, active in flags.items() if active]
    multiple = len(true_flags) > 1
    if multiple:
        recommendation, risk_level, reason = "escalate", "high", REASONS["multiple"]
    elif flags["big_change"]:
        recommendation, risk_level, reason = "override", "high", REASONS["big_change"]
    elif flags["low_confidence"]:
        recommendation, risk_level, reason = "investigate", "medium", REASONS["low_confidence"]
    elif flags["volatility"]:
        recommendation, risk_level, reason = "investigate", "high", REASONS["volatility"]
    elif flags["wide_band"]:
        recommendation, risk_level, reason = "investigate", "medium", REASONS["wide_band"]
    else:
        recommendation, risk_level, reason = "accept", "low", REASONS["accept"]
    penalty = 0.3 if multiple else 0.1 if true_flags else 0.0
    decision_confidence = max(0.0, min(1.0, round(confidence_score - penalty, 2)))
    item_id = row.get("item_id", "unknown_item")
    category = row.get("category", "unknown_category")
    planner_memo = f"{item_id} in {category}: {recommendation}. {reason}"
    return {
        "recommendation": recommendation,
        "recommendation_reason": reason,
        "decision_confidence": decision_confidence,
        "risk_level": risk_level,
        "planner_memo": planner_memo,
    }


def main():
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    rows = json.loads(input_path.read_text(encoding="utf-8"))
    enriched = []
    for row in rows:
        updated = dict(row)
        updated.update(decide(row))
        enriched.append(updated)
    output_path.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
    print(f"Wrote {len(enriched)} forecasts to {output_path}")


if __name__ == "__main__":
    main()
