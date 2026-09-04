# Phase 4: ML Dataset Design & Formulation

## Overview
This document outlines the design and formulation of the future ML dataset for the CloudSense project. It is based on a rigorous exploratory analysis of the processed, validated 2000–2025 NetCDF historical dataset. No assumptions regarding targets, architecture, or external datasets were made prior to the actual local data audit.

---

## Part 1: Actual Data Audit

**Observation & Audit Results:**
- **Rainfall**: 129x135 grid (0.25°). Valid land points per day: 4,964 (~28.5% of grid). Highly zero-inflated (approx. 75% of days are zero). Rare extremes (>50mm occurs on ~0.38% of valid days). Low short-term autocorrelation (lag-1: ~0.35).
- **Max/Min Temperature**: 31x31 grid (1°). Valid land points per day: 351 (~36.5% of grid). Highly autocorrelated (MaxTemp lag-1: ~0.96).
- **Spatial Overlap**: Exact coordinate intersection on a 1° step yields 961 common coordinate points, of which exactly 306 are overlapping valid land points.
- **Missing Values**: Verified that all missing values are masked cleanly as `NaN` in xarray across all files, matching land/ocean boundaries perfectly. 
- **Anomaly Verification**: The 2019 MaxT file is fully populated and valid, overcoming earlier listing anomalies.

---

## Part 2: Determine What the Data Can Actually Support

**Candidate ML Formulations Evaluated:**

- **A. Daily Rainfall Forecasting (Continuous Regression)**
  - *Feasibility:* Difficult due to zero-inflation (75% zeros) and high variance.
  - *Scientific Usefulness:* High, but typically yields smoothed, conservative predictions that underestimate extremes.
- **B. Daily Temperature Forecasting**
  - *Feasibility:* Highly feasible. Autocorrelation is extremely strong (0.96). 
  - *Scientific Usefulness:* Moderate. Climatology and simple persistence models (e.g., "tomorrow = today") form very strong baselines that are hard to beat.
- **C. Extreme Rainfall Classification (>50mm)**
  - *Feasibility:* Severe class imbalance (~0.38% positive class). Requires advanced sampling and specialized loss functions.
- **D. Short-term Cumulative Rainfall Forecasting (e.g., Next 7-day cumulative)**
  - *Feasibility:* Easier than daily prediction because temporal aggregation smooths out the high stochasticity of single-day events.
  - *Scientific Usefulness:* Very high for agricultural and water-stress planning.

**Decision:** The dataset best supports **Next-Day Daily Rainfall Forecasting**, potentially coupled with an extreme-rainfall classification metric. Temperature is highly predictable and serves as an excellent feature rather than the primary target, though predicting temperature anomalies is also highly supported.

---

## Part 3: Define ONE Observation

**ONE OBSERVATION = A specific valid spatial point (latitude, longitude) on a specific calendar day (date).**

*Rationale:* The data varies highly both spatially and temporally. Aggregating to a month or season destroys the extreme values and the day-to-day weather variance that defines the impact of rainfall. Retaining grid cell + day allows us to construct lag features (e.g., rainfall over the last 3 days) while keeping the target precise.

---

## Part 4: Spatial Representation

**Spatial Options Considered:**
- **A. Aggregate Rainfall to 1°:** Artificial smoothing of high-res rainfall data. Extreme rainfall events are highly localized; 1° smoothing destroys this critical signal.
- **B. Interpolate Temperature to 0.25°:** Injects false precision.
- **C. Map native grids (Recommended approach for Tabular ML):** Treat the 0.25° grid as the primary spatial anchor. For each 0.25° rainfall pixel, map it to the nearest 1° temperature pixel. 
- **D. Restrict to strictly overlapping 1° grid points:** Drops 90% of the rainfall data. 

**Recommendation:** Option C. Keep rainfall at 0.25° (4,964 locations) and join temperature data using nearest-neighbor mapping.
- *Information Loss:* None.
- *Artificial Precision:* None, because we are explicitly labeling it as "Regional Temperature" for a specific rainfall point.
- *Downstream Usability:* Retains the high resolution of the most critical variable (rainfall).

---

## Part 5: Temporal Representation

**Recommendation:** Daily resolution.

*Justification:* 
- Rainfall exhibits very low autocorrelation past lag-2 or lag-3. 
- Aggregating to weekly or monthly entirely removes extreme daily events (e.g., flooding).
- Day-of-year embeddings (cyclical) are required to capture the strong annual monsoon seasonality.

---

## Part 6: Target Design

**Recommended Target:** **Next-Day Rainfall (Continuous, mm)**

*Justification:*
- **Measurability:** Directly available from the next chronological day in the historical dataset.
- **Evaluation:** Can be evaluated using RMSE, MAE, and threshold-based F1 scores (for extremes).
- **Rejected Targets:** 
  - *Temperature:* Too easy (persistence baseline is too strong).
  - *Extreme Only:* Extreme rainfall (e.g., > 90th percentile) is excellent but suffers from too few positive examples for a primary MVP model.
  - *Anomaly:* Hard to define without a 30-year climate normal baseline (we only have 26 years).

---

## Part 7: Feature Design

**Historical Rainfall (Target variable lags):**
- `rf_lag_1`, `rf_lag_2`, `rf_lag_3`: Captures immediate synoptic weather systems.
- `rf_rolling_7d_sum`: Soil moisture proxy and recent wetness trend.
- `days_since_last_rain`: Drought/dry-spell indicator.

**Temperature (Regional context):**
- `tmax_lag_1`, `tmin_lag_1`: Captures immediate regional heat.
- `tmax_rolling_7d_mean`: Captures heatwaves that build up convective energy.
- `temp_diurnal_range` (`tmax - tmin`): Indicates atmospheric stability/cloud cover.

**Temporal (Cyclical):**
- `sin_day_of_year`, `cos_day_of_year`: Captures the rigid annual seasonality of the monsoon without arbitrary categorical month boundaries.

**Spatial:**
- `latitude`, `longitude`: Allows the tree-based model to learn spatial variations (e.g., Western Ghats vs. Central India).

*Leakage Note:* All lag and rolling features MUST be shifted by +1 day relative to the target.

---

## Part 8: Leakage Analysis

**Strict Preprocessing Rules:**
1. **Target Leakage:** The target `rainfall(t)` must never be used to calculate rolling features for `day(t)`. Features must strictly use data up to `day(t-1)`.
2. **Train/Test Contamination:** Standardization (e.g., z-scores) must be fit ONLY on the training period (2000-2018) and transformed on the validation/test periods.
3. **Temporal Leakage in Cross-Validation:** Random K-Fold CV is strictly forbidden. A walk-forward or chronological block split must be used.

---

## Part 9: Missing Data

**Analysis:**
- Missingness is overwhelmingly *permanent spatial missingness* (the ocean/borders). Valid land points are consistently populated.
- Missing values in raw GRD (-999.0 and 99.9) were correctly converted to `NaN` during Phase 3.

**Recommendation:**
- **Permanent Spatial:** Exclude all `NaN` cells at the loading phase. We only model valid land points (4,964 for rainfall).
- **Temporary Temporal:** Very rare in this dataset. If found, forward-fill temperature up to 3 days (due to high autocorrelation). For rainfall, impute with 0.0 (safest assumption for precipitation).

---

## Part 10: Extreme Values

**Analysis:**
- Rainfall values > 100mm/day exist and represent genuine meteorological extremes (e.g., cyclonic systems, monsoon depressions), not sensor errors.
- Max Temp values > 45°C represent genuine summer heatwaves in central/northwestern India.

**Recommendation:**
- DO NOT apply IQR capping, clipping, or removal.
- CloudSense’s primary utility is anticipating extremes; capping them destroys the model's ability to learn the upper tail.
- Use robust scaling methods or tree-based models (which are immune to monotonic extreme outliers).

---

## Part 11: Dataset Size

- **Valid Points:** 4,964 (0.25° grid)
- **Days:** 26 years * 365.25 ≈ 9,496 days
- **Total Rows:** ~47,138,144 rows
- **Columns:** ~15 features + identifiers
- **Estimated Size in Memory (float32):** ~3-4 GB.
- **Feasibility:** Comfortably fits in RAM on a modern 16GB laptop. Highly feasible for LightGBM/XGBoost using histogram binning. 

---

## Part 12: Train / Validation / Test

**Recommendation:** Chronological Block Split
- **Training:** 2000–2018 (19 years) -> captures a wide variety of ENSO cycles.
- **Validation:** 2019–2021 (3 years) -> used for early stopping and hyperparameter tuning.
- **Test:** 2022–2025 (4 years) -> strictly untouched holdout set for final evaluation.

*Why not rolling origin?* With 47 million rows, retraining the model for a rolling walk-forward validation is computationally prohibitive for MVP phase. A static chronological split is scientifically valid and standard for climate datasets.

---

## Part 13: Model Requirements

**Candidates Evaluated:**
- *Linear Regression:* Too simple; cannot capture non-linear geospatial patterns or zero-inflated target.
- *Random Forest:* Computationally expensive and memory-heavy for 47M rows.
- **XGBoost / LightGBM:** Highly recommended. 
  - Supports missing values naturally.
  - Histogram-based training makes 47M rows incredibly fast.
  - Handles non-linear feature interactions (e.g., Lat/Lon + Season).

**Baseline Model:** Climatology Baseline (predicting the historical mean rainfall for that specific pixel on that specific day-of-year).

---

## Part 14: Final ML Dataset Design

| COLUMN | TYPE | UNIT | DESCRIPTION | SOURCE | DERIVED? | LEAKAGE RISK | REQUIRED? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `latitude` | float32 | deg | 0.25° grid latitude | Coordinates | No | None | Yes |
| `longitude` | float32 | deg | 0.25° grid longitude | Coordinates | No | None | Yes |
| `time` | datetime | date | Observation date | Coordinates | No | High (if not split correctly) | Yes |
| `target_rf_next_day` | float32 | mm | Next day rainfall | ind_rfp25 | Yes | CRITICAL | Yes |
| `rf_lag_1` | float32 | mm | Previous day rainfall | ind_rfp25 | Yes | High | Yes |
| `rf_rolling_7d_sum`| float32 | mm | Last 7 days total rainfall | ind_rfp25 | Yes | High | Yes |
| `days_since_rain` | int16 | days | Days since rf > 1mm | ind_rfp25 | Yes | High | Yes |
| `tmax_lag_1` | float32 | °C | Prev day max temp (1° nearest) | Maxtemp_MaxT | Yes | High | Yes |
| `tmin_lag_1` | float32 | °C | Prev day min temp (1° nearest) | Mintemp_MinT | Yes | High | Yes |
| `sin_doy` | float32 | - | Sine of day of year | time | Yes | None | Yes |
| `cos_doy` | float32 | - | Cosine of day of year | time | Yes | None | Yes |

---

## Part 15: Data Pipeline Design

1. **RAW GRD** (Binary arrays)
   ↓ *(Phase 3 Decoder)*
2. **PROCESSED NETCDF** (Daily spatial grids)
   ↓ *(Feature Engineer & Spatial Join)*
3. **FEATURE STORE PARQUET** (Tabular, 47M rows)
   ↓ *(Chronological Splitter)*
4. **TRAIN / VAL / TEST SETS** (DMatrix / LightGBM Datasets)
   ↓ *(Model Training)*
5. **XGBOOST/LIGHTGBM MODEL**

---

## Part 16: CloudSense Product Connection

**DIRECTLY SUPPORTED BY CURRENT DATA:**
- **Forecast Display:** A spatial map predicting tomorrow's rainfall probability for 4,964 grid cells across India.
- **Extreme-Event Alerts:** Highlighting cells where predicted rainfall exceeds historical 95th percentiles.

**REQUIRES ADDITIONAL DATA:**
- **Agricultural Decision Support:** Requires soil moisture, crop calendars, and evapotranspiration data.
- **Water-Stress Analysis:** Requires reservoir levels and river basin routing data.

---

## Part 17: Final Recommendation

1. **Prediction problem:** Next-day spatial rainfall forecasting.
2. **Target:** `target_rf_next_day` (Continuous).
3. **One observation:** 1 grid cell (0.25°) on 1 day.
4. **Spatial representation:** 0.25° primary grid, with nearest-neighbor 1° temperature mapped onto it.
5. **Temporal resolution:** Daily.
6. **Input variables:** Rainfall, Max Temp, Min Temp.
7. **Feature categories:** Lags, rolling aggregates, cyclical time, spatial coordinates.
8. **Prediction horizon:** 1 day ahead (t+1).
9. **Dataset size:** ~47 million rows, ~3 GB RAM.
10. **Train/validation/test strategy:** Chronological block split (2000-18 Train, 2019-21 Val, 2022-25 Test).
11. **Baseline model:** Day-of-year pixel climatology.
12. **Primary ML model:** LightGBM / XGBoost.
13. **Evaluation metrics:** MAE, RMSE, and F1-score for threshold > 20mm.
14. **Missing-data strategy:** Drop permanent spatial ocean pixels. Forward fill temp anomalies; zero-fill rain anomalies.
15. **Extreme-event strategy:** Keep unchanged; do not cap. Tree models will handle them.
16. **Major assumptions:** Nearest-neighbor mapping of 1° temperature accurately reflects the localized 0.25° temperature environment.
17. **Additional data required:** None for the MVP.
18. **Biggest scientific risk:** Zero-inflated target leads the model to predict the median (near-zero) constantly, failing to capture extremes.
19. **Biggest engineering risk:** Constructing a 47M row rolling window in pandas might OOM (Out Of Memory) if not engineered carefully using chunking or Polars.
