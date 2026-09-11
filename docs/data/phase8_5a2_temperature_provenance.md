# CLOUDSENSE — PHASE 8.5A.2
## HISTORICAL 1° TEMPERATURE PROVENANCE + OPERATIONAL COMPATIBILITY AUDIT

### 1. Objective and Context
Phase 8.5A.1 identified a critical data resolution mismatch blocking the operationalization of CloudSense:
- **Training Data:** Rainfall (0.25°), Tmax (1.0°), Tmin (1.0°)
- **Operational Data (Real-time):** Rainfall (0.25°), Tmax (0.5°), Tmin (0.5°)

This audit traces the exact provenance of the historical 1.0° temperature data to determine if it can be mathematically reconciled with the operational 0.5° feeds, without violating the system's strict architectural constraints (no model retraining or code modification).

### 2. Historical Provenance Trace
**Source of Truth:**
The historical 1.0° data originates directly from IMD's native historical products.
- **Files:** `data/Maxtemp_MaxT_{year}.GRD`, `data/Mintemp_MinT_{year}.GRD`
- **Resolution:** 1.0° (31x31 Grid)
- **Bounding Box:** Lat [7.5, 37.5], Lon [67.5, 97.5]

**Data Transformations (CloudSense Pipeline):**
1. `src/data/raw_decoder.py` reads the Fortran binary `.GRD` files as a pure 3D tensor (31x31).
2. `src/data/xarray_builder.py` attaches coordinates according to `configs/datasets.yaml` (1.0° spacing) and masks missing values (`99.9`).
3. `src/ml/temperature_features.py` maps the 1.0° grid to the 0.25° rainfall grid using `xarray.interp(method='nearest')`.

**Conclusion on Provenance:** The 1.0° dataset is NOT derived from a higher-resolution grid within CloudSense. It was ingested directly as a 1.0° IMD product. The ML models were trained on 0.25° features derived strictly from this specific 1.0° IMD product via nearest-neighbor interpolation.

### 3. Spatial Relationship and Overlap Experiment
To determine if the 1.0° product is a simple mathematical derivative of the 0.5° operational product, an overlapping-date experiment was conducted for May 2024.

**Coordinate Alignment:**
- 1.0° Coordinates: `7.5, 8.5, 9.5 ... 37.5`
- 0.5° Coordinates: `7.5, 8.0, 8.5, 9.0, 9.5 ... 37.5`
The 1.0° spatial coordinates are a **perfect subset** of the 0.5° operational coordinates.

**Numerical Equivalence (Sub-sampling & Aggregation):**
Despite the perfect coordinate overlap, extracting the 0.5° data at the 1.0° coordinates (center-point subsetting) yields significant discrepancies:
- **Mean Absolute Error:** ~3.14°C
- **Max Absolute Error:** ~88.05°C
- **Correlation:** ~0.905

Further spatial aggregations (3x3 Mean, Max, Min) also fail to exactly reproduce the 1.0° dataset. 

**Conclusion on Compatibility:** The 1.0° historical product is a distinctly generated meteorological dataset by IMD (likely independently interpolated from station data), not a simple mathematical downsampling of the 0.5° product.

### 4. Final Verdict (NO-GO)
> [!CAUTION]
> **HARD BLOCKER IDENTIFIED**
> The operational 0.5° temperature feed cannot be used to perfectly reconstruct the 1.0° data expected by the system.

Any attempt to downsample the 0.5° data (via subsetting or averaging) will introduce a fundamental **distribution shift** (MAE ~3.14°C) into the inference pipeline. Because the ML models were exclusively trained on the underlying statistical distribution of the 1.0° IMD product, feeding shifted data violates the forecasting integrity.

Given the STRICT NO-IMPLEMENTATION RULE (No retraining, no workarounds), we cannot proceed with building the `OperationalIMDProvider`. 

**Required User Action:**
The engineering phase is blocked. The user must decide how to proceed:
1. **Find 1° Operational Source:** Discover a hidden or private IMD API that provides real-time 1.0° data.
2. **Authorize Model Retraining:** Retrain the ML models using the historical 0.5° temperature product (which is available historically) to align the training pipeline with the operational reality.
