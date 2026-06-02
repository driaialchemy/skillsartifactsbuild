import json
from pathlib import Path

import numpy as np

INPUT_PATH = Path("data/forecasts.json")
LOW_CONFIDENCE_THRESHOLD = 0.60
BIG_CHANGE_THRESHOLD = 0.30
HIGH_VOLATILITY_THRESHOLD = 0.40
WIDE_BAND_THRESHOLD = 0.50
MAX_PULL = 0.45
TOP_ROWS_TO_SHOW = 8


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_ratio(numerator, denominator):
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calibration_metrics(row):
    point = float(row["point_forecast"])
    prior = float(row["prior_forecast"])
    recent = np.array(row["recent_sales"], dtype=float)
    lower = float(row["lower_bound"])
    upper = float(row["upper_bound"])
    confidence = float(row["confidence_score"])

    recent_mean = float(np.mean(recent)) if len(recent) else point
    recent_std = float(np.std(recent)) if len(recent) else 0.0
    recent_trend = safe_ratio(float(np.mean(recent[-7:]) - np.mean(recent[:7])), recent_mean)
    volatility = safe_ratio(recent_std, recent_mean)
    band_ratio = safe_ratio(upper - lower, point)
    change_ratio = safe_ratio(abs(point - prior), prior)

    uncertainty = clamp(
        safe_ratio(LOW_CONFIDENCE_THRESHOLD - confidence, LOW_CONFIDENCE_THRESHOLD),
        0.0,
        1.0,
    )
    change_pressure = clamp(change_ratio / BIG_CHANGE_THRESHOLD, 0.0, 1.0)
    volatility_pressure = clamp(volatility / HIGH_VOLATILITY_THRESHOLD, 0.0, 1.0)
    band_pressure = clamp(band_ratio / WIDE_BAND_THRESHOLD, 0.0, 1.0)
    pull_strength = clamp(
        0.10
        + 0.20 * uncertainty
        + 0.20 * change_pressure
        + 0.10 * volatility_pressure
        + 0.10 * band_pressure,
        0.0,
        MAX_PULL,
    )

    anchor = 0.50 * recent_mean + 0.35 * prior + 0.15 * point * (1 + recent_trend)
    calibrated = int(round(point * (1 - pull_strength) + anchor * pull_strength))

    return {
        "item_id": row["item_id"],
        "category": row["category"],
        "point_forecast": int(point),
        "calibrated_forecast": max(0, calibrated),
        "calibration_delta": int(round(calibrated - point)),
        "pull_strength": round(pull_strength, 3),
        "recent_mean": round(recent_mean, 1),
        "change_ratio": round(change_ratio, 3),
        "volatility_ratio": round(volatility, 3),
        "band_ratio": round(band_ratio, 3),
        "confidence_score": confidence,
    }


def main():
    rows = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    calibrated = [calibration_metrics(row) for row in rows]
    calibrated.sort(key=lambda row: abs(row["calibration_delta"]), reverse=True)

    avg_abs_delta = np.mean([abs(row["calibration_delta"]) for row in calibrated])
    avg_pull = np.mean([row["pull_strength"] for row in calibrated])
    changed = sum(1 for row in calibrated if row["calibration_delta"] != 0)

    print("Forecast Calibration Summary")
    print(f"Input rows: {len(calibrated)}")
    print(f"Rows adjusted: {changed}")
    print(f"Average absolute adjustment: {avg_abs_delta:.2f}")
    print(f"Average pull strength: {avg_pull:.3f}")
    print()
    print(f"Top {min(TOP_ROWS_TO_SHOW, len(calibrated))} calibration adjustments")
    for row in calibrated[:TOP_ROWS_TO_SHOW]:
        direction = "+" if row["calibration_delta"] > 0 else ""
        print(
            f"{row['item_id']} | point={row['point_forecast']} | "
            f"calibrated={row['calibrated_forecast']} | "
            f"delta={direction}{row['calibration_delta']} | pull={row['pull_strength']:.3f}"
        )
        print(
            f"  conf={row['confidence_score']:.2f} recent_mean={row['recent_mean']:.1f} "
            f"change={row['change_ratio']:.3f} vol={row['volatility_ratio']:.3f} "
            f"band={row['band_ratio']:.3f}"
        )


if __name__ == "__main__":
    main()
