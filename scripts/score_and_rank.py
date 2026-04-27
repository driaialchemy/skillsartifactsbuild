import json
from pathlib import Path

LOW_CONFIDENCE_THRESHOLD = 0.6
BIG_CHANGE_THRESHOLD = 0.30
VOLATILITY_THRESHOLD = 0.40
WIDE_BAND_THRESHOLD = 0.50
RISK_BASE = {"high": 70, "medium": 40, "low": 10}


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def stats(row):
    sales = row.get("recent_sales")
    if not isinstance(sales, list) or not sales:
        return 0.0, 0.0
    values = [to_float(value) for value in sales]
    mean_sales = sum(values) / len(values)
    if mean_sales <= 0:
        return mean_sales, 0.0
    variance = sum((value - mean_sales) ** 2 for value in values) / len(values)
    return mean_sales, (variance ** 0.5) / mean_sales


def derive_decision(row):
    if all(key in row for key in ("recommendation", "decision_confidence", "risk_level")):
        return row["recommendation"], to_float(row["decision_confidence"]), row["risk_level"]
    if not row.get("is_exception"):
        return "accept", round(to_float(row.get("confidence_score")), 2), "low"
    point = to_float(row.get("point_forecast"))
    prior = to_float(row.get("prior_forecast"))
    lower = to_float(row.get("lower_bound"))
    upper = to_float(row.get("upper_bound"))
    confidence = to_float(row.get("confidence_score"))
    _, volatility = stats(row)
    change = abs(point - prior) / prior if prior > 0 else 0.0
    band = (upper - lower) / point if point > 0 else 0.0
    flags = {
        "low_confidence": confidence < LOW_CONFIDENCE_THRESHOLD,
        "big_change": change > BIG_CHANGE_THRESHOLD,
        "volatility": volatility > VOLATILITY_THRESHOLD,
        "wide_band": band > WIDE_BAND_THRESHOLD,
    }
    active = [name for name, enabled in flags.items() if enabled]
    multiple = len(active) > 1
    if multiple:
        recommendation, risk_level = "escalate", "high"
    elif flags["big_change"]:
        recommendation, risk_level = "override", "high"
    elif flags["low_confidence"]:
        recommendation, risk_level = "investigate", "medium"
    elif flags["volatility"]:
        recommendation, risk_level = "investigate", "high"
    elif flags["wide_band"]:
        recommendation, risk_level = "investigate", "medium"
    else:
        recommendation, risk_level = "accept", "low"
    penalty = 0.3 if multiple else 0.1 if active else 0.0
    return recommendation, max(0.0, min(1.0, round(confidence - penalty, 2))), risk_level


def priority_tier(score):
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def score_row(row):
    updated = dict(row)
    if not row.get("is_exception"):
        updated["priority_score"] = 0
        updated["priority_tier"] = "none"
        return updated
    recommendation, confidence, risk_level = derive_decision(row)
    score = RISK_BASE.get(risk_level, 0) + (1 - confidence) * 30
    if recommendation == "escalate":
        score += 20
    updated["recommendation"] = recommendation
    updated["decision_confidence"] = confidence
    updated["risk_level"] = risk_level
    updated["priority_score"] = min(100, round(score))
    updated["priority_tier"] = priority_tier(updated["priority_score"])
    return updated


def main():
    input_path = Path("data/forecasts_with_memos.json")
    output_path = Path("data/forecasts_ranked.json")
    rows = json.loads(input_path.read_text(encoding="utf-8"))
    ranked = [score_row(row) for row in rows]
    ranked.sort(key=lambda row: (not row.get("is_exception"), -row["priority_score"]))
    output_path.write_text(json.dumps(ranked, indent=2), encoding="utf-8")
    print(f"Wrote {len(ranked)} forecasts to {output_path}")
    for row in ranked[:5]:
        print(
            f"{row['item_id']}: exception={row['is_exception']}, "
            f"score={row['priority_score']}, tier={row['priority_tier']}"
        )


if __name__ == "__main__":
    main()
