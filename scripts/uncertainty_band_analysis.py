import json
import math
from pathlib import Path

INPUT = Path("data/forecasts_with_feedback.json")
OUTPUT = Path("data/uncertainty_band_summary.json")


def avg(values):
    return round(sum(values) / len(values), 4) if values else 0.0


def main():
    rows = json.loads(INPUT.read_text(encoding="utf-8"))
    scores = [float(row["priority_score"]) for row in rows]
    max_gap = max((abs(a - b) for a, b in zip(scores, scores[1:])), default=1.0) or 1.0
    top_n = max(1, math.ceil(len(rows) * 0.10))
    top_ids = {row["item_id"] for row in rows[:top_n]}
    items = []
    for index, row in enumerate(rows):
        prev_gap = abs(scores[index] - scores[index - 1]) if index > 0 else max_gap
        next_gap = abs(scores[index] - scores[index + 1]) if index < len(rows) - 1 else max_gap
        local_gap = min(prev_gap, next_gap)
        gap_norm = local_gap / max_gap
        stability = gap_norm * float(row.get("decision_confidence", 0.0))
        if stability >= 0.35:
            band = "high"
        elif stability >= 0.15:
            band = "medium"
        else:
            band = "low"
        items.append(
            {
                "item_id": row["item_id"],
                "priority_score": row["priority_score"],
                "local_gap": round(local_gap, 4),
                "decision_confidence": round(float(row.get("decision_confidence", 0.0)), 4),
                "stability_score": round(stability, 4),
                "uncertainty_band": band,
                "confidence_gap": round(float(row.get("confidence_gap", 0.0)), 4),
            }
        )
    counts = {"high": [], "medium": [], "low": []}
    for item in items:
        counts[item["uncertainty_band"]].append(item)
    result = {
        "band_percentages": {
            band: round(len(group) / len(items), 4) if items else 0.0 for band, group in counts.items()
        },
        "top_tier_low_certainty_pct": round(
            sum(item["item_id"] in top_ids and item["uncertainty_band"] == "low" for item in items) / top_n,
            4,
        ),
        "average_confidence_gap_per_band": {
            band: avg([item["confidence_gap"] for item in group]) for band, group in counts.items()
        },
        "items": items,
    }
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote uncertainty band analysis to {OUTPUT}")
    print(f"Band percentages: {result['band_percentages']}")
    print(f"Top-tier low certainty pct: {result['top_tier_low_certainty_pct']:.2%}")
    print(f"Average confidence gap per band: {result['average_confidence_gap_per_band']}")


if __name__ == "__main__":
    main()
