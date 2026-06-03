import json
from pathlib import Path

from add_run_metadata import load_with_fallback

BASELINE = Path("data/forecasts_stress_ranked_v3.json")
CASES = {
    "mild": Path("data/forecasts_noise_mild_ranked.json"),
    "moderate": Path("data/forecasts_noise_moderate_ranked.json"),
    "targeted": Path("data/forecasts_noise_targeted_ranked.json"),
}
OUTPUT = Path("data/ranking_stability_v2_summary.json")
BOUNDARIES = (0.10, 0.30, 0.60)
BOUNDARY_BAND = 0.05
TOP_K_PCTS = (0.05, 0.10, 0.20)


def load_rows(path):
    rows, _metadata = load_with_fallback(path)
    return rows


def rank_map(rows):
    return {row["item_id"]: index + 1 for index, row in enumerate(rows)}


def spearman(base_ranks, other_ranks):
    ids = sorted(base_ranks)
    n = len(ids)
    diff_sq = sum((base_ranks[i] - other_ranks[i]) ** 2 for i in ids)
    return round(1 - (6 * diff_sq) / (n * (n**2 - 1)), 4) if n > 1 else 1.0


def marc(base_ranks, other_ranks):
    ids = base_ranks.keys()
    return round(sum(abs(base_ranks[i] - other_ranks[i]) for i in ids) / len(base_ranks), 2)


def weighted_top_overlap(base_rows, other_rows):
    base_ids = [row["item_id"] for row in base_rows]
    other_ids = [row["item_id"] for row in other_rows]
    total_weight = 0.0
    weighted_sum = 0.0
    for pct in TOP_K_PCTS:
        k = max(1, round(len(base_rows) * pct))
        overlap = len(set(base_ids[:k]) & set(other_ids[:k])) / k
        weight = 1 / pct
        total_weight += weight
        weighted_sum += overlap * weight
    return round(weighted_sum / total_weight, 4)


def boundary_ids(rows):
    ids = set()
    count = len(rows)
    for index, row in enumerate(rows):
        pct = (index + 1) / count if count else 1.0
        if any(abs(pct - cutoff) <= BOUNDARY_BAND for cutoff in BOUNDARIES):
            ids.add(row["item_id"])
    return ids


def boundary_instability(base_rows, other_rows):
    base_tier = {row["item_id"]: row["priority_tier"] for row in base_rows}
    other_tier = {row["item_id"]: row["priority_tier"] for row in other_rows}
    ids = boundary_ids(base_rows)
    changed = sum(base_tier[i] != other_tier[i] for i in ids)
    rate = round(changed / len(ids), 4) if ids else 0.0
    return len(ids), rate


def displacement_profile(base_ranks, other_ranks):
    buckets = {"no_change": 0, "small_1_5": 0, "medium_6_20": 0, "large_gt_20": 0}
    for item_id, base_rank in base_ranks.items():
        delta = abs(base_rank - other_ranks[item_id])
        if delta == 0:
            buckets["no_change"] += 1
        elif delta <= 5:
            buckets["small_1_5"] += 1
        elif delta <= 20:
            buckets["medium_6_20"] += 1
        else:
            buckets["large_gt_20"] += 1
    total = len(base_ranks)
    return {name: round(count / total, 4) for name, count in buckets.items()}


def evaluate_case(base_rows, case_rows):
    base_ranks = rank_map(base_rows)
    case_ranks = rank_map(case_rows)
    boundary_count, boundary_rate = boundary_instability(base_rows, case_rows)
    return {
        "spearman_rank_correlation": spearman(base_ranks, case_ranks),
        "mean_absolute_rank_change": marc(base_ranks, case_ranks),
        "weighted_top_overlap": weighted_top_overlap(base_rows, case_rows),
        "boundary_band_count": boundary_count,
        "boundary_instability_rate": boundary_rate,
        "rank_displacement_distribution": displacement_profile(base_ranks, case_ranks),
    }


def main():
    base_rows = load_rows(BASELINE)
    summary = {"baseline": str(BASELINE), "cases": {}}
    for name, path in CASES.items():
        rows = load_rows(path)
        summary["cases"][name] = evaluate_case(base_rows, rows)
    OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote stability summary to {OUTPUT}")
    for name, metrics in summary["cases"].items():
        print(name)
        print(f"  Spearman: {metrics['spearman_rank_correlation']}")
        print(f"  MARC: {metrics['mean_absolute_rank_change']}")
        print(f"  Weighted top overlap: {metrics['weighted_top_overlap']}")
        print(
            f"  Boundary instability: {metrics['boundary_instability_rate']} "
            f"({metrics['boundary_band_count']} items)"
        )
        print(f"  Displacement: {metrics['rank_displacement_distribution']}")


if __name__ == "__main__":
    main()
