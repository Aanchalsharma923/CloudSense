# Phase 4.2/4.3: ML Algorithm & Feature Engineering Design (Final Corrections)

## Overview
This document specifies the machine learning algorithm candidates, feature engineering design, computational architecture, and evaluation strategy for CloudSense Phase 5 experimentation. It incorporates Phase 4.3 final corrections based on the verified statistical properties of the historical 2000–2025 dataset (47M valid land observations, 0.25° rainfall, 1° temperature).

All ML choices in this document are *candidates* or *experiments*. The final production model and thresholds will be selected ONLY after rigorous validation.

---

## Part 1 — Model Status & Candidates

**Candidate Evaluation:**
Standard linear regression fails heavily due to the extreme zero-inflation (~75% zeros). Random Forests are computationally unfeasible to train across 47 million rows. LightGBM provides histogram-based binning, drastically reducing memory usage, making training over 47M rows highly feasible.

**Candidates for Phase 5 Evaluation:**
- **PRIMARY CANDIDATE:** Two-Stage Hurdle LightGBM.
- **SECONDARY CANDIDATE:** Single-stage LightGBM with Tweedie objective.
- **BASELINES:** 
  - Day-of-year pixel climatology.
  - Lag-1 persistence/recent-history baseline.

The final production model must be selected ONLY after validation experiments in Phase 5.

---

## Part 2 — Two-Stage Rainfall Model

**Rain Occurrence Threshold Decision:**
We will *not* permanently hard-code rain occurrence as `>0 mm` without analysis.
Instead, we define an experiment set to evaluate the actual distribution of measurements near zero (e.g., sensor noise vs. true precipitation).
*Experiments for Threshold Definition:*
- `>0.0 mm`
- `>0.1 mm` (standard meteorological trace threshold)
- `>1.0 mm` (standard meteorological wet day)

**Stage 2 (Amount) Transformation:**
$\log1p(x) = \log(x + 1)$ is evaluated as a variance/stability transformation. It is NOT itself an extreme-event handling strategy. Predictions must eventually be inverse-transformed back to original `mm` units for proper evaluation.

---

## Part 3 — Extreme Rainfall Evaluation

Extreme rainfall handling is NOT solved merely by a log-transformation. It must be evaluated separately as a dedicated task.

**Extreme Evaluation Threshold Definition:**
The definition of an "extreme event" will be evaluated based on:
1. Dataset distribution (e.g., > 95th or 99th percentile for that location).
2. Operational usefulness (e.g., > 50mm absolute threshold representing severe flooding risk).

**Mandatory Extreme Event Metrics:**
Instead of accuracy (which is artificially inflated by class imbalance), we will report:
- Precision
- Recall
- F1-Score
- PR-AUC (Precision-Recall AUC)
- Confusion Matrix

---

## Part 4 — Final V1 Feature Engineering & Exact Leakage-Safe Definitions

The initial feature set is deliberately kept small. Every feature uses only information strictly $\le t$ to predict $target(t) = rainfall(t+1)$. No centered rolling windows are permitted.

**Target Definition:**
- `target_rf_next_day` = $Rainfall(t+1)$ at the 0.25° grid cell.

**Rainfall Temporal Features (0.25° resolution):**
- `rf_lag_1` = $Rainfall(t)$
- `rf_lag_2` = $Rainfall(t-1)$
- `rf_roll7_sum` = $\sum_{k=0}^{6} Rainfall(t-k)$
- `days_since_rain` = Count of days extending backward from $t$ where $Rainfall \le threshold$.

**Spatial Rainfall Features (0.25° resolution):**
- `neighbor_mean_lag1` = Average $Rainfall(t)$ of the 8 immediate adjacent 0.25° grid cells (N, S, E, W, NE, NW, SE, SW).
- `neighbor_max_lag1` = Maximum $Rainfall(t)$ among the 8 immediate adjacent 0.25° grid cells.

**Temperature Features (1° resolution, mapped as coarse regional context):**
- `tmax_1deg_lag1` = $MaxTemp(t)$ of the mapped nearest 1° cell.
- `tmin_1deg_lag1` = $MinTemp(t)$ of the mapped nearest 1° cell.
- `tmax_1deg_roll7` = $\frac{1}{7} \sum_{k=0}^{6} MaxTemp(t-k)$ of the mapped nearest 1° cell.
- `diurnal_range_1deg` = `tmax_1deg_lag1` - `tmin_1deg_lag1`

**Seasonal Features:**
- `sin_doy` = $\sin(\frac{2\pi \times DOY(t)}{365.25})$
- `cos_doy` = $\cos(\frac{2\pi \times DOY(t)}{365.25})$

---

## Part 5 — Walk-Forward Temporal Validation

**Validation Strategy:**
The final test period (2022–2025) will remain completely untouched. It will NEVER be used for feature selection, hyperparameter tuning, or model selection.

A block-based walk-forward validation strategy will be deployed to avoid unreasonable training computation while preserving chronological integrity:
- **Block 1:** Train 2000–2014 → Validate 2015–2016
- **Block 2:** Train 2000–2016 → Validate 2017–2018
- **Block 3:** Train 2000–2018 → Validate 2019–2021

Hyperparameter tuning and early stopping will average metrics across these validation folds.
**FINAL TEST:** 2022–2025.

---

## Part 6 — Spatial Validation

A specific spatial generalization holdout is deemed unnecessary for V1, as the goal is predicting future values for existing spatial points, rather than interpolating over unseen physical geographies (like a different country). Temporal holdout effectively prevents temporal leakage.

---

## Part 7 — Feature Ablation Plan & Model Experiments

To isolate the actual contribution of each feature group and algorithm, the following rigorous experiment matrix will be executed evaluated on the identical validation blocks:

**Feature Sets:**
- **E0:** Climatology (No ML features)
- **E1:** Persistence (`rf_lag_1` only)
- **E2:** Rainfall Temporal (`rf_lag_1`, `rf_lag_2`, `rf_roll7_sum`, `days_since_rain`)
- **E3:** Rainfall Temporal + Spatial (`neighbor_mean_lag1`, `neighbor_max_lag1`)
- **E4:** E3 + Temperature (`tmax_1deg_lag1`, etc.)
- **E5:** E4 + Seasonal encoding
- **E6:** Final combined model

**Model Architectures (Evaluated across E2-E6):**
- **M0:** Climatology Baseline
- **M1:** Persistence Baseline
- **M2:** Single-stage LightGBM Tweedie
- **M3:** Two-stage Hurdle LightGBM

---

## Part 8 — Computational Design

To manage tens of millions of observations (47M valid land rows), we will strictly avoid large monolithic pandas DataFrames. 

**Architecture:**
1. **Raw NetCDF** `(xarray)`
2. **Chunked Feature Generation** `(xarray / dask)`
3. **Tabular Conversion** `(Polars)`
4. **Partitioned Storage** `(Parquet, partitioned by Year)`
5. **Model Training** `(LightGBM Dataset / Iterative loading)`

**Estimates:**
- **RAM:** Generation limits to 8-16GB chunks. LightGBM histogram binning allows training ~47M rows in ~3-4 GB RAM.
- **Storage:** Feature Parquet files will total approximately 2-5 GB compressed. Highly feasible locally.

---

## Part 9 — SHAP / Explainability

Explainability is a core component. We will not use SHAP yet, but it is factored into the design.
- **Global Feature Importance:** Used on the validation set to ensure physical features operate logically.
- **Local Explanations:** Explain individual extreme event predictions.
- **Computational Bound:** SHAP values will only be generated over a stratified sample (e.g., 1%) of the validation data to avoid out-of-memory errors.

---

## Part 10 — Phase 4.3 Final Decisions & Remaining Human Decisions

**Verified Facts:**
- The datasets cover 2000–2025 at native 0.25° (Rainfall) and 1° (Temperature) resolution.
- Target $Rainfall(t+1)$ uses strict $\le t$ information.

**Decisions:**
- Spatial interpolation of temperature is rejected; explicit 1° naming conventions are adopted.
- Random K-fold CV is strictly forbidden in favor of chronologically-blocked walk-forward validation.

**Remaining Human Decisions for Phase 5:**
1. Definition of "Rain Occurrence" threshold (e.g., >0.1mm vs >1.0mm) after distribution experiments.
2. Selection of the Extreme Rainfall evaluation threshold (absolute vs. percentile).
3. Final choice of Single-Stage vs Two-Stage model after validation metrics are logged.
