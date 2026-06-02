import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from metadata_foundation import MetadataContext, get_current_run_id

SEED = 42
COUNT = 50
STORE_ID = "CA_1"
CATEGORIES = ["HOBBIES", "HOUSEHOLD", "FOODS"]
POINT_MIN = 5
POINT_MAX = 200
LOW_CONFIDENCE_COUNT = 10
EXCEPTION_COUNT = 13
RECENT_DAYS = 28


def build_forecast(index, category, low_confidence, exception_case, rng):
    point = int(rng.integers(POINT_MIN, POINT_MAX + 1))
    confidence = float(np.round(rng.uniform(0.35, 0.59) if low_confidence else rng.uniform(0.6, 0.96), 2))
    noise = max(3, int(point * rng.uniform(0.08, 0.18)))
    recent = np.clip(rng.normal(point, noise, RECENT_DAYS).round().astype(int), 0, None).tolist()
    interval = max(4, int(point * (0.1 + (1 - confidence) * 0.25)))
    lower = max(0, point - interval)
    upper = point + interval
    if exception_case:
        delta = rng.uniform(0.3, 0.55)
        direction = -1 if rng.random() < 0.5 else 1
        prior = int(np.clip(round(point * (1 + direction * delta)), POINT_MIN, POINT_MAX))
        if abs(prior - point) / point < 0.3:
            prior = max(POINT_MIN, point - max(2, int(np.ceil(point * 0.3))))
    else:
        delta = rng.uniform(-0.18, 0.18)
        prior = int(np.clip(round(point * (1 + delta)), POINT_MIN, POINT_MAX))
    return {
        "item_id": f"{category}_1_{index:03d}",
        "store_id": STORE_ID,
        "category": category,
        "point_forecast": point,
        "lower_bound": lower,
        "upper_bound": upper,
        "confidence_score": confidence,
        "recent_sales": recent,
        "prior_forecast": prior,
    }


def main():
    run_id = get_current_run_id()

    with MetadataContext(run_id, stage_number=1, stage_name="generate_forecasts",
                         script_path="scripts/generate_forecasts.py") as ctx:
        ctx.log_threshold("seed", SEED)
        ctx.log_threshold("item_count", COUNT)

        rng = np.random.default_rng(SEED)
        low_confidence_idx = set(rng.choice(COUNT, size=LOW_CONFIDENCE_COUNT, replace=False).tolist())
        exception_idx = set(rng.choice(COUNT, size=EXCEPTION_COUNT, replace=False).tolist())
        counts = {category: 1 for category in CATEGORIES}
        forecasts = []
        for index in range(COUNT):
            category = CATEGORIES[int(rng.integers(0, len(CATEGORIES)))]
            forecasts.append(
                build_forecast(
                    counts[category],
                    category,
                    index in low_confidence_idx,
                    index in exception_idx,
                    rng,
                )
            )
            counts[category] += 1
        output_path = Path("data/forecasts.json")
        output_path.write_text(json.dumps(forecasts, indent=2), encoding="utf-8")

        ctx.log_output(str(output_path), row_count=len(forecasts), fields_added=["item_id", "store_id", "category", "point_forecast", "lower_bound", "upper_bound", "confidence_score", "recent_sales", "prior_forecast"])
        ctx.log_metric("forecasts_generated", len(forecasts))
        ctx.log_metric("low_confidence_count", LOW_CONFIDENCE_COUNT)

        print(f"Wrote {len(forecasts)} forecasts to {output_path}")


if __name__ == "__main__":
    main()
