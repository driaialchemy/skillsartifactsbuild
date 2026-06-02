"""Test Phase 1: Metadata Foundation - Run 3 core scripts and verify metadata."""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from metadata_foundation import init_run, finalize_run


def main():
    # Generate test run ID
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{timestamp}-42-test-phase1"

    print(f"Testing Phase 1 with run_id: {run_id}")
    print("=" * 60)

    # Initialize run
    init_run(run_id, run_type="test-phase1", seed=42, config={
        "thresholds": {
            "low_confidence": 0.55,
            "change_ratio": 0.25,
            "volatility": 0.25,
            "band_ratio": 0.35
        }
    })

    # Set environment variable
    env = os.environ.copy()
    env["PIPELINE_RUN_ID"] = run_id

    scripts = [
        ("Stage 1", "scripts/generate_forecasts.py"),
        ("Stage 2", "scripts/detect_exceptions.py"),
    ]

    # Note: Stage 4 requires Stage 3 (generate_memos.py) which we haven't instrumented yet
    # So we'll skip it for now

    try:
        for stage_name, script_path in scripts:
            print(f"\n{stage_name}: Running {script_path}...")
            result = subprocess.run(
                [sys.executable, script_path],
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"ERROR: {script_path} failed")
                print(result.stderr)
                finalize_run(run_id, status="failed")
                return

            print(result.stdout)

        # Finalize run
        finalize_run(run_id, status="success")

        # Verify metadata files
        print("\n" + "=" * 60)
        print("Verifying metadata files...")
        run_dir = Path(f"data/runs/{run_id}")

        expected_files = [
            "run_manifest.json",
            "stage_01_generate_forecasts.json",
            "stage_02_detect_exceptions.json",
            "summary.md"
        ]

        all_present = True
        for filename in expected_files:
            filepath = run_dir / filename
            if filepath.exists():
                print(f"[OK] {filename} exists ({filepath.stat().st_size} bytes)")
            else:
                print(f"[MISSING] {filename}")
                all_present = False

        print("\n" + "=" * 60)
        if all_present:
            print("SUCCESS: Phase 1 metadata collection working!")
            print(f"\nView results at: {run_dir}")
            print(f"Summary: {run_dir / 'summary.md'}")
        else:
            print("FAILURE: Some metadata files missing")

    except Exception as e:
        print(f"ERROR: {e}")
        finalize_run(run_id, status="failed")


if __name__ == "__main__":
    main()
