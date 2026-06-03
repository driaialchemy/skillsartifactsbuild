import json
import math
from pathlib import Path

from add_run_metadata import load_with_fallback

BASELINE = Path("data/forecasts_stress_ranked_v3.json")
PERTURBATIONS = {
    "mild": Path("data/forecasts_noise_mild_ranked.json"),
    "moderate": Path("data/forecasts_noise_moderate_ranked.json"),
    "targeted": Path("data/forecasts_noise_targeted_ranked.json"),
}
STABILITY = Path("data/ranking_stability_v2_summary.json")
OUTPUT = Path("data/top_tier_separation_analysis.json")
THIN_MARGIN = 3


def load(path):
    data, _metadata = load_with_fallback(path)
    return data


def std_dev(values):
    if not values:
        return 0.0
    mean_value = sum(values) / len(values)
    return (sum((value - mean_value) ** 2 for value in values) / len(values)) ** 0.5


def top_rows(rows):
    exceptions = [row for row in rows if row.get("is_exception")]
    count = max(1, math.ceil(len(exceptions) * 0.10))
    return exceptions[:count], exceptions


def rank_map(rows):
    return {row["item_id"]: index + 1 for index, row in enumerate(rows)}


def analyze_top(base_rows, all_rows):
    cutoff_score = base_rows[-1]["priority_score"]
    details = []
    gaps = []
    for index, row in enumerate(base_rows):
        next_score = all_rows[index + 1]["priority_score"] if index + 1 < len(all_rows) else row["priority_score"]
        gap = row["priority_score"] - next_score
        gaps.append(gap)
        details.append({
            "item_id": row["item_id"],
            "score": row["priority_score"],
            "gap_to_next": gap,
            "gap_to_cutoff": row["priority_score"] - cutoff_score,
            "thin_margin": gap <= THIN_MARGIN or (row["priority_score"] - cutoff_score) <= THIN_MARGIN,
        })
    scores = [row["priority_score"] for row in base_rows]
    return {
        "top_count": len(base_rows),
        "average_adjacent_gap": round(sum(gaps) / len(gaps), 2),
        "minimum_adjacent_gap": min(gaps),
        "top_score_std_dev": round(std_dev(scores), 2),
        "cutoff_score": cutoff_score,
        "items": details,
    }


def fragility(base_top, baseline_rows, perturbations):
    base_ranks = rank_map(baseline_rows)
    thin_ids = {item["item_id"] for item in base_top["items"] if item["thin_margin"]}
    moved_ids = set()
    stable_weak = []
    for name, rows in perturbations.items():
        ranks = rank_map(rows)
        for item in base_top["items"]:
            item_id = item["item_id"]
            delta = abs(base_ranks[item_id] - ranks[item_id])
            if delta > 0:
                moved_ids.add(item_id)
            if item["thin_margin"] and delta <= 2:
                stable_weak.append({"dataset": name, "item_id": item_id, "rank_change": delta})
    fragile = thin_ids & moved_ids
    return {
        "thin_margin_pct": round(len(thin_ids) / len(base_top["items"]), 4),
        "fragility_score": round(len(fragile) / len(base_top["items"]), 4),
        "stable_but_weakly_differentiated": stable_weak,
        "fragile_item_ids": sorted(fragile),
    }


def main():
    baseline_rows = load(BASELINE)
    stability = load(STABILITY)["cases"]
    base_top_rows, base_exception_rows = top_rows(baseline_rows)
    perturbation_rows = {name: load(path) for name, path in PERTURBATIONS.items()}
    top_summary = analyze_top(base_top_rows, base_exception_rows)
    fragility_summary = fragility(top_summary, baseline_rows, perturbation_rows)
    result = {
        "baseline": str(BASELINE),
        "stability_metrics": stability,
        "top_tier_separation": top_summary,
        "fragility_analysis": fragility_summary,
        "interpretation": "compressed" if fragility_summary["thin_margin_pct"] >= 0.4 else "well-separated",
    }
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote top-tier analysis to {OUTPUT}")
    print(f"Average top-tier gap: {top_summary['average_adjacent_gap']}")
    print(f"Thin-margin items: {fragility_summary['thin_margin_pct']:.2%}")
    print(f"Fragility score: {fragility_summary['fragility_score']:.2%}")
    print(f"Interpretation: {result['interpretation']}")


if __name__ == "__main__":
    main()
