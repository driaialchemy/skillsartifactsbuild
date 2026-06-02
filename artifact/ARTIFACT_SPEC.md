# Planner Review Console Artifact Spec

Build a single-file React artifact for Claude.ai that acts as a demand-planning review console for forecast exceptions. The artifact should load from pasted JSON data (with inline sample fallback), show a planner's queue of exception items on the left, show the selected item's detail and decision controls on the right, and provide a separate audit log view. The artifact should feel like a compact internal operations tool: fast to scan, easy to act on, and persistent across refreshes through `window.storage`.

## Data loader

A textarea at the top of the console allows pasting forecasts_ranked.json content. When valid JSON is pasted, the artifact loads and uses that data. If the textarea is empty, the artifact falls back to the inline sample dataset so it still renders standalone.

## Data shape

Use an inline array named something like `sampleForecasts` as the artifact's fallback dataset. Each object has this structure:

```json
{
  "item_id": "HOBBIES_1_002",
  "store_id": "CA_1",
  "category": "HOBBIES",
  "point_forecast": 119,
  "lower_bound": 93,
  "upper_bound": 145,
  "confidence_score": 0.51,
  "recent_sales": [121, 121, 133, 127, 123, 134, 107, 113, 110, 115, 105, 125, 117, 104, 109, 122, 127, 139, 148, 123, 109, 98, 122, 111, 115, 113, 118, 130],
  "prior_forecast": 136,
  "is_exception": true,
  "exception_reasons": ["Low confidence (0.51)"],
  "planner_memo": "HOBBIES_1_002 in HOBBIES needs planner review. The item is flagged for low confidence (0.51). Investigate whether recent data is sparse or missing."
}
```

Embed these 5 sample exception items directly in the file so the artifact renders without upload:

```json
[
  {
    "item_id": "HOBBIES_1_002",
    "store_id": "CA_1",
    "category": "HOBBIES",
    "point_forecast": 119,
    "lower_bound": 93,
    "upper_bound": 145,
    "confidence_score": 0.51,
    "recent_sales": [121, 121, 133, 127, 123, 134, 107, 113, 110, 115, 105, 125, 117, 104, 109, 122, 127, 139, 148, 123, 109, 98, 122, 111, 115, 113, 118, 130],
    "prior_forecast": 136,
    "is_exception": true,
    "exception_reasons": ["Low confidence (0.51)"],
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
    "recent_sales": [31, 32, 37, 32, 35, 31, 28, 29, 30, 38, 30, 35, 29, 35, 33, 32, 32, 30, 33, 31, 28, 28, 33, 37, 32, 32, 33, 36],
    "prior_forecast": 35,
    "is_exception": true,
    "exception_reasons": ["Low confidence (0.48)"],
    "planner_memo": "HOUSEHOLD_1_002 in HOUSEHOLD needs planner review. The item is flagged for low confidence (0.48). Investigate whether recent data is sparse or missing."
  },
  {
    "item_id": "HOUSEHOLD_1_005",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 53,
    "lower_bound": 44,
    "upper_bound": 62,
    "confidence_score": 0.69,
    "recent_sales": [68, 76, 44, 50, 56, 67, 45, 51, 59, 56, 50, 52, 42, 51, 51, 55, 49, 57, 61, 54, 56, 53, 53, 47, 56, 52, 70, 66],
    "prior_forecast": 32,
    "is_exception": true,
    "exception_reasons": ["Forecast changed 66% from prior week"],
    "planner_memo": "HOUSEHOLD_1_005 in HOUSEHOLD needs planner review. The item is flagged for forecast changed 66% from prior week. Investigate whether recent promotions, price changes, or seasonality shifts are affecting demand."
  },
  {
    "item_id": "FOODS_1_002",
    "store_id": "CA_1",
    "category": "FOODS",
    "point_forecast": 190,
    "lower_bound": 151,
    "upper_bound": 229,
    "confidence_score": 0.57,
    "recent_sales": [218, 201, 232, 201, 210, 183, 192, 173, 214, 162, 209, 185, 218, 208, 234, 208, 152, 188, 162, 178, 226, 205, 173, 166, 191, 161, 174, 197],
    "prior_forecast": 194,
    "is_exception": true,
    "exception_reasons": ["Low confidence (0.57)"],
    "planner_memo": "FOODS_1_002 in FOODS needs planner review. The item is flagged for low confidence (0.57). Investigate whether recent data is sparse or missing."
  },
  {
    "item_id": "HOUSEHOLD_1_006",
    "store_id": "CA_1",
    "category": "HOUSEHOLD",
    "point_forecast": 198,
    "lower_bound": 172,
    "upper_bound": 224,
    "confidence_score": 0.86,
    "recent_sales": [217, 277, 191, 130, 253, 182, 202, 243, 144, 155, 144, 171, 213, 216, 207, 150, 119, 200, 182, 214, 222, 203, 224, 206, 216, 174, 192, 205],
    "prior_forecast": 138,
    "is_exception": true,
    "exception_reasons": ["Forecast changed 43% from prior week"],
    "planner_memo": "HOUSEHOLD_1_006 in HOUSEHOLD needs planner review. The item is flagged for forecast changed 43% from prior week. Investigate whether recent promotions, price changes, or seasonality shifts are affecting demand."
  }
]
```

## UI layout

Create a two-tab experience at the top level:

- `Review Queue` tab: the main planner workspace.
- `Audit Log` tab: a table or list of all saved decisions.

Within the `Review Queue` tab, use a two-column layout:

- Left panel:
  Show only items where `is_exception === true` and no decision has been saved yet.
  Display each queue row as a selectable card with `item_id`, `category`, and a short summary made from `exception_reasons`.
  Also show a small queue count at the top, such as `5 items remaining`.
  When an item is selected, highlight it clearly.
  If no undecided items remain, replace the queue with an empty-state message like `All exception items have been reviewed`.

- Right panel:
  Show the currently selected item's full detail.
  At the top, display `item_id`, `category`, `store_id`, and current status if a saved decision exists.
  Show key metrics in compact cards: `point_forecast`, `prior_forecast`, `confidence_score`, and the numeric low/high band.
  Include a visual confidence band for the forecast:
  Render a simple horizontal bar where the full width represents the band span and a marker indicates `point_forecast` between `lower_bound` and `upper_bound`.
  Include a 28-day `recent_sales` sparkline using either plain SVG or `recharts`.
  Show `exception_reasons` as a bulleted list or pills.
  Show `planner_memo` in a callout panel meant for quick reading.
  At the bottom, show planner action controls.

Within the `Audit Log` tab:

- Show a reverse-chronological list or table with columns for `timestamp`, `item_id`, `action`, and `reason`.
- If the action was `Accept` or `Escalate` and no reason was entered, show a dash or blank value consistently.
- If there are no log entries yet, show an empty-state message.

## Behavior

Use inline sample data as the source records. On initial load:

- Read all saved decisions from `window.storage`.
- Filter the queue so any item with an existing saved decision does not appear in the left panel.
- Auto-select the first undecided exception item.
- If the selected item becomes decided, automatically move selection to the next undecided item.

Buttons and actions:

- `Accept`:
  Saves a decision for the selected item with action `Accept`.
  No typed reason is required.
  Writes an audit entry with the current timestamp, `item_id`, action, and empty reason.
  Removes the item from the queue immediately.

- `Override`:
  Show a multiline text input labeled something like `Override reason`.
  The submit button for override must stay disabled until the typed reason is at least 10 characters long after trimming whitespace.
  When submitted, save a decision for the selected item with action `Override` and the typed reason.
  Write a matching audit entry.
  Clear the text box after save.
  Remove the item from the queue immediately.

- `Investigate`:
  Follows the same validation rules as `Override` (requires at least 10 trimmed characters).
  Saves a decision for the selected item with action `Investigate` and the typed reason.
  Write a matching audit entry with action `investigate`.
  Clear the text box after save.
  Remove the item from the queue immediately.

- `Escalate`:
  Saves a decision for the selected item with action `Escalate`.
  A typed reason is optional.
  If text is present in the reason box, include it in the saved decision and audit entry.
  Remove the item from the queue immediately.

- `Export`:
  A button in the top bar that exports all saved decisions.
  Reads all decisions from window.storage and produces a downloadable JSON file.
  Output shape matches simulate_planner_feedback.py: `planner_action` (lowercase action), `decision_match` (boolean comparing planner_action to the row's `recommendation` field), `confidence_gap` (abs(decision_confidence - int(decision_match))), `error_type` (none | underreaction | overreaction | judgment_difference), plus `item_id` and `timestamp`.
  Uses the same formulas as simulate_planner_feedback.py for decision_match, confidence_gap, and error_type.

Additional behavior:

- Decided items must disappear from the review queue after any action.
- The audit log should update immediately after each decision without needing refresh.
- If all items are decided, the detail panel should show a completion state instead of item detail.
- Keep all state local to the single file; do not depend on uploads, routing, or server APIs.

## Persistence

Persist decisions with `window.storage` so they survive page refresh.

Use these keys:

- `decisions:<item_id>`:
  Store one object per decided item with fields such as `item_id`, `action`, `reason`, and `timestamp`.

- `audit_log`:
  Store an array of audit entries.
  Each entry should include `timestamp`, `item_id`, `action`, and `reason`.

Persistence rules:

- On load, read `audit_log` first and default to an empty array if absent.
- For each sample item, check `decisions:<item_id>` to determine whether it should still appear in the queue.
- On every action, write both the item-level decision record and the updated audit log back to `window.storage`.
- Use ISO timestamps so the audit log is sortable and readable.

## Styling

Use a clean, professional, minimal internal-tool style. Use Tailwind classes only. Do not use external libraries beyond what Claude.ai artifacts support natively; React, Tailwind, `lucide-react`, and `recharts` are allowed. Favor a bright neutral background, restrained color accents, compact cards, clear typography, and obvious selected and disabled states. Keep spacing tight enough that a planner can scan the queue and detail view without excessive scrolling on a laptop-sized screen.

## Build notes for Claude.ai

- Build everything in a single React artifact file.
- Do not require file upload or external data fetches.
- Start on the `Review Queue` tab.
- Seed the UI from the 5 inline JSON items above.
- Make the default selected item the first undecided item in the queue.
- Ensure the queue summary, detail panel, action buttons, override validation, persistence, and audit log all work end to end.
