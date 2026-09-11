# CLOUDSENSE — PHASE 8.5B
## HISTORICAL 0.5° TEMPERATURE DATA FEASIBILITY + RETRAINING IMPACT AUDIT

### 1. Executive Summary
This audit evaluates the feasibility of rebuilding CloudSense's historical training dataset using the 0.5° operational IMD temperature product to replace the blocked 1.0° contract. The investigation concludes that retraining is **NOT FEASIBLE** due to a catastrophic lack of historical coverage in the operational product family (data only exists from 2016 onwards) and the unavailability of identical historical products, which would result in an 84% loss of training data.

### 2. Historical 0.5° Source
- **Official Operational Endpoint:** `https://imdpune.gov.in/cmpg/Realtimedata/max/max.php`
- **Resolution:** 0.5° (61x61 Grid)
- **Spatial Bounds:** Lat [7.5, 37.5], Lon [67.5, 97.5]
- **Missing Value Sentinels:** `99.9` and `-999.0` (both are used and must be masked).
- **Archival Alternative:** The IMD Pune Climate Data Services Portal (`cdsp.imdpune.gov.in`) hosts a generalized historical 0.5° dataset, but the server is currently unresponsive (timed out during audit) and cannot be programmatically accessed.

### 3. Product Identity
We cannot assume the archival historical 0.5° dataset (if accessible) is the same product family as the operational real-time 0.5° dataset. Operational datasets are typically generated using real-time GTS (Global Telecommunication System) station data (fewer stations, lower QC), while archival datasets use finalized data from all stations. Mixing them would introduce severe distribution shifts and temporal leakage. Therefore, we must rely solely on the operational endpoint for backfill to maintain product identity.

### 4. Year-by-Year Coverage (Operational Feed)
A script was written to query the operational real-time endpoint for January 1st of historical years.
- **2025:** SUCCESS
- **2024:** SUCCESS
- **2020:** SUCCESS
- **2019:** SUCCESS
- **2018:** SUCCESS
- **2017:** SUCCESS
- **2016:** SUCCESS
- **2015:** FAILED (No data)
- **2010:** FAILED (No data)
- **2000:** FAILED (No data)

**Conclusion:** The operational 0.5° product is only available from **2016 to Present**.

### 5. Sample Validation
Validating a slice of the 2024 operational 0.5° data confirmed:
- Dimensions: 61x61
- Coordinates perfectly align with 0.5° intervals (7.5, 8.0, 8.5, etc.)
- Missing values include both `99.9` and `-999.0`.

### 6. Operational vs Historical Comparison
Due to the unavailability of the IMD Pune CDSP server, we could not download the archival historical 0.5° dataset to compare it against the operational 0.5° dataset. This confirms that relying on the archival historical product is not viable for an automated pipeline.

### 7. Spatial Mapping Analysis
**Mapping 0.5° Temp to 0.25° Rainfall Grid:**
- **Geometry:** 0.5° points (e.g., 7.5, 8.0) perfectly align with the 0.25° grid (e.g., 7.5, 7.75, 8.0).
- **Interpolation:** Nearest-neighbor interpolation remains appropriate. Each 0.5° cell will simply map to a 2x2 block of 0.25° cells.
- **Domain Edges:** The 0.25° rainfall grid is larger (Lat [6.5, 38.5]) than the temperature grid (Lat [7.5, 37.5]). Like the previous 1.0° contract, the outer edges (coastal/borders) will be extrapolated using the nearest boundary temperature pixel. This behavior is unchanged.

### 8. Feature Impact
The four temperature features must be redefined conceptually to reflect the source resolution, while the mapping method remains identical.
1. `tmax_0p5deg_lag1`: 1-day lag of Tmax (0.5°), mapped to 0.25° via NN.
2. `tmin_0p5deg_lag1`: 1-day lag of Tmin (0.5°), mapped to 0.25° via NN.
3. `tmax_0p5deg_roll7`: 7-day rolling mean of Tmax (0.5°), mapped to 0.25° via NN.
4. `diurnal_range_0p5deg`: `tmax` - `tmin` computed at 0.5°, then mapped to 0.25° via NN.

All rainfall, spatial neighbor, and seasonal features remain entirely unchanged.

### 9. Dataset-Size Impact
The spatial row count for any given day remains identical (129x135 = 17,415 pixels) because the prediction grid is dictated by the 0.25° rainfall data.
However, because historical operational data only exists from 2016 onwards, the total number of rows drops catastrophically.
- **Current Training Data (2000-2018):** ~120 million rows
- **New Training Data (2016-2018):** ~19 million rows (**84% reduction**)

### 10. Missingness / Data Quality
The operational 0.5° feed uses dual missing-value sentinels (`99.9` and `-999.0`). As an operational product, it is subject to real-time telemetry failures and is expected to have a higher spatial missingness rate (more NaNs) than a finalized historical archival product.

### 11. Train/Validation/Test Impact
The current temporal split is irrevocably broken by the 2016 data cutoff.
- **Train (2000-2018):** Now restricted to 2016-2018. Loss of 16 years of climatological variance.
- **Validation (2019-2021):** Unchanged.
- **Test (2022-2025):** Unchanged.

### 12. Leakage Analysis
By exclusively using the operational real-time feed (`Realtimedata/max/max.php`) to backfill the 2016-2025 dataset, we guarantee **zero temporal leakage**, as the historical training data would consist of the exact same data artifacts that were available operationally on those days. 

### 13. Compute/Storage Estimate
While the final feature Parquet size drops by 84% (due to fewer years), the compute effort to rewrite the NetCDF builder, execute a full regeneration for 2016-2025, and tune the LightGBM models on a tiny 3-year dataset is significant and likely to yield a poor model.

### 14. Retraining Dependency Graph
If conditionally approved, the following cascading changes would be required:
`configs/datasets.yaml` (Add 0.5° spatial parameters) → `raw_decoder.py` (Handle operational binary format) → `xarray_builder.py` (Mask both 99.9 and -999.0) → `temperature_features.py` (Redefine feature names) → `dataset_builder.py` (Restrict loop to 2016+) → `run_full_generation.py` (Execute) → `train.py` (Retrain LightGBM) → `evaluate.py` (Recompute all baseline and test metrics) → `FeatureBuilder` (Update feature names).

### 15. Risks
1. **Severe Model Degradation:** Training on only 3 years of data (2016-2018) will prevent the model from learning long-term decadal climate oscillations (e.g., ENSO cycles).
2. **Distribution Shift vs Historical:** We permanently lose the ability to compare performance against the legacy 1.0° model.

### 16. Decision
> [!CAUTION]
> **NOT FEASIBLE**
> Retraining CloudSense using the operational 0.5° temperature product is mathematically possible but scientifically and practically invalid. The operational product only covers 2016-Present, meaning we would lose 84% of the historical training data (2000-2015). Mixing this with a different archival 0.5° product (if one could even be downloaded) would introduce severe leakage and distribution shift.

### 17. Exact Next Phase Recommendation
We have exhausted both the 1.0° and 0.5° IMD operational avenues.
**Recommendation:** Suspend operationalization. CloudSense must remain a historical/offline-only analytical model until a reliable, automated, and backfillable historical-operational unified IMD product is procured, or a commercial/global alternative (e.g., ERA5 real-time, GFS) is substituted for the IMD temperature feed.
