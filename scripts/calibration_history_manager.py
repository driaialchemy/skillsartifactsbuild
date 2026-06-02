"""Calibration History Manager - Track calibration reports over time."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional


class CalibrationHistoryManager:
    """Manages versioned calibration reports and trends."""

    def __init__(self, history_dir: Optional[Path] = None):
        if history_dir is None:
            self.history_dir = Path("data/calibration_history")
        else:
            self.history_dir = Path(history_dir)

        self.reports_dir = self.history_dir / "reports"
        self.trends_dir = self.history_dir / "trends"
        self.index_file = self.history_dir / "calibration_index.json"

        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.trends_dir.mkdir(parents=True, exist_ok=True)

    def save_calibration_report(
        self,
        run_id: str,
        policy_version: str,
        report: Dict[str, Any],
        recommendations_applied: bool = False,
        improved_from: Optional[str] = None
    ) -> str:
        """
        Save a calibration report to history.

        Args:
            run_id: Pipeline run identifier
            policy_version: Policy version used
            report: Calibration report data
            recommendations_applied: Whether recommendations were applied
            improved_from: Previous calibration ID if this is an improvement iteration

        Returns:
            Calibration ID
        """
        # Generate calibration ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        calibration_id = f"cal-{timestamp}"

        # Enhance report with metadata
        enhanced_report = {
            "calibration_id": calibration_id,
            "run_id": run_id,
            "policy_version": policy_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recommendations_applied": recommendations_applied,
            "improved_from": improved_from,
            **report
        }

        # Save to reports directory
        report_file = self.reports_dir / f"{run_id}_calibration.json"
        report_file.write_text(json.dumps(enhanced_report, indent=2), encoding="utf-8")

        # Update index
        self._update_index(calibration_id, enhanced_report)

        return calibration_id

    def _update_index(self, calibration_id: str, report: Dict[str, Any]):
        """Update the calibration index with a new entry."""
        if self.index_file.exists():
            index = json.loads(self.index_file.read_text(encoding="utf-8"))
        else:
            index = {
                "schema_version": "1.0",
                "calibrations": [],
                "latest": None
            }

        # Add entry to index
        index_entry = {
            "calibration_id": calibration_id,
            "run_id": report["run_id"],
            "policy_version": report["policy_version"],
            "timestamp": report["timestamp"],
            "overall_accuracy": report["overall_accuracy"],
            "bias_flags": report.get("bias_flags", []),
            "overreaction_count": report["error_distribution"].get("overreaction", 0),
            "underreaction_count": report["error_distribution"].get("underreaction", 0),
            "recommendations_applied": report.get("recommendations_applied", False),
            "improved_from": report.get("improved_from")
        }

        index["calibrations"].append(index_entry)
        index["latest"] = calibration_id

        # Save index
        self.index_file.write_text(json.dumps(index, indent=2), encoding="utf-8")

    def get_calibration(self, calibration_id: str) -> Dict[str, Any]:
        """Load a specific calibration report by ID."""
        # Search for report file
        for report_file in self.reports_dir.glob("*_calibration.json"):
            report = json.loads(report_file.read_text(encoding="utf-8"))
            if report.get("calibration_id") == calibration_id:
                return report

        raise FileNotFoundError(f"Calibration not found: {calibration_id}")

    def get_calibration_trend(self, metric: str) -> List[Dict[str, Any]]:
        """
        Extract time-series trend for a specific metric.

        Args:
            metric: Metric name (overall_accuracy, overreaction_count, etc.)

        Returns:
            List of {timestamp, value, policy_version, calibration_id} dicts
        """
        if not self.index_file.exists():
            return []

        index = json.loads(self.index_file.read_text(encoding="utf-8"))
        trend = []

        for entry in index["calibrations"]:
            if metric in entry:
                trend.append({
                    "timestamp": entry["timestamp"],
                    "value": entry[metric],
                    "policy_version": entry["policy_version"],
                    "calibration_id": entry["calibration_id"]
                })

        return sorted(trend, key=lambda x: x["timestamp"])

    def compare_calibrations(
        self,
        calibration_id_1: str,
        calibration_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare two calibration reports.

        Args:
            calibration_id_1: First calibration ID
            calibration_id_2: Second calibration ID

        Returns:
            Comparison dictionary with deltas
        """
        cal1 = self.get_calibration(calibration_id_1)
        cal2 = self.get_calibration(calibration_id_2)

        comparison = {
            "calibration_1": {
                "id": calibration_id_1,
                "policy_version": cal1["policy_version"],
                "timestamp": cal1["timestamp"]
            },
            "calibration_2": {
                "id": calibration_id_2,
                "policy_version": cal2["policy_version"],
                "timestamp": cal2["timestamp"]
            },
            "deltas": {}
        }

        # Compare key metrics
        metrics_to_compare = [
            "overall_accuracy",
            ("error_distribution", "overreaction"),
            ("error_distribution", "underreaction")
        ]

        for metric in metrics_to_compare:
            if isinstance(metric, tuple):
                section, key = metric
                val1 = cal1.get(section, {}).get(key, 0)
                val2 = cal2.get(section, {}).get(key, 0)
                metric_name = f"{section}.{key}"
            else:
                val1 = cal1.get(metric, 0)
                val2 = cal2.get(metric, 0)
                metric_name = metric

            delta = val2 - val1
            pct_change = (delta / val1 * 100) if val1 != 0 else 0

            comparison["deltas"][metric_name] = {
                "before": val1,
                "after": val2,
                "delta": delta,
                "percent_change": round(pct_change, 1)
            }

        return comparison

    def get_all_calibrations(self) -> List[Dict[str, Any]]:
        """Get all calibration entries from the index."""
        if not self.index_file.exists():
            return []

        index = json.loads(self.index_file.read_text(encoding="utf-8"))
        return index.get("calibrations", [])


# Global instance
_calibration_manager = CalibrationHistoryManager()


def get_calibration_manager() -> CalibrationHistoryManager:
    """Get the global calibration history manager instance."""
    return _calibration_manager


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calibration History Manager CLI")
    parser.add_argument("--list", action="store_true", help="List all calibrations")
    parser.add_argument("--show", metavar="CAL_ID", help="Show specific calibration")
    parser.add_argument("--trend", metavar="METRIC", help="Show trend for metric")
    parser.add_argument("--compare", nargs=2, metavar=("CAL1", "CAL2"), help="Compare two calibrations")

    args = parser.parse_args()

    manager = get_calibration_manager()

    if args.list:
        calibrations = manager.get_all_calibrations()
        if not calibrations:
            print("No calibrations found.")
        else:
            print(f"\nFound {len(calibrations)} calibration(s):\n")
            for cal in calibrations:
                print(f"  {cal['calibration_id']}")
                print(f"    Run: {cal['run_id']}")
                print(f"    Policy: {cal['policy_version']}")
                print(f"    Accuracy: {cal['overall_accuracy']:.4f}")
                print(f"    Bias flags: {len(cal.get('bias_flags', []))}")
                print()

    elif args.show:
        try:
            cal = manager.get_calibration(args.show)
            print(json.dumps(cal, indent=2))
        except FileNotFoundError as e:
            print(f"Error: {e}")

    elif args.trend:
        trend = manager.get_calibration_trend(args.trend)
        if not trend:
            print(f"No trend data for metric: {args.trend}")
        else:
            print(f"\nTrend for {args.trend}:\n")
            for point in trend:
                print(f"  {point['timestamp']}: {point['value']} (policy: {point['policy_version']})")

    elif args.compare:
        try:
            comparison = manager.compare_calibrations(args.compare[0], args.compare[1])
            print(f"\nCalibration Comparison: {comparison['calibration_1']['id']} → {comparison['calibration_2']['id']}")
            print("=" * 70)
            print(f"\nPolicy: {comparison['calibration_1']['policy_version']} → {comparison['calibration_2']['policy_version']}")
            print("\nMetric Changes:")
            for metric, delta_info in comparison['deltas'].items():
                before = delta_info['before']
                after = delta_info['after']
                delta = delta_info['delta']
                pct = delta_info['percent_change']
                sign = "+" if delta > 0 else ""
                print(f"  {metric}: {before} → {after} ({sign}{delta}, {sign}{pct}%)")
        except FileNotFoundError as e:
            print(f"Error: {e}")

    else:
        parser.print_help()
