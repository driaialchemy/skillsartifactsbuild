import json
from pathlib import Path

SUGGESTIONS = {
    "Low confidence": "recent data is sparse or missing",
    "Forecast changed": "recent promotions, price changes, or seasonality shifts are affecting demand",
    "Recent sales volatility": "stockouts, returns, or data-entry errors are distorting recent sales",
    "Wide confidence band": "more historical data would tighten the estimate",
}


def join_phrases(parts):
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def build_memo(row):
    reasons = row["exception_reasons"]
    suggestions = []
    for reason in reasons:
        for trigger, suggestion in SUGGESTIONS.items():
            if reason.startswith(trigger) and suggestion not in suggestions:
                suggestions.append(suggestion)
    first = (
        f"{row['item_id']} in {row['category']} needs planner review. "
        f"The item is flagged for {join_phrases([reason.lower() for reason in reasons])}."
    )
    second = f"Investigate whether {join_phrases(suggestions)}."
    return f"{first} {second}"


def main():
    input_path = Path("data/forecasts_with_exceptions.json")
    output_path = Path("data/forecasts_with_memos.json")
    rows = json.loads(input_path.read_text(encoding="utf-8"))
    enriched = []
    for row in rows:
        updated = dict(row)
        if row["is_exception"]:
            updated["planner_memo"] = build_memo(row)
        enriched.append(updated)
    output_path.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
    print(f"Wrote {len(enriched)} forecasts to {output_path}")
    shown = 0
    for row in enriched:
        if row["is_exception"]:
            print(f"{row['item_id']}: {row['planner_memo']}")
            shown += 1
            if shown == 3:
                break


if __name__ == "__main__":
    main()
