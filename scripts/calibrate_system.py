import json
import sys
from collections import Counter
from pathlib import Path

from metadata_foundation import MetadataContext, get_current_run_id

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from policy_manager import load_policy

# Add scripts directory to path for utilities
sys.path.insert(0, str(Path(__file__).parent))
from add_run_metadata import load_with_fallback
from calibration_history_manager import get_calibration_manager

# Load policy configuration
policy = load_policy()
CALIBRATION_GAP_THRESHOLD = policy.get("calibration", {}).get("calibration_gap_threshold", 0.4)

INPUT_PATH = Path("data/forecasts_with_feedback.json")
OUTPUT_PATH = Path("data/calibration_report.json")
RECOMMENDATIONS = ("accept", "override", "investigate", "escalate")
ERROR_TYPES = ("underreaction", "overreaction", "judgment_difference", "none")


def average(values):
    return sum(values) / len(values) if values else 0.0


def round_metrics(metrics):
    for key, value in metrics.items():
        if isinstance(value, float):
            metrics[key] = round(value, 4)
    return metrics


def build_accuracy_by_recommendation(rows):
    grouped = {}
    for name in RECOMMENDATIONS:
        subset = [row for row in rows if row["recommendation"] == name]
        grouped[name] = round_metrics(
            {
                "accuracy": average([float(row["decision_match"]) for row in subset]),
                "average_decision_confidence": average(
                    [row["decision_confidence"] for row in subset]
                ),
                "average_confidence_gap": average(
                    [row["confidence_gap"] for row in subset]
                ),
            }
        )
    return grouped


def build_recommendations(error_distribution, avg_gap, rec_metrics):
    recommendations = []
    if error_distribution["overreaction"] > error_distribution["underreaction"]:
        recommendations.append(
            "Increase exception thresholds because overreaction errors exceed underreaction errors."
        )
    elif error_distribution["underreaction"] > error_distribution["overreaction"]:
        recommendations.append(
            "Decrease exception thresholds because underreaction errors exceed overreaction errors."
        )
    else:
        recommendations.append(
            "Keep base thresholds steady because overreaction and underreaction counts are balanced."
        )

    if avg_gap > CALIBRATION_GAP_THRESHOLD:
        recommendations.append(
            "Adjust confidence penalties because the overall confidence gap is above 0.40."
        )

    weakest = min(RECOMMENDATIONS, key=lambda name: rec_metrics[name]["accuracy"])
    weakest_gap = rec_metrics[weakest]["average_confidence_gap"]
    recommendations.append(
        f"Tighten the {weakest} threshold because it has the lowest accuracy "
        f"({rec_metrics[weakest]['accuracy']:.2f}) and an average confidence gap of {weakest_gap:.2f}."
    )

    highest_gap = max(
        RECOMMENDATIONS, key=lambda name: rec_metrics[name]["average_confidence_gap"]
    )
    if highest_gap != weakest:
        recommendations.append(
            f"Recalibrate the {highest_gap} threshold because it has the largest confidence gap "
            f"({rec_metrics[highest_gap]['average_confidence_gap']:.2f})."
        )
    return recommendations[:4]


def main():
    run_id = get_current_run_id()

    with MetadataContext(run_id, stage_number=6, stage_name="calibrate_system",
                         script_path="scripts/calibrate_system.py") as ctx:
        # Log policy version
        ctx.log_metric("policy_version", policy["policy_version"])
        ctx.log_threshold("calibration_gap_threshold", CALIBRATION_GAP_THRESHOLD)

        # Load with metadata fallback
        rows, input_metadata = load_with_fallback(INPUT_PATH)
        ctx.log_input(str(INPUT_PATH), row_count=len(rows))

        total_rows = len(rows)
        total_exceptions = sum(row["is_exception"] for row in rows)
        overall_accuracy = average([float(row["decision_match"]) for row in rows])
        error_distribution = Counter(row["error_type"] for row in rows)
        for name in ERROR_TYPES:
            error_distribution.setdefault(name, 0)

        accuracy_by_recommendation = build_accuracy_by_recommendation(rows)
        avg_confidence_gap = average([row["confidence_gap"] for row in rows])
        bias_flags = []
        if error_distribution["overreaction"] > error_distribution["underreaction"]:
            bias_flags.append("system too aggressive")
        if error_distribution["underreaction"] > error_distribution["overreaction"]:
            bias_flags.append("system too conservative")
        if avg_confidence_gap > CALIBRATION_GAP_THRESHOLD:
            bias_flags.append("confidence poorly calibrated")

        report = {
            "total_rows": total_rows,
            "total_exceptions": total_exceptions,
            "overall_accuracy": round(overall_accuracy, 4),
            "error_distribution": {name: error_distribution[name] for name in ERROR_TYPES},
            "accuracy_by_recommendation": accuracy_by_recommendation,
            "bias_flags": bias_flags,
            "threshold_recommendations": build_recommendations(
                error_distribution, avg_confidence_gap, accuracy_by_recommendation
            ),
        }
        OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

        # Save to calibration history
        policy_version = input_metadata.get("policy_version", "v1.0.0")
        calibration_manager = get_calibration_manager()
        calibration_id = calibration_manager.save_calibration_report(
            run_id=run_id,
            policy_version=policy_version,
            report=report,
            recommendations_applied=False  # Can be updated manually later
        )

        ctx.log_metric("calibration_id", calibration_id)

        ctx.log_output(str(OUTPUT_PATH), row_count=1)
        ctx.log_metric("overall_accuracy", overall_accuracy)
        ctx.log_metric("total_exceptions", total_exceptions)
        ctx.log_metric("avg_confidence_gap", avg_confidence_gap)
        ctx.log_metric("bias_flags_count", len(bias_flags))
        ctx.log_metric("error_distribution", dict(error_distribution))

        print(f"Wrote calibration report to {OUTPUT_PATH}")
        print(f"Overall accuracy: {report['overall_accuracy']:.4f}")
        print(f"Bias flags: {len(report['bias_flags'])}")
        print(f"Recommendations: {len(report['threshold_recommendations'])}")


if __name__ == "__main__":
    main()
