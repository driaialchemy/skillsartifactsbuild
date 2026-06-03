import json
import math
from pathlib import Path

from add_run_metadata import load_with_fallback

INPUT = Path("data/forecasts_ranked.json")
OUTPUT = Path("data/decision_equivalence_summary.json")


def variance(values):
    if len(values) < 2:
        return 0.0
    mean_value = sum(values) / len(values)
    return sum((value - mean_value) ** 2 for value in values) / len(values)


def main():
    rows, _metadata = load_with_fallback(INPUT)
    groups = {}
    for row in rows:
        key = (row["recommendation"], row["priority_tier"])
        groups.setdefault(key, []).append(row)
    summaries = []
    spreads = []
    top_n = max(1, math.ceil(len(rows) * 0.10))
    top_ids = {row["item_id"] for row in rows[:top_n]}
    equivalent_top = 0
    for (recommendation, tier), items in sorted(groups.items()):
        scores = [float(item["priority_score"]) for item in items]
        confidences = [float(item.get("decision_confidence", 0.0)) for item in items]
        spread = max(scores) - min(scores) if scores else 0.0
        spreads.append(spread)
        top_members = [item["item_id"] for item in items if item["item_id"] in top_ids]
        equivalent_top += len(top_members) if len(items) > 1 else 0
        summaries.append(
            {
                "recommendation": recommendation,
                "priority_tier": tier,
                "item_count": len(items),
                "score_variance": round(variance(scores), 4),
                "max_score_gap": round(spread, 4),
                "confidence_variance": round(variance(confidences), 4),
                "item_ids": [item["item_id"] for item in items],
            }
        )
    result = {
        "equivalence_group_count": len(groups),
        "avg_score_spread_within_group": round(sum(spreads) / len(spreads), 4),
        "max_score_spread_within_group": round(max(spreads), 4),
        "top_tier_decision_equivalent_pct": round(equivalent_top / top_n, 4),
        "groups": summaries,
    }
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote decision equivalence summary to {OUTPUT}")
    print(f"Equivalence groups: {result['equivalence_group_count']}")
    print(f"Average score spread: {result['avg_score_spread_within_group']}")
    print(f"Max score spread: {result['max_score_spread_within_group']}")
    print(f"Top-tier decision-equivalent pct: {result['top_tier_decision_equivalent_pct']:.2%}")


if __name__ == "__main__":
    main()
