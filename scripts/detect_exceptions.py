import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from metadata_foundation import MetadataContext, get_current_run_id

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from policy_manager import load_policy

from add_run_metadata import save_with_metadata

# Load policy configuration
policy = load_policy()
exception_config = policy["exception_detection"]

LOW_CONFIDENCE_THRESHOLD = exception_config["low_confidence_threshold"]
CHANGE_RATIO_THRESHOLD = exception_config["change_ratio_threshold"]
VOLATILITY_THRESHOLD = exception_config["volatility_threshold"]
BAND_RATIO_THRESHOLD = exception_config["band_ratio_threshold"]
ZSCORE_THRESHOLD = exception_config["zscore_threshold"]
HIGH_CONFIDENCE_THRESHOLD = exception_config["high_confidence_threshold"]

# Constants not in policy
SMALL_POINT_THRESHOLD = 15.0
POINT_FLOOR = 10.0
PRIOR_FLOOR = 10.0
SALES_FLOOR = 1.0
ZSCORE_CAP = 3.0


def capped_zscore(value, mean, std_dev):
    if std_dev == 0:
        return 0.0
    return float(np.clip((value - mean) / std_dev, -ZSCORE_CAP, ZSCORE_CAP))


def row_metrics(forecast):
    point = max(float(forecast["point_forecast"]), 0.0)
    prior = max(float(forecast["prior_forecast"]), 0.0)
    lower = float(forecast["lower_bound"])
    upper = float(forecast["upper_bound"])
    recent = np.array(forecast["recent_sales"], dtype=float)
    mean_sales = max(float(np.mean(recent)) if len(recent) else 0.0, SALES_FLOOR)
    volatility = float(np.std(recent) / mean_sales) if len(recent) else 0.0
    change = abs(point - prior) / max(prior, PRIOR_FLOOR)
    band = (upper - lower) / max(point, POINT_FLOOR)
    return {"change": change, "volatility": volatility, "band": band, "point": point}


def dataset_stats(metrics):
    return {
        key: (
            float(np.mean([row[key] for row in metrics])),
            float(np.std([row[key] for row in metrics])),
        )
        for key in ("change", "volatility", "band")
    }


def detect_reasons(forecast, metrics, stats):
    reasons = []
    score = float(forecast["confidence_score"])
    change_z = capped_zscore(metrics["change"], *stats["change"])
    volatility_z = capped_zscore(metrics["volatility"], *stats["volatility"])
    band_z = capped_zscore(metrics["band"], *stats["band"])
    change_gate = ZSCORE_THRESHOLD + (0.45 if score >= HIGH_CONFIDENCE_THRESHOLD else 0.0)
    band_gate = ZSCORE_THRESHOLD + (0.45 if metrics["point"] < SMALL_POINT_THRESHOLD else 0.0)

    if score < LOW_CONFIDENCE_THRESHOLD:
        reasons.append(f"Low confidence ({score:.2f})")
    if metrics["change"] >= CHANGE_RATIO_THRESHOLD and change_z >= change_gate:
        reasons.append(f"Forecast changed {metrics['change'] * 100:.0f}% from prior week")
    if metrics["volatility"] >= VOLATILITY_THRESHOLD and volatility_z >= ZSCORE_THRESHOLD:
        reasons.append(
            f"Recent sales volatility ({metrics['volatility'] * 100:.0f}% of mean)"
        )
    if metrics["band"] >= BAND_RATIO_THRESHOLD and band_z >= band_gate:
        reasons.append(f"Wide confidence band ({metrics['band'] * 100:.0f}% of point)")
    return reasons


def main():
    run_id = get_current_run_id()

    with MetadataContext(run_id, stage_number=2, stage_name="detect_exceptions",
                         script_path="scripts/detect_exceptions.py") as ctx:
        # Log policy version
        ctx.log_metric("policy_version", policy["policy_version"])

        ctx.log_threshold("low_confidence_threshold", LOW_CONFIDENCE_THRESHOLD)
        ctx.log_threshold("change_ratio_threshold", CHANGE_RATIO_THRESHOLD)
        ctx.log_threshold("volatility_threshold", VOLATILITY_THRESHOLD)
        ctx.log_threshold("band_ratio_threshold", BAND_RATIO_THRESHOLD)

        input_path = Path("data/forecasts.json")
        output_path = Path("data/forecasts_with_exceptions.json")
        forecasts = json.loads(input_path.read_text(encoding="utf-8"))

        ctx.log_input(str(input_path), row_count=len(forecasts))

        metrics_list = [row_metrics(forecast) for forecast in forecasts]
        stats = dataset_stats(metrics_list)
        counts = {
            "Low confidence": 0,
            "Forecast changed": 0,
            "Recent sales volatility": 0,
            "Wide confidence band": 0,
        }
        enriched = []
        for forecast, metrics in zip(forecasts, metrics_list):
            reasons = detect_reasons(forecast, metrics, stats)
            row = dict(forecast)
            row["is_exception"] = bool(reasons)
            row["exception_reasons"] = reasons
            enriched.append(row)
            for reason in reasons:
                for label in counts:
                    if reason.startswith(label):
                        counts[label] += 1

        # Save with metadata wrapper
        save_with_metadata(enriched, output_path, run_id=run_id, policy_version=policy["policy_version"])

        exception_count = sum(row['is_exception'] for row in enriched)
        ctx.log_output(str(output_path), row_count=len(enriched), fields_added=["is_exception", "exception_reasons"])
        ctx.log_metric("exceptions_detected", exception_count)
        ctx.log_metric("exception_rate", exception_count / len(enriched) if enriched else 0)
        ctx.log_metric("reason_counts", counts)

        print(f"Wrote {len(enriched)} forecasts to {output_path}")
        print(f"Flagged {exception_count} forecasts")
        for name, count in counts.items():
            print(f"{name}: {count}")


if __name__ == "__main__":
    main()
