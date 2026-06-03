import json
from collections import Counter
from pathlib import Path

from add_run_metadata import load_with_fallback

TOP_ITEMS_TO_SHOW = 5
MAX_REASON_WIDTH = 72


def load_rows():
    input_path = Path("data/forecasts_ranked.json")
    rows, _metadata = load_with_fallback(input_path)
    return rows


def exception_rows(rows):
    return [row for row in rows if row.get("is_exception")]


def summarize_counts(rows, key):
    return Counter(row.get(key, "unknown") for row in rows)


def shorten(text, width):
    if len(text) <= width:
        return text
    return text[: width - 3].rstrip() + "..."


def format_reasons(row):
    reasons = row.get("exception_reasons", [])
    if not reasons:
        return "No reasons recorded"
    return shorten("; ".join(reasons), MAX_REASON_WIDTH)


def print_counter(title, counts):
    print(title)
    for name, count in counts.most_common():
        print(f"  {name}: {count}")


def print_top_items(rows):
    print(f"Top {min(TOP_ITEMS_TO_SHOW, len(rows))} exception items")
    for row in rows[:TOP_ITEMS_TO_SHOW]:
        print(
            f"  {row['item_id']} | score={row['priority_score']} | "
            f"tier={row['priority_tier']} | rec={row['recommendation']}"
        )
        print(f"    memo: {shorten(row['planner_memo'], MAX_REASON_WIDTH)}")
        print(f"    why:  {format_reasons(row)}")


def main():
    rows = load_rows()
    flagged = exception_rows(rows)
    if not flagged:
        print("No exception rows found in data/forecasts_ranked.json")
        return

    print("Planner Review Queue Summary")
    print(f"Total rows: {len(rows)}")
    print(f"Exception rows: {len(flagged)}")
    print_counter("Recommendations", summarize_counts(flagged, "recommendation"))
    print_counter("Priority tiers", summarize_counts(flagged, "priority_tier"))
    print_counter("Categories", summarize_counts(flagged, "category"))
    print_top_items(flagged)


if __name__ == "__main__":
    main()
