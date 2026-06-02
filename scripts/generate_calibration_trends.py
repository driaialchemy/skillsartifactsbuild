"""Generate calibration trend summaries and visualizations."""
import json
from pathlib import Path
from typing import List, Dict, Any

from calibration_history_manager import get_calibration_manager


def generate_accuracy_trend():
    """Generate accuracy trend over time."""
    manager = get_calibration_manager()
    trend = manager.get_calibration_trend("overall_accuracy")

    if not trend:
        return {"trend": [], "summary": "No calibration data available"}

    # Calculate statistics
    accuracies = [point["value"] for point in trend]
    avg_accuracy = sum(accuracies) / len(accuracies)
    min_accuracy = min(accuracies)
    max_accuracy = max(accuracies)

    # Calculate improvement
    if len(accuracies) >= 2:
        first = accuracies[0]
        last = accuracies[-1]
        improvement = last - first
        improvement_pct = (improvement / first * 100) if first != 0 else 0
    else:
        improvement = 0
        improvement_pct = 0

    summary = {
        "trend": trend,
        "statistics": {
            "count": len(trend),
            "average": round(avg_accuracy, 4),
            "min": round(min_accuracy, 4),
            "max": round(max_accuracy, 4),
            "latest": round(accuracies[-1], 4),
            "improvement": round(improvement, 4),
            "improvement_percent": round(improvement_pct, 1)
        }
    }

    return summary


def generate_bias_trend():
    """Generate bias flag evolution over time."""
    manager = get_calibration_manager()
    calibrations = manager.get_all_calibrations()

    bias_evolution = []
    for cal in calibrations:
        bias_evolution.append({
            "calibration_id": cal["calibration_id"],
            "timestamp": cal["timestamp"],
            "policy_version": cal["policy_version"],
            "bias_flags": cal.get("bias_flags", []),
            "bias_count": len(cal.get("bias_flags", []))
        })

    # Summary
    total = len(calibrations)
    with_bias = sum(1 for cal in calibrations if cal.get("bias_flags"))
    without_bias = total - with_bias

    summary = {
        "evolution": bias_evolution,
        "statistics": {
            "total_calibrations": total,
            "with_bias_flags": with_bias,
            "without_bias_flags": without_bias,
            "bias_rate": round(with_bias / total, 2) if total > 0 else 0
        }
    }

    return summary


def generate_error_trend():
    """Generate overreaction/underreaction trend."""
    manager = get_calibration_manager()
    overreaction_trend = manager.get_calibration_trend("overreaction_count")
    underreaction_trend = manager.get_calibration_trend("underreaction_count")

    combined = []
    for over, under in zip(overreaction_trend, underreaction_trend):
        combined.append({
            "calibration_id": over["calibration_id"],
            "timestamp": over["timestamp"],
            "policy_version": over["policy_version"],
            "overreaction": over["value"],
            "underreaction": under["value"],
            "total_errors": over["value"] + under["value"]
        })

    summary = {
        "trend": combined,
        "statistics": {
            "count": len(combined),
            "latest_overreaction": combined[-1]["overreaction"] if combined else 0,
            "latest_underreaction": combined[-1]["underreaction"] if combined else 0
        }
    }

    return summary


def generate_threshold_effectiveness():
    """Analyze threshold change effectiveness."""
    manager = get_calibration_manager()
    calibrations = manager.get_all_calibrations()

    # Group by policy version
    by_policy = {}
    for cal in calibrations:
        policy_ver = cal["policy_version"]
        if policy_ver not in by_policy:
            by_policy[policy_ver] = []
        by_policy[policy_ver].append(cal)

    policy_performance = []
    for policy_ver, cals in sorted(by_policy.items()):
        accuracies = [cal["overall_accuracy"] for cal in cals]
        policy_performance.append({
            "policy_version": policy_ver,
            "calibration_count": len(cals),
            "average_accuracy": round(sum(accuracies) / len(accuracies), 4),
            "min_accuracy": round(min(accuracies), 4),
            "max_accuracy": round(max(accuracies), 4)
        })

    summary = {
        "policy_performance": policy_performance,
        "statistics": {
            "total_policies": len(policy_performance),
            "best_policy": max(policy_performance, key=lambda p: p["average_accuracy"])["policy_version"] if policy_performance else None
        }
    }

    return summary


def main():
    """Generate all calibration trend summaries."""
    trends_dir = Path("data/calibration_history/trends")
    trends_dir.mkdir(parents=True, exist_ok=True)

    print("Generating calibration trends...")

    # Accuracy trend
    accuracy_trend = generate_accuracy_trend()
    (trends_dir / "accuracy_trend.json").write_text(
        json.dumps(accuracy_trend, indent=2),
        encoding="utf-8"
    )
    print(f"  * Accuracy trend: {accuracy_trend['statistics']['count']} data points")

    # Bias trend
    bias_trend = generate_bias_trend()
    (trends_dir / "bias_trend.json").write_text(
        json.dumps(bias_trend, indent=2),
        encoding="utf-8"
    )
    print(f"  * Bias trend: {bias_trend['statistics']['bias_rate']:.0%} calibrations with bias flags")

    # Error trend
    error_trend = generate_error_trend()
    (trends_dir / "error_trend.json").write_text(
        json.dumps(error_trend, indent=2),
        encoding="utf-8"
    )
    print(f"  * Error trend: {error_trend['statistics']['count']} data points")

    # Threshold effectiveness
    threshold_effectiveness = generate_threshold_effectiveness()
    (trends_dir / "threshold_effectiveness.json").write_text(
        json.dumps(threshold_effectiveness, indent=2),
        encoding="utf-8"
    )
    print(f"  * Threshold effectiveness: {threshold_effectiveness['statistics']['total_policies']} policies analyzed")

    print(f"\nTrend summaries saved to: {trends_dir}")


if __name__ == "__main__":
    main()
