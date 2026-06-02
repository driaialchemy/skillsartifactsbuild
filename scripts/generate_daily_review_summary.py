"""
Generate Daily Review Summary

Aggregates all review sessions for a given date and generates
a comprehensive daily summary report.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "lib"))

from summary_generator import generate_daily_summary, save_summary


PROJECT_ROOT = Path(__file__).parent.parent
SESSION_DIR = PROJECT_ROOT / "data" / "review_sessions"
SUMMARY_DIR = PROJECT_ROOT / "data" / "review_summaries" / "daily"


def load_sessions_for_date(target_date: str) -> List[Dict]:
    """
    Load all review sessions for a specific date.

    Args:
        target_date: Date string in YYYY-MM-DD format

    Returns:
        List of session data dictionaries
    """
    if not SESSION_DIR.exists():
        return []

    sessions = []

    for session_file in SESSION_DIR.glob("session-*.json"):
        session_data = json.loads(session_file.read_text(encoding="utf-8"))

        # Extract date from started_at timestamp
        session_date = session_data["started_at"][:10]

        if session_date == target_date:
            sessions.append(session_data)

    return sessions


def generate_summary_for_date(target_date: str) -> None:
    """
    Generate and save daily summary for a specific date.

    Args:
        target_date: Date string in YYYY-MM-DD format
    """
    print(f"Loading sessions for {target_date}...")
    sessions = load_sessions_for_date(target_date)

    if not sessions:
        print(f"No sessions found for {target_date}")
        return

    print(f"Found {len(sessions)} sessions")

    # Generate summary
    print("Generating daily summary...")
    summary_content = generate_daily_summary(sessions, target_date)

    # Save summary
    summary_path = SUMMARY_DIR / f"{target_date}_review_summary.md"
    save_summary(summary_content, summary_path)

    print(f"\nDaily summary saved to {summary_path}")
    print("\n" + "=" * 60)
    print(summary_content)
    print("=" * 60)


def main():
    """Main entry point."""
    # Check if date provided as argument
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        # Validate date format
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # Use today's date
        target_date = date.today().isoformat()
        print(f"No date specified, using today: {target_date}")

    generate_summary_for_date(target_date)


if __name__ == "__main__":
    main()
