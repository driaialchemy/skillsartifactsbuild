# 1. Project Overview

This project implements a five-step synthetic demand-planning pipeline for Walmart-style daily item forecasts. It generates 50 reproducible synthetic forecast records, flags exception items with rule-based logic, adds deterministic planner memos to flagged rows, provides a Markdown specification for a React-based planner review console to be built in Claude.ai, and packages the memo step as a reusable Claude Skill.

# 2. Directory Structure

```text
skillsartifactsbuild/
├── AGENTS.md
├── README.md
├── PROJECT_STATE_SUMMARY.md
├── artifact/
│   ├── ARTIFACT_SPEC.md
│   └── planner_console.jsx
├── data/
│   ├── forecasts.json
│   ├── forecasts_with_exceptions.json
│   └── forecasts_with_memos.json
├── scripts/
│   ├── generate_forecasts.py
│   ├── detect_exceptions.py
│   └── generate_memos.py
└── skills/
    └── planner-memo/
        ├── SKILL.md
        ├── README.md
        └── generate_memos.py
```

# 3. Memory File

`AGENTS.md` exists. `CLAUDE.md` was not present in the project root during inspection.

- Project goal: a learning sandbox for synthetic demand planning, Claude Skills, and Claude Artifacts
- Allowed stack: Python 3.10+ with standard library plus `numpy` only
- Folder roles are explicitly defined for `data/`, `scripts/`, `skills/`, and `artifact/`
- Scripts should stay under 150 lines when practical
- Rule-based scripts should place threshold constants at the top
- Every script must run standalone with `python scripts/<name>.py`
- Workflow requires reading existing files before changes
- Workflow requires running relevant scripts to verify work
- Workflow expects a descriptive commit after each phase

# 4. Pipeline Summary

## Phase 0: Forecast generation

- Input: no external data; synthetic generation only
- Output: `data/forecasts.json`
- Purpose: create 50 reproducible M5-Walmart-style forecast records for downstream phases

## Phase 1: Exception detection

- Input: `data/forecasts.json`
- Output: `data/forecasts_with_exceptions.json`
- Purpose: append `is_exception` and `exception_reasons` using fixed rule thresholds

## Phase 2: Planner memos

- Input: `data/forecasts_with_exceptions.json`
- Output: `data/forecasts_with_memos.json`
- Purpose: append plain-English `planner_memo` text to exception rows only

## Phase 3: Artifact spec

- Input: `data/forecasts_with_memos.json` plus the project’s review-console requirements
- Output: `artifact/ARTIFACT_SPEC.md`
- Purpose: define a single-file React artifact for Claude.ai that reviews exception items, records decisions, and persists them via `window.storage`

## Phase 4: Skill packaging

- Input: the memo-generation logic from `scripts/generate_memos.py` and the exception-enriched JSON contract
- Output: `skills/planner-memo/`
- Purpose: package memo generation as a Claude Skill with trigger metadata, instructions, and a path-driven bundled script

# 5. Data Schemas

## forecasts.json

- `item_id`: `str`
- `store_id`: `str`
- `category`: `str`
- `point_forecast`: `int`
- `lower_bound`: `int`
- `upper_bound`: `int`
- `confidence_score`: `float`
- `recent_sales`: `list[int]`
- `prior_forecast`: `int`

## forecasts_with_exceptions.json

- `item_id`: `str`
- `store_id`: `str`
- `category`: `str`
- `point_forecast`: `int`
- `lower_bound`: `int`
- `upper_bound`: `int`
- `confidence_score`: `float`
- `recent_sales`: `list[int]`
- `prior_forecast`: `int`
- `is_exception`: `bool`
- `exception_reasons`: `list[str]`

## forecasts_with_memos.json

- `item_id`: `str`
- `store_id`: `str`
- `category`: `str`
- `point_forecast`: `int`
- `lower_bound`: `int`
- `upper_bound`: `int`
- `confidence_score`: `float`
- `recent_sales`: `list[int]`
- `prior_forecast`: `int`
- `is_exception`: `bool`
- `exception_reasons`: `list[str]`
- `planner_memo`: `str` on exception rows only

# 6. Data Samples (5 rows each)

## forecasts.json

```json
[
  {
    "item_id": "HOBBIES_1_001",
    "store_id": "CA_1",
    "category": "HOBBIES",
    "point_forecast": 195,
    "lower_bound": 172,
    "upper_bound": 218,
    "confidence_score": 0.92,
    "recent_sales": [
      184,
      211,
      206,
      207,
      208,
      259,
      183,
      180,
      171,
      213,
      229,
      192,
      170,
      170,
      215,
      217,
      211,
      175,
      202,
      199,
      202,
      221,
      202,
      215,
      197,
      204,
      214,
      151
    ],
    "prior_forecast": 200
  },
  {
    "item_id": "HOUSEHOLD_1_001",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 94,
    "lower_bound": 80,
    "upper_bound": 108,
    "confidence_score": 0.8,
    "recent_sales": [
      106,
      87,
      102,
      81,
      91,
      95,
      99,
      100,
      100,
      91,
      90,
      101,
      92,
      84,
      85,
      87,
      98,
      95,
      100,
      91,
      95,
      99,
      92,
      98,
      89,
      91,
      91,
      84
    ],
    "prior_forecast": 93
  },
  {
    "item_id": "FOODS_1_001",
    "store_id": "CA_1",
    "category": "FOODS",
    "point_forecast": 36,
    "lower_bound": 31,
    "upper_bound": 41,
    "confidence_score": 0.78,
    "recent_sales": [
      37,
      38,
      36,
      35,
      36,
      31,
      32,
      32,
      33,
      37,
      33,
      35,
      40,
      35,
      38,
      33,
      35,
      33,
      35,
      39,
      31,
      37,
      37,
      34,
      32,
      36,
      34,
      37
    ],
    "prior_forecast": 38
  },
  {
    "item_id": "HOBBIES_1_002",
    "store_id": "CA_1",
    "category": "HOBBIES",
    "point_forecast": 119,
    "lower_bound": 93,
    "upper_bound": 145,
    "confidence_score": 0.51,
    "recent_sales": [
      121,
      121,
      133,
      127,
      123,
      134,
      107,
      113,
      110,
      115,
      105,
      125,
      117,
      104,
      109,
      122,
      127,
      139,
      148,
      123,
      109,
      98,
      122,
      111,
      115,
      113,
      118,
      130
    ],
    "prior_forecast": 136
  },
  {
    "item_id": "HOUSEHOLD_1_002",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 32,
    "lower_bound": 25,
    "upper_bound": 39,
    "confidence_score": 0.48,
    "recent_sales": [
      31,
      32,
      37,
      32,
      35,
      31,
      28,
      29,
      30,
      38,
      30,
      35,
      29,
      35,
      33,
      32,
      32,
      30,
      33,
      31,
      28,
      28,
      33,
      37,
      32,
      32,
      33,
      36
    ],
    "prior_forecast": 35
  }
]
```

## forecasts_with_exceptions.json

```json
[
  {
    "item_id": "HOBBIES_1_001",
    "store_id": "CA_1",
    "category": "HOBBIES",
    "point_forecast": 195,
    "lower_bound": 172,
    "upper_bound": 218,
    "confidence_score": 0.92,
    "recent_sales": [
      184,
      211,
      206,
      207,
      208,
      259,
      183,
      180,
      171,
      213,
      229,
      192,
      170,
      170,
      215,
      217,
      211,
      175,
      202,
      199,
      202,
      221,
      202,
      215,
      197,
      204,
      214,
      151
    ],
    "prior_forecast": 200,
    "is_exception": false,
    "exception_reasons": []
  },
  {
    "item_id": "HOUSEHOLD_1_001",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 94,
    "lower_bound": 80,
    "upper_bound": 108,
    "confidence_score": 0.8,
    "recent_sales": [
      106,
      87,
      102,
      81,
      91,
      95,
      99,
      100,
      100,
      91,
      90,
      101,
      92,
      84,
      85,
      87,
      98,
      95,
      100,
      91,
      95,
      99,
      92,
      98,
      89,
      91,
      91,
      84
    ],
    "prior_forecast": 93,
    "is_exception": false,
    "exception_reasons": []
  },
  {
    "item_id": "FOODS_1_001",
    "store_id": "CA_1",
    "category": "FOODS",
    "point_forecast": 36,
    "lower_bound": 31,
    "upper_bound": 41,
    "confidence_score": 0.78,
    "recent_sales": [
      37,
      38,
      36,
      35,
      36,
      31,
      32,
      32,
      33,
      37,
      33,
      35,
      40,
      35,
      38,
      33,
      35,
      33,
      35,
      39,
      31,
      37,
      37,
      34,
      32,
      36,
      34,
      37
    ],
    "prior_forecast": 38,
    "is_exception": false,
    "exception_reasons": []
  },
  {
    "item_id": "HOBBIES_1_002",
    "store_id": "CA_1",
    "category": "HOBBIES",
    "point_forecast": 119,
    "lower_bound": 93,
    "upper_bound": 145,
    "confidence_score": 0.51,
    "recent_sales": [
      121,
      121,
      133,
      127,
      123,
      134,
      107,
      113,
      110,
      115,
      105,
      125,
      117,
      104,
      109,
      122,
      127,
      139,
      148,
      123,
      109,
      98,
      122,
      111,
      115,
      113,
      118,
      130
    ],
    "prior_forecast": 136,
    "is_exception": true,
    "exception_reasons": [
      "Low confidence (0.51)"
    ]
  },
  {
    "item_id": "HOUSEHOLD_1_002",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 32,
    "lower_bound": 25,
    "upper_bound": 39,
    "confidence_score": 0.48,
    "recent_sales": [
      31,
      32,
      37,
      32,
      35,
      31,
      28,
      29,
      30,
      38,
      30,
      35,
      29,
      35,
      33,
      32,
      32,
      30,
      33,
      31,
      28,
      28,
      33,
      37,
      32,
      32,
      33,
      36
    ],
    "prior_forecast": 35,
    "is_exception": true,
    "exception_reasons": [
      "Low confidence (0.48)"
    ]
  }
]
```

## forecasts_with_memos.json

```json
[
  {
    "item_id": "HOBBIES_1_001",
    "store_id": "CA_1",
    "category": "HOBBIES",
    "point_forecast": 195,
    "lower_bound": 172,
    "upper_bound": 218,
    "confidence_score": 0.92,
    "recent_sales": [
      184,
      211,
      206,
      207,
      208,
      259,
      183,
      180,
      171,
      213,
      229,
      192,
      170,
      170,
      215,
      217,
      211,
      175,
      202,
      199,
      202,
      221,
      202,
      215,
      197,
      204,
      214,
      151
    ],
    "prior_forecast": 200,
    "is_exception": false,
    "exception_reasons": []
  },
  {
    "item_id": "HOUSEHOLD_1_001",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 94,
    "lower_bound": 80,
    "upper_bound": 108,
    "confidence_score": 0.8,
    "recent_sales": [
      106,
      87,
      102,
      81,
      91,
      95,
      99,
      100,
      100,
      91,
      90,
      101,
      92,
      84,
      85,
      87,
      98,
      95,
      100,
      91,
      95,
      99,
      92,
      98,
      89,
      91,
      91,
      84
    ],
    "prior_forecast": 93,
    "is_exception": false,
    "exception_reasons": []
  },
  {
    "item_id": "FOODS_1_001",
    "store_id": "CA_1",
    "category": "FOODS",
    "point_forecast": 36,
    "lower_bound": 31,
    "upper_bound": 41,
    "confidence_score": 0.78,
    "recent_sales": [
      37,
      38,
      36,
      35,
      36,
      31,
      32,
      32,
      33,
      37,
      33,
      35,
      40,
      35,
      38,
      33,
      35,
      33,
      35,
      39,
      31,
      37,
      37,
      34,
      32,
      36,
      34,
      37
    ],
    "prior_forecast": 38,
    "is_exception": false,
    "exception_reasons": []
  },
  {
    "item_id": "HOBBIES_1_002",
    "store_id": "CA_1",
    "category": "HOBBIES",
    "point_forecast": 119,
    "lower_bound": 93,
    "upper_bound": 145,
    "confidence_score": 0.51,
    "recent_sales": [
      121,
      121,
      133,
      127,
      123,
      134,
      107,
      113,
      110,
      115,
      105,
      125,
      117,
      104,
      109,
      122,
      127,
      139,
      148,
      123,
      109,
      98,
      122,
      111,
      115,
      113,
      118,
      130
    ],
    "prior_forecast": 136,
    "is_exception": true,
    "exception_reasons": [
      "Low confidence (0.51)"
    ],
    "planner_memo": "HOBBIES_1_002 in HOBBIES needs planner review. The item is flagged for low confidence (0.51). Investigate whether recent data is sparse or missing."
  },
  {
    "item_id": "HOUSEHOLD_1_002",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 32,
    "lower_bound": 25,
    "upper_bound": 39,
    "confidence_score": 0.48,
    "recent_sales": [
      31,
      32,
      37,
      32,
      35,
      31,
      28,
      29,
      30,
      38,
      30,
      35,
      29,
      35,
      33,
      32,
      32,
      30,
      33,
      31,
      28,
      28,
      33,
      37,
      32,
      32,
      33,
      36
    ],
    "prior_forecast": 35,
    "is_exception": true,
    "exception_reasons": [
      "Low confidence (0.48)"
    ],
    "planner_memo": "HOUSEHOLD_1_002 in HOUSEHOLD needs planner review. The item is flagged for low confidence (0.48). Investigate whether recent data is sparse or missing."
  }
]
```

# 7. Exception Detection Logic

- Thresholds used in `scripts/detect_exceptions.py`:
  - `LOW_CONFIDENCE_THRESHOLD = 0.6`
  - `BIG_CHANGE_THRESHOLD = 0.30`
  - `HIGH_VOLATILITY_THRESHOLD = 0.40`
  - `WIDE_BAND_THRESHOLD = 0.50`
- Formulas:
  - Low confidence: `confidence_score < 0.6`
  - Big change: `abs(point_forecast - prior_forecast) / prior_forecast > 0.30`
  - High volatility: `stdev(recent_sales) / mean(recent_sales) > 0.40`
  - Wide band: `(upper_bound - lower_bound) / point_forecast > 0.50`
- Logic type: binary flagging only; `is_exception` is `True` if any rule triggers
- Output form: rule text is stored as human-readable strings in `exception_reasons`
- Observed current output from `forecasts_with_exceptions.json`:
  - 20 of 50 rows flagged
  - Rule counts: `Forecast changed` 12, `Low confidence` 10, `Wide confidence band` 1, `Recent sales volatility` 0

Short snippet:

```python
if score < LOW_CONFIDENCE_THRESHOLD:
    reasons.append(f"Low confidence ({score:.2f})")
if change > BIG_CHANGE_THRESHOLD:
    reasons.append(f"Forecast changed {change * 100:.0f}% from prior week")
```

# 8. Memo Generation Logic

- Inputs used:
  - `item_id`
  - `category`
  - `is_exception`
  - `exception_reasons`
- Recommendation mapping exists and is static:
  - `Low confidence` -> `recent data is sparse or missing`
  - `Forecast changed` -> `recent promotions, price changes, or seasonality shifts are affecting demand`
  - `Recent sales volatility` -> `stockouts, returns, or data-entry errors are distorting recent sales`
  - `Wide confidence band` -> `more historical data would tighten the estimate`
- Confidence exists only as an upstream numeric field and as text echoed inside `exception_reasons`; memo generation does not compute a new confidence value
- Risk does not exist as a separate field, score, class, or escalation recommendation
- Decision formation:
  - no accept/override/escalate decision is made in the data pipeline
  - the script simply builds a 2-sentence memo for exception rows
  - sentence 1 names the item and restates the triggered reasons
  - sentence 2 combines one or more mapped investigation suggestions into a single sentence
- Non-exception rows are passed through unchanged and receive no `planner_memo`

# 9. Artifact Spec Summary

The artifact specification in `artifact/ARTIFACT_SPEC.md` defines a single-file React review console with two top-level tabs: `Review Queue` and `Audit Log`. The review queue uses a left panel for undecided exception items and a right panel for the selected item’s detail, including point forecast, prior forecast, confidence score, numeric band, a visual confidence-band bar, a 28-day sparkline, the exception reason list, and the planner memo. The spec embeds five sample exception items inline so the UI can render without upload.

User actions defined in the spec:

- `Accept`
- `Override`
- `Escalate`

State changes are defined. Decisions are persisted through `window.storage`, decided items disappear from the queue, override requires a typed reason of at least 10 trimmed characters, and an audit log entry is created for every decision with `timestamp`, `item_id`, `action`, and `reason`.

# 10. Skill Package Summary

The packaged skill at `skills/planner-memo/` wraps the Phase 2 memo logic as a Claude Skill. It uses `SKILL.md` frontmatter and body text to describe when the skill should trigger, and a bundled `generate_memos.py` that runs as:

```bash
python generate_memos.py <input_json> <output_json>
```

Inputs:

- a JSON array of forecast rows already enriched with `is_exception` and `exception_reasons`

Outputs:

- the same JSON structure, with `planner_memo` added only to exception rows

Reusability level:

- moderately reusable inside the narrow contract of this project
- path-driven and no longer hardcoded
- still tightly coupled to the exact exception-reason prefixes used by the pipeline

# 11. Git State

Last 5 commit messages:

- `Phase 4: planner-memo skill packaged`
- `Phase 3: artifact spec`
- `Phase 2: planner memos`
- `Phase 1: exception detection`
- `Phase 0: synthetic forecast data`

Working directory status:

- not clean
- one untracked file was present during inspection: `artifact/planner_console.jsx`

# 12. Observed Limitations (IMPORTANT)

- Forecast generation is synthetic only and does not model true M5 hierarchy, calendar effects, promotions, price history, or store/item relationships beyond `store_id = "CA_1"`.
- The dataset contract is weakly enforced. Scripts assume the expected keys exist and do not validate schema, types, or array lengths.
- Exception detection is purely binary. There is no severity score, ranking, prioritization, or separate exception class.
- `exception_reasons` is stored as free-form strings, which makes downstream logic depend on string-prefix matching instead of stable rule IDs.
- The volatility rule is effectively inactive on the current generated data; the current output contains zero `Recent sales volatility` exceptions.
- Memo generation is shallow and deterministic. It does not look at forecast magnitude, band width, trend shape, or recent sales values directly beyond the precomputed reason strings.
- Memos are advisory text only. They do not produce structured planner recommendations, recommended actions, owners, due dates, or confidence in the memo itself.
- `planner_memo` is optional by row rather than normalized into a separate decision-ready object, which limits consistency for downstream consumers.
- The artifact is only specified in Markdown; the committed Phase 3 deliverable is not a tested UI implementation inside this repo.
- The packaged skill is reusable only if the input already follows this project’s exact exception-enriched JSON contract and reason labeling scheme.
