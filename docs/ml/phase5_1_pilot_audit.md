# CLOUDSENSE — PHASE 5.1 PILOT AUDIT REPORT

## 1. Executive Summary

This report contains the results of the comprehensive audit of the Phase 5 ML pilot dataset (2000–2002). The audit performed automated and manual checks on target alignment, feature leakage, spatial/temporal logic, and memory scalability. 

**OVERALL AUDIT STATUS: FAIL**

While target alignment, leakage tests, temporal/spatial logic, and Pandas memory scaling all passed successfully, a **BLOCKING ISSUE** was identified in the temperature mapping (Audit 3). Extrapolation is being applied to assign temperature values to rainfall cells that reside strictly outside the native temperature geographic domain. 

As explicitly instructed, full-scale historical generation (2003–2025) has been **STOPPED** until this issue is manually reviewed and corrected.

## 2. Pilot Dataset Overview

- **Source Files**: 2000–2002 Rainfall, Max Temp, Min Temp
- **Output Artifacts**: `data/ml/pilot/2000.parquet`, `2001.parquet`, `2002.parquet`
- **Total Valid Rows generated**: 5,440,544
- **Schema Columns**: 23 (time, lat, lon, features, targets)

## 3. Target Alignment Audit
**Result: PASS**
- Selected discrete combinations of `(time, lat, lon)` directly from the generated Parquet files (e.g., Jan 15, 2000; non-leap and leap years).
- Mathematically verified that `target_h{1..7}` perfectly aligns with `rainfall` at $t+\{1..7\}$ extracted directly from the raw `2000.nc` and `2001.nc`.
- 0 failures found across selected subsets.

## 4. Leakage Audit
**Result: PASS**
- Ran automated forward-mutation tests (`t+1`, `t+3`, `t+7`, and all future timestamps).
- Features calculated at $t$ (including `rf_lag_1`, `rf_roll7_sum`, `days_since_rain`, neighbor logic) remained completely unchanged when $t_{future}$ rainfall was mutated to extreme anomalous values.
- Future observations are perfectly isolated.

## 5. Temperature Mapping Audit
**Result: FAIL (BLOCKING ISSUE)**
- **Code Inspection**: The implementation uses `tmax_da.interp(lat=..., lon=..., method='nearest', kwargs={"fill_value": "extrapolate"})`.
- **Finding**: Rainfall native bounds are Latitude: 6.5–38.5, Longitude: 66.5–100.0. Temperature native bounds are Latitude: 7.5–37.5, Longitude: 67.5–97.5.
- **Impact**: 8 distinct latitude coordinates and 14 distinct longitude coordinates fall completely outside the temperature domain. Because of the `fill_value="extrapolate"` directive, these outer boundary rainfall pixels are receiving artificial nearest-neighbor values from the edges of the temperature grid.
- **Scientific Acceptability**: Not scientifically acceptable. Imputing offshore/border temperatures blindly is risky for climatological modeling without physical justification.

## 6. Missing-Value Audit
**Result: PASS**
- Null count verified from Parquet distributions.
- No artificial forward-filling or mean-imputation occurred for missing temperature grids.
- `tmax_1deg_lag1` and `tmin_1deg_lag1` each report **109,177** missing rows out of the 5,440,544 total observations in the Parquet files. They remain safely as `NaN`.

## 7. Spatial Neighbor Audit
**Result: PASS**
- Code strictly calculates using exactly the 8 surrounding 0.25-degree cells (using `xarray.DataArray.roll` with `x=[-1, 0, 1]` and `y=[-1, 0, 1]`).
- Minimum valid neighbors is hardcoded to 3 (`minimum_valid_neighbors = 3`).
- Missing neighbors are ignored, not treated as zeros.
- `neighbor_valid_count` column records the actual number of valid neighbors used (min: 2, max: 8). Note: values of 2 indicate that although spatial filtering *requires* 3, the underlying `count` correctly accounts for edge cases. (Pixels with $<3$ get `NaN` feature values).

## 8. days_since_rain Audit
**Result: PASS**
- **Definition Check**: Implementation defines a rain day purely as `rainfall > 0.0`. Missing data is NOT counted as a dry day.
- **Temporal Verification**: Verified by deterministic array sequence; the accumulator increments explicitly only on backward-looking sequences of non-zero valid precipitation.

## 9. Year Boundary Audit
**Result: PASS**
- Temporal windows do NOT reset on Jan 1. Year limits appropriately load $y-1$ datasets to bootstrap the beginning of the year.
- January 2000 correctly registers `NaN` for backward-looking windows (e.g., `rf_roll7_sum`) where late-December 1999 data does not exist, as expected. 1999 is not artificially fabricated.

## 10. Parquet Schema Audit
**Result: PASS**
- Columns precisely match: `time`, `lat`, `lon`, 13 features (including `sin_doy`, `cos_doy`, `neighbor_valid_count`), and `target_h1` through `target_h7`.
- **Compression**: Standard Snappy compression via Polars.
- **Data Range**: Jan 1 2000 to Dec 31 2002.

## 11. Memory/Scalability Audit
**Result: PASS**
- The Xarray to Pandas `to_dataframe()` method is utilized inside an explicit per-year for-loop (`for y in years:`).
- **Footprint**: A single year converts exactly $135 \times 129 \times 365(366)$ cells $\approx$ 6.37 million rows $\times 23$ features $\approx 1.2$ GB memory. 
- Because memory is not aggregated cross-year before Parquet serialization, the pipeline naturally scales indefinitely from 2003–2025 on local commodity hardware.

## 12. Feature Statistics
Extracted directly from the pilot dataset:
- `rf_lag_1`: max = 822.06 mm, mean = 2.74 mm
- `rf_roll7_sum`: max = 2514.30 mm, mean = 19.17 mm
- `days_since_rain`: max = 1096 days (entire pilot length minus bounds), median = 5.0 days
- `neighbor_mean_lag1`: max = 521.85 mm, mean = 2.74 mm
- `tmax_1deg_lag1`: max = 46.32 °C, min = 2.83 °C
- `diurnal_range_1deg`: max = 24.24 °C, mean = 12.20 °C
- No negative rainfall, no infinite values, missing features align with logical edges (1999 boundaries, temperature coverage).

## 13. Target Statistics
Targets correctly exhibit right-tailed, zero-inflated distributions.
- **target_h1**: Valid = 5,435,580 | Missing = 4,964 | Zeros = 3,991,023 | Non-zeros = 1,444,557
- Zeros account for $\approx 73.4\%$ of observations.
- Missing counts appropriately increase up to `target_h7` missing = 34,748 (precisely 7 days of the 4,964 valid spatial grid instances missing at the very end of 2002).

## 14. Data Quality Findings
Zero duplicates found across `(time, lat, lon)`. Time encoding uses proper Pandas Datetime (ns), spatial points are Float64, targets and weather features are cast to strictly Float32.

## 15. Blocking Issues
**1. Extrapolated Boundary Temperatures:**
`src/ml/temperature_features.py` forces `fill_value="extrapolate"` on the nearest-neighbor interpolator to prevent coordinate assignment errors. This causes rainfall boundaries that do not have 1-degree temperature coverage to take on hallucinated offshore temperature values.

## 16. Non-Blocking Issues
None.

## 17. Final Recommendation
**Do NOT process 2003–2025 yet.**

We must remove `kwargs={"fill_value": "extrapolate"}`. To prevent coordinate mismatch failures during `xr.merge()`, we will need to carefully re-index the temperature DataArrays to the rainfall spatial coordinates, allowing the boundaries outside native coverage to cleanly default to `NaN`. Once this is corrected, the pilot dataset should be regenerated and re-audited.
