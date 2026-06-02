import json
from pathlib import Path

INPUT_PATH = Path("data/calibration_report.json")
OUTPUT_PATH = Path("data/calibration_summary.txt")


def format_error_patterns(errors):
    return (
        f"Underreaction: {errors['underreaction']}\n"
        f"Overreaction: {errors['overreaction']}\n"
        f"Judgment difference: {errors['judgment_difference']}\n"
        f"No error: {errors['none']}"
    )


def format_bias(bias_flags):
    if not bias_flags:
        return "No explicit bias flags were detected in the current report."
    return "\n".join(f"- {flag}" for flag in bias_flags)


def format_recommendations(recommendations):
    return "\n".join(f"- {text}" for text in recommendations)


def build_risk_assessment(report):
    accuracy = report["overall_accuracy"]
    errors = report["error_distribution"]
    bias_flags = report["bias_flags"]
    lines = []
    if accuracy >= 0.9:
        lines.append("System shows high agreement but may be overfit to current logic.")
    else:
        lines.append("System agreement is moderate, so threshold changes should be tested carefully.")
    if errors["underreaction"] + errors["overreaction"] + errors["judgment_difference"] <= 4:
        lines.append("Low diversity of errors suggests limited stress testing.")
    else:
        lines.append("Broader error variety suggests the system is seeing multiple failure modes.")
    if bias_flags:
        lines.append("Detected bias flags indicate threshold tuning should happen before wider rollout.")
    else:
        lines.append("No bias flags were raised, but calibration should still be monitored over time.")
    return "\n".join(lines)


def main():
    report = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    summary = "\n\n".join(
        [
            "1. Overall Performance\n"
            f"Overall accuracy: {report['overall_accuracy']:.2%}\n"
            "The current calibration report indicates the system is usually aligned with planner decisions.",
            "2. Error Patterns\n" + format_error_patterns(report["error_distribution"]),
            "3. Detected Bias\n" + format_bias(report["bias_flags"]),
            "4. Recommended Adjustments\n"
            + format_recommendations(report["threshold_recommendations"]),
            "5. Risk Assessment\n" + build_risk_assessment(report),
        ]
    )
    OUTPUT_PATH.write_text(summary + "\n", encoding="utf-8")
    print(f"Wrote calibration summary to {OUTPUT_PATH}")
    print(summary)


if __name__ == "__main__":
    main()
