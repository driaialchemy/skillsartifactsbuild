import json
import math
import sys
from pathlib import Path

from add_run_metadata import load_with_fallback

BUFFER_PCT = 0.025
SCORE_DELTA_THRESHOLD = 4
BOUNDARIES = (
    ("critical", 0.10, "high"),
    ("high", 0.30, "medium"),
    ("medium", 0.60, "none"),
)


def smooth_rows(rows):
    smoothed = [dict(row) for row in rows]
    exceptions = [row for row in smoothed if row.get("is_exception")]
    count = len(exceptions)
    holds = 0
    overrides = 0
    for index, row in enumerate(exceptions):
        percentile = (index + 1) / count if count else 1.0
        row["original_percentile"] = round(percentile, 4)
        row["smoothed_percentile"] = round(percentile, 4)
        row["tier_decision_reason"] = "Outside smoothing buffer"
    for upper_tier, cutoff, lower_tier in BOUNDARIES:
        boundary_index = math.ceil(count * cutoff) - 1
        if boundary_index < 0 or boundary_index >= count - 1:
            continue
        upper_score = exceptions[boundary_index]["priority_score"]
        lower_score = exceptions[boundary_index + 1]["priority_score"]
        span = math.ceil(count * BUFFER_PCT)
        start = max(0, boundary_index - span)
        stop = min(count, boundary_index + span + 2)
        for index in range(start, boundary_index + 1):
            row = exceptions[index]
            if row["priority_tier"] != upper_tier:
                continue
            if row["original_percentile"] < cutoff - BUFFER_PCT:
                continue
            gap = row["priority_score"] - lower_score
            boundary_label = f"{int(cutoff * 100)}%"
            if gap < SCORE_DELTA_THRESHOLD:
                row["tier_decision_reason"] = (
                    f"Held in {upper_tier}; buffer gap {gap} < "
                    f"{SCORE_DELTA_THRESHOLD}"
                )
                holds += 1
            else:
                row["tier_decision_reason"] = (
                    f"Retained {upper_tier}; buffer gap {gap} >= "
                    f"{SCORE_DELTA_THRESHOLD}"
                )
        for index in range(boundary_index + 1, stop):
            row = exceptions[index]
            if row["priority_tier"] != lower_tier:
                continue
            if row["original_percentile"] > cutoff + BUFFER_PCT:
                continue
            gap = upper_score - row["priority_score"]
            if gap < SCORE_DELTA_THRESHOLD:
                row["priority_tier"] = upper_tier
                row["smoothed_percentile"] = round(cutoff - 0.0001, 4)
                row["tier_decision_reason"] = (
                    f"Promoted into {upper_tier} buffer hold; score gap {gap} < "
                    f"{SCORE_DELTA_THRESHOLD}"
                )
                overrides += 1
    for row in smoothed:
        if row.get("is_exception"):
            continue
        row["original_percentile"] = 1.0
        row["smoothed_percentile"] = 1.0
        row["tier_decision_reason"] = "Non-exception item; smoothing not applied"
    return smoothed, holds, overrides


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/forecasts_ranked.json")
    output_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/forecasts_smoothed_ranked.json")
    )
    rows, _metadata = load_with_fallback(input_path)
    smoothed, holds, overrides = smooth_rows(rows)
    output_path.write_text(json.dumps(smoothed, indent=2), encoding="utf-8")
    print(f"Wrote {len(smoothed)} rows to {output_path}")
    print(f"Buffer holds: {holds}")
    print(f"Tier overrides: {overrides}")
    for row in smoothed[:5]:
        print(
            f"{row['item_id']}: {row['priority_tier']} "
            f"({row['tier_decision_reason']})"
        )


if __name__ == "__main__":
    main()
