"""Pipeline orchestrator - runs all stages with metadata capture."""
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from metadata_foundation import init_run, finalize_run

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from policy_manager import load_policy


# Pipeline stages in execution order
PIPELINE_STAGES = [
    ("Stage 1: Generate Forecasts", "scripts/generate_forecasts.py"),
    ("Stage 2: Detect Exceptions", "scripts/detect_exceptions.py"),
    ("Stage 3: Generate Memos", "scripts/generate_memos.py"),
    ("Stage 4: Score and Rank", "scripts/score_and_rank.py"),
    ("Stage 5: Simulate Feedback", "scripts/simulate_planner_feedback.py"),
    ("Stage 6: Calibrate System", "scripts/calibrate_system.py"),
    ("Validation", "scripts/validate_pipeline_data.py"),
]


def generate_run_id(run_type: str, seed: int) -> str:
    """Generate deterministic run ID."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{seed}-{run_type}"


def run_pipeline(run_type: str = "baseline", seed: int = 42, validate: bool = True, policy_version: str = None):
    """Run the complete pipeline with metadata capture."""
    run_id = generate_run_id(run_type, seed)

    # Load policy configuration
    policy = load_policy(version=policy_version)
    policy_ver = policy["policy_version"]

    print("=" * 70)
    print(f"Pipeline Run: {run_id}")
    print(f"Policy Version: {policy_ver}")
    print("=" * 70)

    # Initialize run with policy version
    config = {}
    init_run(run_id, run_type=run_type, seed=seed, config=config, policy_version=policy_ver)
    print(f"Initialized run at: data/runs/{run_id}\n")

    # Set environment variable for all scripts
    env = os.environ.copy()
    env["PIPELINE_RUN_ID"] = run_id
    env["PIPELINE_SEED"] = str(seed)
    env["PIPELINE_RUN_TYPE"] = run_type
    env["POLICY_VERSION"] = policy_ver

    # Run all stages
    stages_to_run = PIPELINE_STAGES if validate else PIPELINE_STAGES[:-1]

    try:
        for stage_name, script_path in stages_to_run:
            print(f"{stage_name}...")
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
                return False

            # Print script output
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    print(f"  {line}")
            print()

        # Finalize run
        finalize_run(run_id, status="success")

        print("=" * 70)
        print("SUCCESS: Pipeline completed")
        print("=" * 70)
        print(f"\nRun ID: {run_id}")
        print(f"Results: data/runs/{run_id}")
        print(f"Summary: data/runs/{run_id}/summary.md")
        print()

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        finalize_run(run_id, status="failed")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run AI Demand Planning pipeline with metadata capture"
    )
    parser.add_argument(
        "--type",
        default="baseline",
        choices=["baseline", "stress", "noise-mild", "noise-moderate", "noise-targeted", "test"],
        help="Run type (default: baseline)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--policy-version",
        type=str,
        default=None,
        help="Policy version to use (default: latest/default)"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation step"
    )

    args = parser.parse_args()

    success = run_pipeline(
        run_type=args.type,
        seed=args.seed,
        validate=not args.skip_validation,
        policy_version=args.policy_version
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
