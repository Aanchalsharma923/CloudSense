# CloudSense Phase 8.0: Local Inference Engine

## Overview
This document outlines the architecture of the local inference engine created in Phase 8.0. The engine encapsulates the 7 frozen CloudSense LightGBM models into a deterministic, strictly validated wrapper, ensuring robust behavior without altering the underlying models.

## Frozen ML Architecture
- **Model**: LightGBM Tweedie (variance power = 1.5)
- **Horizons**: 7 independent models (H1 through H7)
- **Artifacts Location**: `models/` directory

## The 12-Feature Contract
The engine enforces exactly 12 input features. This ordering is canonically defined and is non-negotiable.

1. `rf_lag_1`
2. `rf_lag_2`
3. `rf_roll7_sum`
4. `days_since_rain`
5. `neighbor_mean_lag1`
6. `neighbor_max_lag1`
7. `tmax_1deg_lag1`
8. `tmin_1deg_lag1`
9. `tmax_1deg_roll7`
10. `diurnal_range_1deg`
11. `sin_doy`
12. `cos_doy`

## Validation Rules
The `InferenceInput` schema strictly rejects:
- Missing fields
- Extra fields
- `NaN` values
- `+infinity` and `-infinity` values
- Non-numeric types (that cannot be cleanly parsed as floats)

If a prediction is valid but slightly negative, the `CloudSensePredictor` safely clamps it to `0.0` at the output boundary, maintaining non-negative rainfall targets.

## Future Data Requirements & Limitations
> [!WARNING]
> This phase **does not** implement real-time weather ingestion. The feature definitions rely on historical time-series state (e.g., `rf_roll7_sum` needs 7 days of rainfall history, spatial features need neighbor rainfall). 

Future orchestration layers *must* reconstruct this historical state prior to generating the feature vector. Do not attempt a shortcut that maps a single "current weather" point directly into the feature contract without preserving historical context.
