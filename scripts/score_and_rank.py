import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from metadata_foundation import MetadataContext, get_current_run_id

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from policy_manager import load_policy

from add_run_metadata import load_with_fallback, save_with_metadata

# Load policy configuration
policy = load_policy()
scoring_config = policy["scoring_weights"]
exception_config = policy["exception_detection"]
tier_config = policy["tier_boundaries"]

WEIGHTS = {
    "change": scoring_config["change"],
    "volatility": scoring_config["volatility"],
    "band": scoring_config["band"],
    "low_confidence": scoring_config["low_confidence"]
}
DIMINISHING_RETURNS = tuple(scoring_config["diminishing_returns"])
HIGH_CONFIDENCE_THRESHOLD = exception_config["high_confidence_threshold"]

# Constants not in policy
POINT_FLOOR = 10.0
PRIOR_FLOOR = 10.0
SALES_FLOOR = 1.0
SMALL_POINT_THRESHOLD = 15.0
CORRELATED_DISCOUNT = 0.75
ACTIVE_SIGNAL_THRESHOLD = 0.08
ZSCORE_CAP = 3.0


def capped_zscore(value, mean, std_dev):
    if std_dev == 0:
        return 0.0
    return max(-ZSCORE_CAP, min(ZSCORE_CAP, (value - mean) / std_dev))


def row_metrics(row):
    point = max(float(row["point_forecast"]), 0.0)
    prior = max(float(row["prior_forecast"]), 0.0)
    recent = [float(value) for value in row.get("recent_sales", [])]
    mean_sales = max(sum(recent) / len(recent), SALES_FLOOR) if recent else SALES_FLOOR
    variance = sum((value - mean_sales) ** 2 for value in recent) / len(recent) if recent else 0.0
    return {
        "change": abs(point - prior) / max(prior, PRIOR_FLOOR),
        "volatility": (variance ** 0.5) / mean_sales if recent else 0.0,
        "band": (float(row["upper_bound"]) - float(row["lower_bound"])) / max(point, POINT_FLOOR),
        "point": point,
    }


def dataset_stats(metrics_list):
    stats = {}
    for key in ("change", "volatility", "band"):
        values = [metrics[key] for metrics in metrics_list]
        mean_value = sum(values) / len(values) if values else 0.0
        variance = sum((value - mean_value) ** 2 for value in values) / len(values) if values else 0.0
        stats[key] = (mean_value, variance ** 0.5)
    return stats


def validate_decision_fields(row):
    required = ("recommendation", "decision_confidence", "risk_level")
    if any(field not in row for field in required):
        raise ValueError("Missing decision fields. Run generate_memos.py before score_and_rank.py")


def confidence_signal(confidence):
    if confidence < 0.2:
        return 0.55
    if confidence < 0.4:
        return 0.35
    if confidence < 0.6:
        return 0.18
    if confidence < 0.8:
        return 0.05
    return 0.0


def signal_strengths(row, metrics, stats):
    confidence = float(row["confidence_score"])
    change = max(0.0, capped_zscore(metrics["change"], *stats["change"]) / ZSCORE_CAP)
    volatility = max(0.0, capped_zscore(metrics["volatility"], *stats["volatility"]) / ZSCORE_CAP)
    band = max(0.0, capped_zscore(metrics["band"], *stats["band"]) / ZSCORE_CAP)
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        change *= 0.65
    if metrics["point"] < SMALL_POINT_THRESHOLD:
        band *= metrics["point"] / SMALL_POINT_THRESHOLD
    if change > 0 and volatility > 0:
        if change < volatility:
            change *= CORRELATED_DISCOUNT
        else:
            volatility *= CORRELATED_DISCOUNT
    return {"change": change, "volatility": volatility, "band": band, "low_confidence": confidence_signal(confidence)}


def stability_factor(signals):
    active = [name for name, value in signals.items() if value > ACTIVE_SIGNAL_THRESHOLD]
    core = [name for name in active if name != "low_confidence"]
    agreeing = len(core) + (1 if core and "low_confidence" in active else 0)
    if not active:
        return 0.0
    if not core:
        return 0.55
    if len(core) == 1 and "low_confidence" not in active:
        return 0.8
    if len(core) == 1:
        return 0.92
    return min(1.25, 1.0 + 0.12 * (agreeing - 2))


def raw_score(row, metrics, stats):
    signals = signal_strengths(row, metrics, stats)
    weighted = sorted((WEIGHTS[name] * value for name, value in signals.items() if value > 0), reverse=True)
    total = sum(value * DIMINISHING_RETURNS[min(index, len(DIMINISHING_RETURNS) - 1)] for index, value in enumerate(weighted))
    total *= stability_factor(signals)
    active = [name for name, value in signals.items() if value > ACTIVE_SIGNAL_THRESHOLD]
    if active == ["low_confidence"]:
        total = min(total, 24.0)
    return round(min(100.0, total), 2)


def percentile_score(index, count):
    return 100 if count <= 1 else round(100 * (count - index - 1) / (count - 1))


def priority_tier(index, count):
    pct = (index + 1) / count if count else 1.0
    return "critical" if pct <= tier_config["critical"] else "high" if pct <= tier_config["high"] else "medium" if pct <= tier_config["medium"] else "none"


def score_rows(rows):
    metrics_list = [row_metrics(row) for row in rows]
    stats = dataset_stats(metrics_list)
    scored = []
    for row, metrics in zip(rows, metrics_list):
        updated = dict(row)
        validate_decision_fields(row)
        updated["_raw_score"] = raw_score(row, metrics, stats) if row.get("is_exception") else 0.0
        scored.append(updated)
    exceptions = sorted([row for row in scored if row.get("is_exception")], key=lambda row: (-row["_raw_score"], row["item_id"]))
    for index, row in enumerate(exceptions):
        row["priority_score"] = percentile_score(index, len(exceptions))
        row["priority_tier"] = priority_tier(index, len(exceptions))
    for row in scored:
        if not row.get("is_exception"):
            row["priority_score"] = 0
            row["priority_tier"] = "none"
        del row["_raw_score"]
    return sorted(scored, key=lambda row: (not row.get("is_exception"), -row["priority_score"], row["item_id"]))


def main():
    run_id = get_current_run_id()

    with MetadataContext(run_id, stage_number=4, stage_name="score_and_rank",
                         script_path="scripts/score_and_rank.py") as ctx:
        # Log policy version
        ctx.log_metric("policy_version", policy["policy_version"])

        ctx.log_threshold("weights", WEIGHTS)
        ctx.log_threshold("diminishing_returns", list(DIMINISHING_RETURNS))
        ctx.log_threshold("tier_boundaries", tier_config)

        input_path = Path("data/forecasts_with_memos.json")

        # Load with metadata fallback
        rows, input_metadata = load_with_fallback(input_path)
        ctx.log_input(str(input_path), row_count=len(rows))

        ranked = score_rows(rows)
        output_path = Path("data/forecasts_ranked.json")

        # Save with metadata wrapper
        save_with_metadata(ranked, output_path, run_id=run_id, policy_version=policy["policy_version"])

        # Calculate tier distribution
        tier_counts = {}
        for row in ranked:
            tier = row.get('priority_tier', 'none')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        ctx.log_output(str(output_path), row_count=len(ranked), fields_added=["priority_score", "priority_tier"])
        ctx.log_metric("tier_distribution", tier_counts)
        ctx.log_metric("total_ranked", len(ranked))

        print(f"Wrote {len(ranked)} forecasts to {output_path}")
        for row in ranked[:5]:
            print(f"{row['item_id']}: exception={row['is_exception']}, score={row['priority_score']}, tier={row['priority_tier']}")


if __name__ == "__main__":
    main()
