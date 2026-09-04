# CloudSense Data Metadata Manifest

This document serves as the source of truth for all metadata regarding the environmental GRD datasets (Rainfall, Max Temp, Min Temp).
It strictly separates definitively verified facts from inferred assumptions.

## Status Definitions
- **Verified**: Proven programmatically via direct file inspection, or confirmed by authoritative IMD documentation.
- **Inferred**: Derived from superficial inspection, web scrapes, or naming conventions, but not yet proven.
- **Unknown**: Needs investigation.

## 1. Rainfall Dataset

| Property | Value | Status | Source/Verification Method |
| :--- | :--- | :--- | :--- |
| **Grid Size** | 135 (Lon) × 129 (Lat) | Verified | Byte size of 2000 file exactly matches 366 days × 135 × 129 × 4 bytes. |
| **Byte Size (Leap)** | 25,495,560 bytes | Verified | `ls -l data/ind2000_rfp25.grd` |
| **Byte Size (Non-Leap)**| 25,425,900 bytes | Verified | `ls -l data/ind2001_rfp25.grd` |
| **Endianness** | Little-Endian (`<f4`) | Verified | Empirical distribution test. `<f4` yields `[0.0, 569.62]`. |
| **Record Markers** | None (Direct Access) | Verified | File size strictly contiguous. First/last 8 bytes show no sequential markers. |
| **Missing Value** | -999.0 | Verified | Outlier detection found precisely 4,557,066 occurrences in the 2000 file. |
| **Lat Bounds** | 6.5N - 38.5N | Verified | IMD HTML source confirms resolution 0.25. (6.5 + 128*0.25 = 38.5). |
| **Lon Bounds** | 66.5E - 100.0E | Verified | IMD HTML source confirms resolution 0.25. (66.5 + 134*0.25 = 100.0). |
| **Units** | mm | Verified | IMD HTML source. |

## 2. Maximum Temperature Dataset

| Property | Value | Status | Source/Verification Method |
| :--- | :--- | :--- | :--- |
| **Grid Size** | 31 (Lon) × 31 (Lat) | Verified | Byte size of 2000 file exactly matches 366 days × 31 × 31 × 4 bytes. |
| **Byte Size (Leap)** | 1,406,904 bytes | Verified | `ls -l data/Maxtemp_MaxT_2000.GRD` |
| **Byte Size (Non-Leap)**| 1,403,060 bytes | Verified | `ls -l data/Maxtemp_MaxT_2001.GRD` |
| **Endianness** | Little-Endian (`<f4`) | Verified | Empirical distribution test. `<f4` yields `[0.62, 45.00]`. |
| **Record Markers** | None (Direct Access) | Verified | File size strictly contiguous. First/last 8 bytes show no sequential markers. |
| **Missing Value** | 99.9 | Verified | Outlier detection found precisely 223,337 occurrences in the 2000 file. |
| **Lat Bounds** | 7.5N - 37.5N | Verified | IMD HTML source confirms resolution 1.0. |
| **Lon Bounds** | 67.5E - 97.5E | Verified | IMD HTML source confirms resolution 1.0. |
| **Units** | Celsius | Verified | IMD HTML source. |

## 3. Minimum Temperature Dataset

| Property | Value | Status | Source/Verification Method |
| :--- | :--- | :--- | :--- |
| **Grid Size** | 31 (Lon) × 31 (Lat) | Verified | Byte size of 2000 file exactly matches 366 days × 31 × 31 × 4 bytes. |
| **Byte Size (Leap)** | 1,406,904 bytes | Verified | `ls -l data/Mintemp_MinT_2000.GRD` |
| **Byte Size (Non-Leap)**| 1,403,060 bytes | Verified | `ls -l data/Mintemp_MinT_2001.GRD` |
| **Endianness** | Little-Endian (`<f4`) | Verified | Empirical distribution test. `<f4` yields `[-9.11, 30.80]`. |
| **Record Markers** | None (Direct Access) | Verified | File size strictly contiguous. First/last 8 bytes show no sequential markers. |
| **Missing Value** | 99.9 | Verified | Outlier detection found precisely 223,337 occurrences. |
| **Lat Bounds** | 7.5N - 37.5N | Verified | IMD HTML source confirms resolution 1.0. |
| **Lon Bounds** | 67.5E - 97.5E | Verified | IMD HTML source confirms resolution 1.0. |
| **Units** | Celsius | Verified | IMD HTML source. |
