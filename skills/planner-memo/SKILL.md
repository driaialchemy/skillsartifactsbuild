---
name: planner-memo
description: Use this skill when you have a JSON file of forecast records that has already been run through exception detection and now includes fields like `is_exception` and `exception_reasons`. Use this skill when you need to add a plain-English `planner_memo` to each exception item while preserving the original JSON structure for downstream review workflows. It applies to rule-based memo generation from exception-flagged forecasts, not raw forecast creation or exception scoring.
---

# Overview

Generate short, deterministic planner-review memos for forecast records that already include exception flags and exception reasons. Read a JSON array of forecast objects, add `planner_memo` only to rows where `is_exception` is `true`, and preserve all original fields exactly for downstream UI or reporting steps.

# When to use

- Add planner-facing memo text to a JSON file that already contains `is_exception` and `exception_reasons`
- Turn exception reasons into short investigation guidance for a planner review queue or audit workflow
- Enrich exception-flagged forecast output before passing it into a UI, artifact, or reporting step

# When NOT to use

- Do not use for forecasts that have not yet been run through exception detection
- Do not use when the input JSON lacks `is_exception` or `exception_reasons`
- Do not use for generating forecasts, confidence intervals, or exception flags
- Do not use for freeform narrative analysis that should go beyond the rule-based memo template

# Input contract

Expect a JSON array of objects. Each object should preserve this shape before memo generation:

```json
{
  "item_id": "FOODS_1_007",
  "store_id": "CA_1",
  "category": "FOODS",
  "point_forecast": 67,
  "lower_bound": 50,
  "upper_bound": 84,
  "confidence_score": 0.42,
  "recent_sales": [61, 75, 69, 70, 66, 58, 73, 64, 62, 71, 68, 59, 74, 72, 65, 63, 60, 76, 67, 71, 64, 66, 69, 62, 70, 68, 61, 73],
  "prior_forecast": 38,
  "is_exception": true,
  "exception_reasons": [
    "Low confidence (0.42)",
    "Forecast changed 77% from prior week"
  ]
}
```

Required semantics:

- `is_exception` determines whether a memo is added
- `exception_reasons` is a list of human-readable reason strings that begin with rule labels such as `Low confidence`, `Forecast changed`, `Recent sales volatility`, or `Wide confidence band`

# Output contract

Write the same JSON array back out with all original fields preserved. Add one new field only for rows where `is_exception` is `true`:

```json
{
  "planner_memo": "FOODS_1_007 in FOODS needs planner review. The item is flagged for low confidence (0.42) and forecast changed 77% from prior week. Investigate whether recent data is sparse or missing and recent promotions, price changes, or seasonality shifts are affecting demand."
}
```

Do not add `planner_memo` to non-exception rows.

# How to invoke

```bash
python generate_memos.py <input_json> <output_json>
```

Example:

```bash
python generate_memos.py data/forecasts_with_exceptions.json data/forecasts_with_memos.json
```

# Example

Input:

```json
[
  {
    "item_id": "HOUSEHOLD_1_002",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 32,
    "lower_bound": 25,
    "upper_bound": 39,
    "confidence_score": 0.48,
    "recent_sales": [31, 32, 37, 32, 35, 31, 28, 29, 30, 38, 30, 35, 29, 35, 33, 32, 32, 30, 33, 31, 28, 28, 33, 37, 32, 32, 33, 36],
    "prior_forecast": 35,
    "is_exception": true,
    "exception_reasons": ["Low confidence (0.48)"]
  },
  {
    "item_id": "HOBBIES_1_001",
    "store_id": "CA_1",
    "category": "HOBBIES",
    "point_forecast": 195,
    "lower_bound": 172,
    "upper_bound": 218,
    "confidence_score": 0.92,
    "recent_sales": [184, 211, 206, 207, 208, 259, 183, 180, 171, 213, 229, 192, 170, 170, 215, 217, 211, 175, 202, 199, 202, 221, 202, 215, 197, 204, 214, 151],
    "prior_forecast": 200,
    "is_exception": false,
    "exception_reasons": []
  }
]
```

Output:

```json
[
  {
    "item_id": "HOUSEHOLD_1_002",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 32,
    "lower_bound": 25,
    "upper_bound": 39,
    "confidence_score": 0.48,
    "recent_sales": [31, 32, 37, 32, 35, 31, 28, 29, 30, 38, 30, 35, 29, 35, 33, 32, 32, 30, 33, 31, 28, 28, 33, 37, 32, 32, 33, 36],
    "prior_forecast": 35,
    "is_exception": true,
    "exception_reasons": ["Low confidence (0.48)"],
    "planner_memo": "HOUSEHOLD_1_002 in HOUSEHOLD needs planner review. The item is flagged for low confidence (0.48). Investigate whether recent data is sparse or missing."
  },
  {
    "item_id": "HOBBIES_1_001",
    "store_id": "CA_1",
    "category": "HOBBIES",
    "point_forecast": 195,
    "lower_bound": 172,
    "upper_bound": 218,
    "confidence_score": 0.92,
    "recent_sales": [184, 211, 206, 207, 208, 259, 183, 180, 171, 213, 229, 192, 170, 170, 215, 217, 211, 175, 202, 199, 202, 221, 202, 215, 197, 204, 214, 151],
    "prior_forecast": 200,
    "is_exception": false,
    "exception_reasons": []
  }
]
```
