# skillsartifactsbuild

A beginner-friendly learning project for building a demand-planning prototype on top of synthetic M5-Walmart-style forecast data, with a focus on understanding how Claude Skills and Claude Artifacts can be mirrored through simple Python scripts, one real skill folder, and a React artifact specification.

## How to run the review app

```bash
pip install streamlit
streamlit run app\planner_review.py
```

Open the URL Streamlit prints (typically http://localhost:8501).

## Phases

- Phase 0: TBD
- Phase 1: TBD
- Phase 2: TBD
- Phase 3: TBD
- Phase 4: TBD
- Phase 5: Streamlit review app

## Current Checkpoint

System has completed:

- Decision Engine
- Prioritization
- Feedback Simulation
- Calibration Layer
- Artifact phase (learning deliverable)

Current state:

> Internally consistent, not externally validated. Streamlit app is the active validation tool.

## Next Session Starting Point

When resuming:

1. Review calibration_report.json
2. Review calibration_summary.txt
3. Decide ONE direction:
   - Stress testing (recommended)
   - Improve simulation realism
   - Apply threshold adjustments

## ⚠️ Important

- Do NOT modify decision + ranking separation
- Do NOT auto-apply calibration changes
- Do NOT refactor working layers

## Threshold Smoothing Layer (Assurance Phase -- Step 2)

Problem:
Percentile-based tier assignment improved score spread, but small score changes near the 10%, 30%, and 60% cutoffs still created threshold discontinuities.

Solution:
A deterministic post-ranking smoothing layer now applies a small buffer plus hysteresis rule around percentile boundaries. Items inside a 2.5% buffer only retain the higher tier when their score gap versus the next lower item clears a fixed threshold.

New script path:
`scripts/apply_threshold_smoothing.py`

Output file:
`data/forecasts_smoothed_ranked.json`

New fields:
- `original_percentile`
- `smoothed_percentile`
- `tier_decision_reason`

Impact on stability:
This layer preserves the existing scoring pipeline while reducing boundary-driven tier flips under mild and targeted perturbations. It is intended as an assurance layer, not a replacement for scoring or calibration logic.

## Current Status (May 1)

The pipeline now includes:
- Exception detection via `scripts/detect_exceptions.py`
- Decision and memo generation via `scripts/generate_memos.py`
- Calibrated scoring and percentile ranking via `scripts/score_and_rank.py`
- Optional post-ranking threshold smoothing via `scripts/apply_threshold_smoothing.py`
- Stability diagnostics via `scripts/evaluate_ranking_stability_v2.py`
- Top-tier separation diagnostics via `scripts/analyze_top_tier_separation.py`

Validated artifacts now include:
- `data/forecasts_stress_ranked_v3.json`
- `data/forecasts_smoothed_ranked.json`
- `data/ranking_stability_v2_summary.json`
- `data/top_tier_separation_analysis.json`

Latest assessment:
- Global rank stability is strong under perturbation.
- Boundary instability is low after smoothing.
- The top of the ranking is still compressed: top items are stable overall but weakly differentiated by score margin.

Current practical state:
The system is statistically more robust than the initial prototype, but it is still not externally validated against real planner behavior or production demand signals.

Recommended next focus:
- Real-world validation design
- Drift detection
- Further refinement of top-tier decision sharpness

## Latest Session Update (Decision-Aware Analysis)

Added deterministic post-pipeline analysis scripts:
- `scripts/decision_equivalence_analysis.py`
- `scripts/top_tier_clustering_analysis.py`
- `scripts/uncertainty_band_analysis.py`

New output artifacts:
- `data/decision_equivalence_summary.json`
- `data/top_tier_clusters.json`
- `data/uncertainty_band_summary.json`

What these layers measure:
- Decision equivalence across items that land in the same recommendation and priority tier
- Cluster structure within the top-ranked slice
- Rank-position certainty using local score density plus decision confidence

Latest findings:
- Decision-equivalent group structure is present, including overlap within top-ranked items.
- The current top slice in `data/forecasts_ranked.json` forms singleton score clusters under the configured clustering threshold.
- The uncertainty-band analysis marks the current ranked set as low-certainty overall, indicating dense local score neighborhoods and weak practical separation.

Current interpretation:
The system now has both statistical stability diagnostics and decision-aware analysis layers, but practical differentiation between close-ranked items remains limited and should not yet be treated as production-grade decision sharpness.
