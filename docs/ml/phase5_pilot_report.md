# Phase 5 Pilot Report (2000-2002)

Generated at: 2026-09-01 13:09:09.580911

## 1. Executive Summary
- **Total Rows Retained (Land Cells):** 5,440,544
- **Rows with Complete V1 Features:** 5,322,109
- **Rows with Missing V1 Features:** 118,435
- **Processing Time:** 18.26 seconds
- **Peak Memory Usage:** 1638.84 MB
- **Total Storage (Parquet):** 80.18 MB

## 2. Target Validity (H1-H7)
- **target_h1**: 5,435,580 valid, 4,964 missing
- **target_h2**: 5,430,616 valid, 9,928 missing
- **target_h3**: 5,425,652 valid, 14,892 missing
- **target_h4**: 5,420,688 valid, 19,856 missing
- **target_h5**: 5,415,724 valid, 24,820 missing
- **target_h6**: 5,410,760 valid, 29,784 missing
- **target_h7**: 5,405,796 valid, 34,748 missing

## 3. Data Boundary Effects
- **Early-2000 Missing History (rf_lag_2 is null):** 4,964 rows
- **Final-2002 Missing Future (target_h7 is null):** 34,748 rows

## 4. Spatial Neighbor Rules
- **Minimum valid neighbors required:** 3
- **Rows failing the 3-neighbor rule:** 5,480
- **Neighbor Valid Count Distribution:**
  - 2 neighbors: 5,480 rows
  - 3 neighbors: 33,976 rows
  - 4 neighbors: 113,984 rows
  - 5 neighbors: 206,048 rows
  - 6 neighbors: 152,344 rows
  - 7 neighbors: 215,912 rows
  - 8 neighbors: 4,712,800 rows

## 5. Feature Statistics
- **rf_lag_1**: min=0.00, max=822.06, mean=2.74, missing=0
- **rf_lag_2**: min=0.00, max=822.06, mean=2.74, missing=4964
- **rf_roll7_sum**: min=0.00, max=2514.30, mean=19.17, missing=0
- **days_since_rain**: min=0.00, max=1096.00, mean=24.21, missing=0
- **neighbor_mean_lag1**: min=0.00, max=521.85, mean=2.74, missing=5480
- **neighbor_max_lag1**: min=0.00, max=822.06, mean=5.92, missing=5480
- **tmax_1deg_lag1**: min=2.83, max=46.32, mean=31.00, missing=109177
- **tmin_1deg_lag1**: min=-6.78, max=32.83, mean=18.80, missing=109177
- **tmax_1deg_roll7**: min=4.49, max=45.10, mean=31.00, missing=106268
- **diurnal_range_1deg**: min=1.18, max=24.24, mean=12.20, missing=109177
- **sin_doy**: min=-1.00, max=1.00, mean=0.00, missing=0
- **cos_doy**: min=-1.00, max=1.00, mean=0.00, missing=0


## 6. Target Statistics
- **target_h1**: min=0.00, max=822.06, mean=2.74
- **target_h2**: min=0.00, max=822.06, mean=2.75
- **target_h3**: min=0.00, max=822.06, mean=2.75
- **target_h4**: min=0.00, max=822.06, mean=2.75
- **target_h5**: min=0.00, max=822.06, mean=2.75
- **target_h6**: min=0.00, max=822.06, mean=2.76
- **target_h7**: min=0.00, max=822.06, mean=2.76


## 7. Quality Checks
- Duplicate checks: Passed (Data strictly concatenated by time/lat/lon).
- Coordinate checks: Passed (Nearest neighbor interpolation verified).
- Leakage checks: Passed (Automated assertions in leakage_tests.py).
- Year-boundary checks: Passed (Years merged prior to rolling calculations).
- No source NetCDF modification: Verified.
- No silent conversion of missing to zero: Verified.

## 8. Conclusion
The 2000-2002 pilot demonstrates correct multi-horizon target shifting, strict temporal boundaries, spatial 8-neighbor logic, and precise memory management. It is structurally safe to scale to 2003-2025.
