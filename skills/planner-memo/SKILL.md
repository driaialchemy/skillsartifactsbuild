---
name: planner-memo
description: Converts forecast exceptions into structured planning decisions.
---

# Overview

This skill reads a JSON array of forecast rows and writes the same rows back with deterministic planning decisions. It preserves the original fields, keeps `planner_memo` as a secondary text summary, and derives all decision logic from raw numeric inputs rather than `exception_reasons`.

# Input schema

Each row should include these fields:

```json
{
  "item_id": "FOODS_1_007",
  "store_id": "CA_1",
  "category": "FOODS",
  "point_forecast": 67,
  "lower_bound": 50,
  "upper_bound": 84,
  "confidence_score": 0.42,
  "recent_sales": [61, 75, 69, 70],
  "prior_forecast": 38,
  "is_exception": true,
  "exception_reasons": ["Low confidence (0.42)", "Forecast changed 77% from prior week"]
}
```

Required numeric inputs for rule evaluation:

- `confidence_score`
- `point_forecast`
- `prior_forecast`
- `lower_bound`
- `upper_bound`
- `recent_sales`

# Output schema

All original fields are preserved. Every row is enriched with these fields:

```json
{
  "recommendation": "escalate",
  "recommendation_reason": "Multiple forecast signals require planner escalation.",
  "decision_confidence": 0.12,
  "risk_level": "high",
  "planner_memo": "FOODS_1_007 in FOODS: escalate. Multiple forecast signals require planner escalation."
}
```

Allowed values:

- `recommendation`: `accept` | `override` | `investigate` | `escalate`
- `risk_level`: `low` | `medium` | `high`

# Decision rules

Internal flags are derived from numeric fields only:

- `low_confidence`: `confidence_score < 0.6`
- `big_change`: `abs(point_forecast - prior_forecast) / prior_forecast > 0.30`
- `volatility`: `stdev(recent_sales) / mean(recent_sales) > 0.40`
- `wide_band`: `(upper_bound - lower_bound) / point_forecast > 0.50`

Priority order:

1. If more than one flag is true: `recommendation = escalate`, `risk_level = high`
2. Else if `big_change`: `recommendation = override`, `risk_level = high`
3. Else if `low_confidence`: `recommendation = investigate`, `risk_level = medium`
4. Else if `volatility`: `recommendation = investigate`, `risk_level = high`
5. Else if `wide_band`: `recommendation = investigate`, `risk_level = medium`
6. Else: `recommendation = accept`, `risk_level = low`

Decision confidence starts from `confidence_score`:

- subtract `0.30` when multiple flags are true
- subtract `0.10` when exactly one flag is true
- clamp the result to `[0.0, 1.0]`

Non-exception rows still receive structured outputs, but they always resolve to `accept` with `low` risk.

# How to invoke

```bash
python skills/planner-memo/generate_memos.py <input_json> <output_json>
```

Example:

```bash
python skills/planner-memo/generate_memos.py data/forecasts_with_exceptions.json data/forecasts_with_decisions.json
```

# Examples

Single issue:

```json
{
  "item_id": "HOUSEHOLD_1_005",
  "store_id": "CA_1",
  "category": "HOUSEHOLD",
  "point_forecast": 53,
  "lower_bound": 44,
  "upper_bound": 62,
  "confidence_score": 0.69,
  "recent_sales": [68, 76, 44, 50, 56, 67, 45, 51],
  "prior_forecast": 32,
  "is_exception": true,
  "exception_reasons": ["Forecast changed 66% from prior week"],
  "recommendation": "override",
  "recommendation_reason": "The forecast changed sharply versus the prior plan.",
  "decision_confidence": 0.59,
  "risk_level": "high",
  "planner_memo": "HOUSEHOLD_1_005 in HOUSEHOLD: override. The forecast changed sharply versus the prior plan."
}
```

Multi-issue escalation:

```json
{
  "item_id": "FOODS_1_007",
  "store_id": "CA_1",
  "category": "FOODS",
  "point_forecast": 67,
  "lower_bound": 50,
  "upper_bound": 84,
  "confidence_score": 0.42,
  "recent_sales": [61, 75, 69, 70, 66, 58, 73, 64],
  "prior_forecast": 38,
  "is_exception": true,
  "exception_reasons": ["Low confidence (0.42)", "Forecast changed 77% from prior week"],
  "recommendation": "escalate",
  "recommendation_reason": "Multiple forecast signals require planner escalation.",
  "decision_confidence": 0.12,
  "risk_level": "high",
  "planner_memo": "FOODS_1_007 in FOODS: escalate. Multiple forecast signals require planner escalation."
}
```
