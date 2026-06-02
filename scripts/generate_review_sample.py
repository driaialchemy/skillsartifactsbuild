"""
Generate Review Sample - Stratified Random Sampling for QA

Creates stratified random samples of forecasts for quality assurance reviews.
Samples are stratified by priority tier and decision confidence to ensure
representative coverage across different risk profiles.
"""

import json
import random
from pathlib import Path
from typing import List, Dict


PROJECT_ROOT = Path(__file__).parent.parent
FORECASTS_PATH = PROJECT_ROOT / "data" / "forecasts_ranked.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "forecasts_with_qa_sample.json"


# Sampling configuration
SAMPLE_CONFIG = {
    "total_sample_size": 50,  # Total items to sample
    "strata": {
        # Stratum: (min_priority_score, max_priority_score, min_confidence, max_confidence, weight)
        "critical_low_conf": {
            "priority_tier": "critical",
            "confidence_range": (0.0, 0.4),
            "weight": 0.3
        },
        "critical_high_conf": {
            "priority_tier": "critical",
            "confidence_range": (0.4, 1.0),
            "weight": 0.1
        },
        "high_low_conf": {
            "priority_tier": "high",
            "confidence_range": (0.0, 0.4),
            "weight": 0.2
        },
        "high_high_conf": {
            "priority_tier": "high",
            "confidence_range": (0.4, 1.0),
            "weight": 0.1
        },
        "medium_low_conf": {
            "priority_tier": "medium",
            "confidence_range": (0.0, 0.4),
            "weight": 0.15
        },
        "medium_high_conf": {
            "priority_tier": "medium",
            "confidence_range": (0.4, 1.0),
            "weight": 0.1
        },
        "none_random": {
            "priority_tier": "none",
            "confidence_range": (0.0, 1.0),
            "weight": 0.05
        }
    }
}


def load_forecasts() -> List[Dict]:
    """Load forecast data."""
    return json.loads(FORECASTS_PATH.read_text(encoding="utf-8"))


def assign_to_stratum(item: Dict, strata_config: Dict) -> str:
    """
    Assign an item to a stratum based on its attributes.

    Args:
        item: Forecast item
        strata_config: Stratum configuration

    Returns:
        Stratum name or None if item doesn't match any stratum
    """
    priority_tier = item.get("priority_tier", "none")
    decision_conf = item.get("decision_confidence", 1.0)

    for stratum_name, config in strata_config.items():
        if config["priority_tier"] == priority_tier:
            min_conf, max_conf = config["confidence_range"]
            if min_conf <= decision_conf < max_conf:
                return stratum_name

    return None


def stratified_sample(forecasts: List[Dict], config: Dict) -> List[Dict]:
    """
    Generate stratified random sample from forecasts.

    Args:
        forecasts: List of forecast items
        config: Sampling configuration

    Returns:
        List of sampled forecast items with sample metadata
    """
    # Only sample from exceptions
    exceptions = [f for f in forecasts if f.get("is_exception", False)]

    # Assign items to strata
    strata_items = {stratum: [] for stratum in config["strata"].keys()}

    for item in exceptions:
        stratum = assign_to_stratum(item, config["strata"])
        if stratum:
            strata_items[stratum].append(item)

    # Calculate sample sizes for each stratum
    total_sample = config["total_sample_size"]
    strata_samples = {}

    for stratum, stratum_config in config["strata"].items():
        weight = stratum_config["weight"]
        target_size = int(total_sample * weight)

        # Don't sample more than available
        available = len(strata_items[stratum])
        sample_size = min(target_size, available)

        strata_samples[stratum] = sample_size

    # Sample from each stratum
    sampled_items = []
    sample_sequence = 0

    for stratum, sample_size in strata_samples.items():
        if sample_size > 0:
            stratum_pool = strata_items[stratum]
            sampled = random.sample(stratum_pool, sample_size)

            # Add sampling metadata
            for item in sampled:
                item_copy = dict(item)
                item_copy["_sampled_for_qa"] = True
                item_copy["_sample_stratum"] = stratum
                item_copy["_sample_sequence"] = sample_sequence
                sampled_items.append(item_copy)
                sample_sequence += 1

    # Add non-sampled items without sample metadata
    sampled_ids = {item["item_id"] for item in sampled_items}
    for item in forecasts:
        if item["item_id"] not in sampled_ids:
            sampled_items.append(item)

    return sampled_items


def generate_sample_report(sampled_forecasts: List[Dict], config: Dict) -> str:
    """
    Generate a report of the sampling results.

    Args:
        sampled_forecasts: Forecasts with sample metadata
        config: Sampling configuration

    Returns:
        Report string
    """
    sampled = [f for f in sampled_forecasts if f.get("_sampled_for_qa")]

    report = f"""# QA Sample Report

## Summary
- Total Sample Size: {len(sampled)}
- Target Sample Size: {config['total_sample_size']}

## Sample Distribution by Stratum

"""

    from collections import Counter
    stratum_counts = Counter([f.get("_sample_stratum") for f in sampled])

    for stratum, count in sorted(stratum_counts.items()):
        weight = config["strata"][stratum]["weight"]
        target = int(config["total_sample_size"] * weight)
        report += f"- **{stratum}**: {count} (target: {target}, weight: {weight * 100:.1f}%)\n"

    return report


def main():
    """Generate stratified QA sample."""
    print("Loading forecasts...")
    forecasts = load_forecasts()
    print(f"Loaded {len(forecasts)} forecasts")

    exceptions = [f for f in forecasts if f.get("is_exception", False)]
    print(f"Found {len(exceptions)} exceptions")

    print("\nGenerating stratified sample...")
    sampled_forecasts = stratified_sample(forecasts, SAMPLE_CONFIG)

    sampled = [f for f in sampled_forecasts if f.get("_sampled_for_qa")]
    print(f"Sampled {len(sampled)} items for QA review")

    print("\nSaving sampled forecasts...")
    OUTPUT_PATH.write_text(
        json.dumps(sampled_forecasts, indent=2),
        encoding="utf-8"
    )
    print(f"Saved to {OUTPUT_PATH}")

    # Generate and save report
    report = generate_sample_report(sampled_forecasts, SAMPLE_CONFIG)
    report_path = PROJECT_ROOT / "data" / "review_summaries" / "qa_sample_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to {report_path}")

    print("\n" + report)


if __name__ == "__main__":
    main()
