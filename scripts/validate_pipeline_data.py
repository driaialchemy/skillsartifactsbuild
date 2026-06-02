import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from add_run_metadata import load_with_fallback
from metadata_foundation import MetadataContext, get_current_run_id

REQUIRED_FORECAST_KEYS = {
    "item_id": str,
    "store_id": str,
    "category": str,
    "point_forecast": int,
    "lower_bound": int,
    "upper_bound": int,
    "confidence_score": (int, float),
    "recent_sales": list,
    "prior_forecast": int,
}
REQUIRED_EXCEPTION_KEYS = {
    "is_exception": bool,
    "exception_reasons": list,
}
REQUIRED_MEMO_KEYS = {
    "recommendation": str,
    "recommendation_reason": str,
    "decision_confidence": (int, float),
    "risk_level": str,
    "planner_memo": str,
}
FILES_TO_CHECK = [
    ("data/forecasts.json", REQUIRED_FORECAST_KEYS),
    (
        "data/forecasts_with_exceptions.json",
        {**REQUIRED_FORECAST_KEYS, **REQUIRED_EXCEPTION_KEYS},
    ),
    (
        "data/forecasts_with_memos.json",
        {**REQUIRED_FORECAST_KEYS, **REQUIRED_EXCEPTION_KEYS, **REQUIRED_MEMO_KEYS},
    ),
    (
        "data/forecasts_ranked.json",
        {
            **REQUIRED_FORECAST_KEYS,
            **REQUIRED_EXCEPTION_KEYS,
            **REQUIRED_MEMO_KEYS,
            "priority_score": int,
            "priority_tier": str,
        },
    ),
]
RECENT_SALES_DAYS = 28
DECISION_CONFIDENCE_MIN = 0.0
DECISION_CONFIDENCE_MAX = 1.0


def load_rows(path):
    rows, _metadata = load_with_fallback(Path(path))
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a JSON array")
    return rows


def type_name(expected_type):
    if isinstance(expected_type, tuple):
        return "/".join(t.__name__ for t in expected_type)
    return expected_type.__name__


def validate_row(row, schema, row_index):
    errors = []
    if not isinstance(row, dict):
        return [f"Row {row_index}: expected object, found {type(row).__name__}"]
    for key, expected_type in schema.items():
        if key not in row:
            errors.append(f"Row {row_index}: missing '{key}'")
            continue
        if not isinstance(row[key], expected_type):
            errors.append(
                f"Row {row_index}: '{key}' expected {type_name(expected_type)}, "
                f"found {type(row[key]).__name__}"
            )
    recent_sales = row.get("recent_sales", [])
    if isinstance(recent_sales, list) and len(recent_sales) != RECENT_SALES_DAYS:
        errors.append(
            f"Row {row_index}: 'recent_sales' expected {RECENT_SALES_DAYS} values, "
            f"found {len(recent_sales)}"
        )
    if isinstance(recent_sales, list) and any(not isinstance(value, int) for value in recent_sales):
        errors.append(f"Row {row_index}: 'recent_sales' must contain integers only")
    decision_confidence = row.get("decision_confidence")
    if isinstance(decision_confidence, (int, float)):
        if not DECISION_CONFIDENCE_MIN <= decision_confidence <= DECISION_CONFIDENCE_MAX:
            errors.append(
                f"Row {row_index}: 'decision_confidence' must be between "
                f"{DECISION_CONFIDENCE_MIN} and {DECISION_CONFIDENCE_MAX}"
            )
    return errors


def validate_file(path, schema):
    rows = load_rows(path)
    errors = []
    for index, row in enumerate(rows, start=1):
        errors.extend(validate_row(row, schema, index))
    return rows, errors


def main():
    run_id = get_current_run_id()

    with MetadataContext(run_id, stage_number=7, stage_name="validate_pipeline",
                         script_path="scripts/validate_pipeline_data.py") as ctx:
        total_rows = 0
        failures = []
        validated_files = []

        for path, schema in FILES_TO_CHECK:
            try:
                rows, errors = validate_file(path, schema)
            except FileNotFoundError:
                failures.append(f"{path}: file not found")
                continue
            except ValueError as exc:
                failures.append(str(exc))
                continue

            ctx.log_input(path, row_count=len(rows))
            total_rows += len(rows)

            if errors:
                failures.extend(f"{path}: {error}" for error in errors)
            else:
                validated_files.append(path)
                print(f"{path}: OK ({len(rows)} rows)")

        ctx.log_metric("total_files_checked", len(FILES_TO_CHECK))
        ctx.log_metric("files_validated", len(validated_files))
        ctx.log_metric("total_rows_validated", total_rows)
        ctx.log_metric("validation_errors", len(failures))

        if failures:
            ctx.status = "failed"
            print("Validation failed")
            for failure in failures[:20]:
                print(f"- {failure}")
            if len(failures) > 20:
                print(f"- ... and {len(failures) - 20} more")
            raise SystemExit(1)

        print(f"Validated {len(FILES_TO_CHECK)} files and {total_rows} rows")


if __name__ == "__main__":
    main()
