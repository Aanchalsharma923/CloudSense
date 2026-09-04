# CLOUDSENSE — PHASE 6 FULL HISTORICAL ML DATASET REPORT

## 1. Executive Summary
The full historical dataset (2000-2025) has been generated successfully and organized into chronological splits.

## 2. Dataset Architecture
- **Source:** `data/processed/` NetCDF files (READ-ONLY, untouched).
- **Output:** `data/ml/` partitioned by split and year.

## 3. Storage & Row Statistics

- **Total Rows:** 47,143,108
- **Total Parquet Size:** 724.33 MB
- **Peak RAM during processing:** 10149.27 MB
- **Total Processing Time:** 71.12 s

### Rows by Split
- **TRAIN**: 34,450,160 rows
- **VALIDATION**: 5,440,544 rows
- **TEST**: 7,252,404 rows

## 4. Analysis: TRAIN

### Target Statistics (H1-H7)

| Horizon | Valid | Missing | Zero | NonZero | Mean | Median | p90 | p95 | p99 | Max |
|---|---|---|---|---|---|---|---|---|---|---|
| target_h1 | 34,450,160 | 0 | 24,939,903 | 9,510,257 | 3.0144 | 0.0000 | 8.0334 | 17.9128 | 49.9535 | 822.0633 |
| target_h2 | 34,450,160 | 0 | 24,939,672 | 9,510,488 | 3.0144 | 0.0000 | 8.0334 | 17.9128 | 49.9535 | 822.0633 |
| target_h3 | 34,450,160 | 0 | 24,939,396 | 9,510,764 | 3.0145 | 0.0000 | 8.0334 | 17.9128 | 49.9535 | 822.0633 |
| target_h4 | 34,450,160 | 0 | 24,939,166 | 9,510,994 | 3.0145 | 0.0000 | 8.0334 | 17.9128 | 49.9535 | 822.0633 |
| target_h5 | 34,450,160 | 0 | 24,938,718 | 9,511,442 | 3.0146 | 0.0000 | 8.0340 | 17.9139 | 49.9535 | 822.0633 |
| target_h6 | 34,450,160 | 0 | 24,938,277 | 9,511,883 | 3.0147 | 0.0000 | 8.0343 | 17.9139 | 49.9537 | 822.0633 |
| target_h7 | 34,450,160 | 0 | 24,937,942 | 9,512,218 | 3.0147 | 0.0000 | 8.0344 | 17.9139 | 49.9533 | 822.0633 |

### Feature Statistics

| Feature | Valid | Missing | Min | Max | Mean | Median | Flags |
|---|---|---|---|---|---|---|---|
| rf_lag_1 | 34,450,160 | 0 | 0.0000 | 822.0633 | 3.0144 | 0.0000 |  |
| rf_lag_2 | 34,445,196 | 4,964 | 0.0000 | 822.0633 | 3.0149 | 0.0000 |  |
| rf_roll7_sum | 34,450,160 | 0 | 0.0000 | 2788.0159 | 21.1008 | 0.5702 |  |
| days_since_rain | 34,450,160 | 0 | 0.0000 | 6940.0000 | 30.4172 | 5.0000 |  |
| neighbor_mean_lag1 | 34,415,460 | 34,700 | 0.0000 | 584.3697 | 3.0174 | 0.0000 |  |
| neighbor_max_lag1 | 34,415,460 | 34,700 | 0.0000 | 822.0633 | 6.1057 | 0.0000 |  |
| tmax_1deg_lag1 | 33,936,218 | 513,942 | 0.9400 | 48.4648 | 31.0504 | 31.3800 |  |
| tmin_1deg_lag1 | 33,947,484 | 502,676 | -9.0300 | 33.2000 | 18.8747 | 20.6186 |  |
| tmax_1deg_roll7 | 33,970,768 | 479,392 | 3.2557 | 46.8869 | 31.0437 | 31.3414 |  |
| diurnal_range_1deg | 33,930,078 | 520,082 | -0.6700 | 24.5400 | 12.1737 | 12.3350 |  |
| sin_doy | 34,450,160 | 0 | -1.0000 | 1.0000 | 0.0000 | -0.0043 |  |
| cos_doy | 34,450,160 | 0 | -1.0000 | 1.0000 | 0.0000 | 0.0011 |  |

## 4. Analysis: VALIDATION

### Target Statistics (H1-H7)

| Horizon | Valid | Missing | Zero | NonZero | Mean | Median | p90 | p95 | p99 | Max |
|---|---|---|---|---|---|---|---|---|---|---|
| target_h1 | 5,440,544 | 0 | 3,761,704 | 1,678,840 | 3.4409 | 0.0000 | 9.6811 | 20.0103 | 53.7291 | 539.9128 |
| target_h2 | 5,440,544 | 0 | 3,761,413 | 1,679,131 | 3.4414 | 0.0000 | 9.6830 | 20.0136 | 53.7353 | 539.9128 |
| target_h3 | 5,440,544 | 0 | 3,761,539 | 1,679,005 | 3.4413 | 0.0000 | 9.6832 | 20.0138 | 53.7377 | 539.9128 |
| target_h4 | 5,440,544 | 0 | 3,761,279 | 1,679,265 | 3.4416 | 0.0000 | 9.6848 | 20.0155 | 53.7377 | 539.9128 |
| target_h5 | 5,440,544 | 0 | 3,760,707 | 1,679,837 | 3.4418 | 0.0000 | 9.6859 | 20.0124 | 53.7377 | 539.9128 |
| target_h6 | 5,440,544 | 0 | 3,759,476 | 1,681,068 | 3.4447 | 0.0000 | 9.7009 | 20.0296 | 53.7510 | 539.9128 |
| target_h7 | 5,440,544 | 0 | 3,758,538 | 1,682,006 | 3.4459 | 0.0000 | 9.7060 | 20.0328 | 53.7529 | 539.9128 |

### Feature Statistics

| Feature | Valid | Missing | Min | Max | Mean | Median | Flags |
|---|---|---|---|---|---|---|---|
| rf_lag_1 | 5,440,544 | 0 | 0.0000 | 539.9128 | 3.4403 | 0.0000 |  |
| rf_lag_2 | 5,440,544 | 0 | 0.0000 | 539.9128 | 3.4397 | 0.0000 |  |
| rf_roll7_sum | 5,440,544 | 0 | 0.0000 | 2053.1184 | 24.0593 | 2.5000 |  |
| days_since_rain | 5,440,544 | 0 | 0.0000 | 8036.0000 | 30.1946 | 3.0000 |  |
| neighbor_mean_lag1 | 5,435,064 | 5,480 | 0.0000 | 463.3798 | 3.4417 | 0.0000 |  |
| neighbor_max_lag1 | 5,435,064 | 5,480 | 0.0000 | 539.9128 | 7.1455 | 0.0000 |  |
| tmax_1deg_lag1 | 5,368,135 | 72,409 | 2.0150 | 47.7926 | 30.6862 | 31.1803 |  |
| tmin_1deg_lag1 | 5,372,648 | 67,896 | -7.1827 | 32.2487 | 18.9875 | 20.8979 |  |
| tmax_1deg_roll7 | 5,374,782 | 65,762 | 3.8677 | 46.7599 | 30.6768 | 31.1396 |  |
| diurnal_range_1deg | 5,365,245 | 75,299 | -0.1376 | 23.3354 | 11.6897 | 11.6122 |  |
| sin_doy | 5,440,544 | 0 | -1.0000 | 1.0000 | 0.0000 | -0.0043 |  |
| cos_doy | 5,440,544 | 0 | -1.0000 | 1.0000 | 0.0002 | 0.0011 |  |

## 4. Analysis: TEST

### Target Statistics (H1-H7)

| Horizon | Valid | Missing | Zero | NonZero | Mean | Median | p90 | p95 | p99 | Max |
|---|---|---|---|---|---|---|---|---|---|---|
| target_h1 | 7,247,361 | 5,043 | 5,090,199 | 2,157,162 | 3.3021 | 0.0000 | 9.0840 | 19.5847 | 53.2831 | 979.1448 |
| target_h2 | 7,242,397 | 10,007 | 5,085,771 | 2,156,626 | 3.3039 | 0.0000 | 9.0914 | 19.5970 | 53.2948 | 979.1448 |
| target_h3 | 7,237,433 | 14,971 | 5,080,968 | 2,156,465 | 3.3061 | 0.0000 | 9.1008 | 19.6080 | 53.3115 | 979.1448 |
| target_h4 | 7,232,469 | 19,935 | 5,076,504 | 2,155,965 | 3.3081 | 0.0000 | 9.1081 | 19.6184 | 53.3297 | 979.1448 |
| target_h5 | 7,227,505 | 24,899 | 5,072,583 | 2,154,922 | 3.3095 | 0.0000 | 9.1129 | 19.6283 | 53.3480 | 979.1448 |
| target_h6 | 7,222,541 | 29,863 | 5,069,363 | 2,153,178 | 3.3093 | 0.0000 | 9.1098 | 19.6261 | 53.3531 | 979.1448 |
| target_h7 | 7,217,577 | 34,827 | 5,065,770 | 2,151,807 | 3.3105 | 0.0000 | 9.1141 | 19.6349 | 53.3710 | 979.1448 |

### Feature Statistics

| Feature | Valid | Missing | Min | Max | Mean | Median | Flags |
|---|---|---|---|---|---|---|---|
| rf_lag_1 | 7,252,325 | 79 | 0.0000 | 979.1448 | 3.3003 | 0.0000 |  |
| rf_lag_2 | 7,252,325 | 79 | 0.0000 | 979.1448 | 3.3008 | 0.0000 |  |
| rf_roll7_sum | 7,252,404 | 0 | 0.0000 | 3343.2981 | 23.1195 | 1.2717 |  |
| days_since_rain | 7,252,325 | 79 | 0.0000 | 8475.0000 | 21.8964 | 4.0000 |  |
| neighbor_mean_lag1 | 7,245,033 | 7,371 | 0.0000 | 882.0921 | 3.3005 | 0.0000 |  |
| neighbor_max_lag1 | 7,245,033 | 7,371 | 0.0000 | 979.1448 | 6.9979 | 0.0000 |  |
| tmax_1deg_lag1 | 7,164,241 | 88,163 | 2.7267 | 48.0946 | 30.9069 | 31.2824 |  |
| tmin_1deg_lag1 | 7,165,397 | 87,007 | -5.4452 | 32.9456 | 19.2124 | 20.9568 |  |
| tmax_1deg_roll7 | 7,167,666 | 84,738 | 4.9155 | 47.0478 | 30.9000 | 31.2557 |  |
| diurnal_range_1deg | 7,162,294 | 90,110 | 0.3528 | 23.9708 | 11.6928 | 11.6424 |  |
| sin_doy | 7,252,404 | 0 | -1.0000 | 1.0000 | 0.0000 | -0.0043 |  |
| cos_doy | 7,252,404 | 0 | -1.0000 | 1.0000 | -0.0000 | 0.0011 |  |

## 5. Cross-Year Boundary & Leakage Validation

- Selected grid point for temporal continuity tests: `lat=8.25`, `lon=77.0`
- [PASS] Boundary 2000 -> 2001: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2001 -> 2002: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2002 -> 2003: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2003 -> 2004: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2004 -> 2005: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.14755509793758392)
- [PASS] Boundary 2005 -> 2006: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2006 -> 2007: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2007 -> 2008: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2008 -> 2009: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2009 -> 2010: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2010 -> 2011: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (14.040084838867188)
- [PASS] Boundary 2011 -> 2012: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (17.411235809326172)
- [PASS] Boundary 2012 -> 2013: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2013 -> 2014: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2014 -> 2015: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (10.442367553710938)
- [PASS] Boundary 2015 -> 2016: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2016 -> 2017: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2017 -> 2018: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2018 -> 2019: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2019 -> 2020: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2020 -> 2021: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (2.3261425495147705)
- [PASS] Boundary 2021 -> 2022: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2022 -> 2023: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2023 -> 2024: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)
- [PASS] Boundary 2024 -> 2025: `target_h1(Dec 31) == rf_lag_1(Jan 1)` (0.0)

**Result:** ALL CROSS-YEAR BOUNDARIES PASSED FORWARD/BACKWARD LINKAGE.

## 6. Final Readiness

The Phase 6 dataset satisfies all scaling, architecture, and correctness requirements.

**FULL HISTORICAL ML DATASET READY FOR MODEL TRAINING**
