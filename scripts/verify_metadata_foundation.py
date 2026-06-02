"""Verification script for Metadata Foundation Layer implementation."""
import json
import sys
from pathlib import Path


def verify_trace_index():
    """Verify trace index exists and has correct structure."""
    print("Checking trace index...")
    trace_path = Path("data/traces/trace_index.json")

    if not trace_path.exists():
        print("  ERROR: trace_index.json not found")
        return False

    trace_index = json.loads(trace_path.read_text())

    # Check schema version
    if trace_index.get("schema_version") != "1.0":
        print("  ERROR: Invalid schema version")
        return False

    # Check required fields
    if "runs" not in trace_index or "latest_by_type" not in trace_index:
        print("  ERROR: Missing required fields")
        return False

    print(f"  OK: {len(trace_index['runs'])} runs tracked")
    print(f"  OK: {len(trace_index['latest_by_type'])} run types")
    return True


def verify_latest_run():
    """Verify latest baseline run has all required files."""
    print("\nChecking latest baseline run...")
    trace_path = Path("data/traces/trace_index.json")
    trace_index = json.loads(trace_path.read_text())

    if "baseline" not in trace_index["latest_by_type"]:
        print("  WARNING: No baseline run found")
        return True  # Not an error if no baseline run yet

    run_id = trace_index["latest_by_type"]["baseline"]
    print(f"  Latest baseline: {run_id}")

    run_dir = Path(f"data/runs/{run_id}")
    if not run_dir.exists():
        print(f"  ERROR: Run directory not found: {run_dir}")
        return False

    # Check required files
    required_files = [
        "run_manifest.json",
        "stage_01_generate_forecasts.json",
        "stage_02_detect_exceptions.json",
        "stage_03_generate_memos.json",
        "stage_04_score_and_rank.json",
        "stage_05_simulate_planner_feedback.json",
        "stage_06_calibrate_system.json",
        "stage_07_validate_pipeline.json",
        "summary.md"
    ]

    all_present = True
    for filename in required_files:
        filepath = run_dir / filename
        if not filepath.exists():
            print(f"  ERROR: Missing {filename}")
            all_present = False

    if all_present:
        print("  OK: All metadata files present")

    return all_present


def verify_run_manifest(run_id):
    """Verify run manifest has correct structure."""
    print(f"\nChecking run manifest for {run_id}...")
    manifest_path = Path(f"data/runs/{run_id}/run_manifest.json")
    manifest = json.loads(manifest_path.read_text())

    # Check required fields
    required_fields = [
        "schema_version", "run_id", "run_type", "pipeline_version",
        "created_at", "status", "config", "environment"
    ]

    missing = [f for f in required_fields if f not in manifest]
    if missing:
        print(f"  ERROR: Missing fields: {missing}")
        return False

    # Check completed runs have duration
    if manifest["status"] == "success" and "duration_seconds" not in manifest:
        print("  ERROR: Successful run missing duration_seconds")
        return False

    print(f"  OK: Status={manifest['status']}, Duration={manifest.get('duration_seconds', 'N/A')}s")
    return True


def verify_stage_metadata(run_id, stage_number, stage_name):
    """Verify stage metadata has correct structure."""
    print(f"\nChecking stage {stage_number} ({stage_name})...")
    stage_path = Path(f"data/runs/{run_id}/stage_{stage_number:02d}_{stage_name}.json")

    if not stage_path.exists():
        print(f"  ERROR: Stage file not found: {stage_path}")
        return False

    stage = json.loads(stage_path.read_text())

    # Check required fields
    required_fields = [
        "schema_version", "stage_id", "run_id", "stage_number",
        "stage_name", "started_at", "duration_seconds", "status",
        "inputs", "outputs", "metrics", "thresholds_used"
    ]

    missing = [f for f in required_fields if f not in stage]
    if missing:
        print(f"  ERROR: Missing fields: {missing}")
        return False

    # Verify stage_id format
    expected_stage_id = f"{run_id}-stage{stage_number}-{stage_name}"
    if stage["stage_id"] != expected_stage_id:
        print(f"  ERROR: Invalid stage_id: {stage['stage_id']}")
        return False

    print(f"  OK: Duration={stage['duration_seconds']}s, Status={stage['status']}")
    print(f"  OK: {len(stage['metrics'])} metrics, {len(stage['thresholds_used'])} thresholds")
    return True


def verify_data_integrity():
    """Verify existing data files are intact."""
    print("\nChecking data file integrity...")

    required_files = [
        "data/forecasts.json",
        "data/forecasts_with_exceptions.json",
        "data/forecasts_with_memos.json",
        "data/forecasts_ranked.json"
    ]

    all_valid = True
    for filepath in required_files:
        path = Path(filepath)
        if not path.exists():
            print(f"  WARNING: {filepath} not found (may not be generated yet)")
            continue

        try:
            data = json.loads(path.read_text())
            if not isinstance(data, list):
                print(f"  ERROR: {filepath} is not a JSON array")
                all_valid = False
                continue
            print(f"  OK: {filepath} ({len(data)} items)")
        except json.JSONDecodeError as e:
            print(f"  ERROR: {filepath} is not valid JSON: {e}")
            all_valid = False

    return all_valid


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("Metadata Foundation Layer - Verification")
    print("=" * 70)

    checks = [
        ("Trace Index", verify_trace_index),
        ("Latest Run", verify_latest_run),
        ("Data Integrity", verify_data_integrity),
    ]

    # Get latest baseline run for detailed checks
    trace_path = Path("data/traces/trace_index.json")
    if trace_path.exists():
        trace_index = json.loads(trace_path.read_text())
        if "baseline" in trace_index["latest_by_type"]:
            run_id = trace_index["latest_by_type"]["baseline"]
            checks.extend([
                (f"Run Manifest ({run_id})", lambda: verify_run_manifest(run_id)),
                ("Stage 2 (detect_exceptions)", lambda: verify_stage_metadata(run_id, 2, "detect_exceptions")),
                ("Stage 4 (score_and_rank)", lambda: verify_stage_metadata(run_id, 4, "score_and_rank")),
                ("Stage 6 (calibrate_system)", lambda: verify_stage_metadata(run_id, 6, "calibrate_system")),
            ])

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Verification Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\nResult: {passed}/{total} checks passed")

    if passed == total:
        print("\nSUCCESS: Metadata Foundation Layer is correctly implemented!")
        return 0
    else:
        print("\nFAILURE: Some checks failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
