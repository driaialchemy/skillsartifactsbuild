import json
from pathlib import Path

import numpy as np

LOW_CONFIDENCE_THRESHOLD = 0.6
BIG_CHANGE_THRESHOLD = 0.30
HIGH_VOLATILITY_THRESHOLD = 0.40
WIDE_BAND_THRESHOLD = 0.50


def detect_reasons(forecast):
    reasons = []
    score = forecast["confidence_score"]
    point = forecast["point_forecast"]
    prior = forecast["prior_forecast"]
    recent = np.array(forecast["recent_sales"], dtype=float)
    mean_sales = float(np.mean(recent))
    volatility = float(np.std(recent) / mean_sales) if mean_sales else 0.0
    change = abs(point - prior) / prior if prior else 0.0
    band = (forecast["upper_bound"] - forecast["lower_bound"]) / point if point else 0.0
    if score < LOW_CONFIDENCE_THRESHOLD:
        reasons.append(f"Low confidence ({score:.2f})")
    if change > BIG_CHANGE_THRESHOLD:
        reasons.append(f"Forecast changed {change * 100:.0f}% from prior week")
    if volatility > HIGH_VOLATILITY_THRESHOLD:
        reasons.append(f"Recent sales volatility ({volatility * 100:.0f}% of mean)")
    if band > WIDE_BAND_THRESHOLD:
        reasons.append(f"Wide confidence band ({band * 100:.0f}% of point)")
    return reasons


def main():
    input_path = Path("data/forecasts.json")
    output_path = Path("data/forecasts_with_exceptions.json")
    forecasts = json.loads(input_path.read_text(encoding="utf-8"))
    enriched = []
    counts = {
        "Low confidence": 0,
        "Forecast changed": 0,
        "Recent sales volatility": 0,
        "Wide confidence band": 0,
    }
    for forecast in forecasts:
        reasons = detect_reasons(forecast)
        row = dict(forecast)
        row["is_exception"] = bool(reasons)
        row["exception_reasons"] = reasons
        enriched.append(row)
        for reason in reasons:
            for label in counts:
                if reason.startswith(label):
                    counts[label] += 1
    output_path.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
    print(f"Wrote {len(enriched)} forecasts to {output_path}")
    print(f"Flagged {sum(row['is_exception'] for row in enriched)} forecasts")
    for name, count in counts.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
