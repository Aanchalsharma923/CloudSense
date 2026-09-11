# CLOUDSENSE — PHASE 8.5A.1
## LIVE IMD ACCESS VALIDATION / PROOF-OF-CONCEPT

---

### A. Actual Source Tested
The Python library `imdlib` (version 0.1.21) was used to fetch both historical (`get_data`) and real-time operational (`get_real_data`) datasets directly from IMD Pune's official endpoints. 
- Real-time Rain URL: `https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php`
- Real-time MaxTemp URL: `https://imdpune.gov.in/cmpg/Realtimedata/max/max.php`
- Real-time MinTemp URL: `https://imdpune.gov.in/cmpg/Realtimedata/min/min.php`

### B. Actual Download Result
A temporary Python script successfully connected to the IMD servers and downloaded operational data for a recent test date range (May 1, 2024 - May 2, 2024).

### C. Actual Rainfall File Inspection
- **Format**: Decoded to `xarray.Dataset` (originating from `.grd` binary)
- **Variable**: `rain`
- **Dimensions**: `time: 2, lat: 129, lon: 135`
- **Resolution**: 0.25° x 0.25°
- **Fill Value**: `-999.00`
- **Valid Range**: `[-999.00, 140.92]` (Valid precipitation values exist)

### D. Actual Tmax File Inspection
- **Format**: Decoded to `xarray.Dataset` (originating from `.grd` binary)
- **Variable**: `tmax`
- **Dimensions**: `time: 2, lat: 61, lon: 61`
- **Resolution**: 0.50° x 0.50°
- **Fill Value**: `-999.00` / `99.90`
- **Valid Range**: `[11.84, 99.90]`

### E. Actual Tmin File Inspection
- **Format**: Decoded to `xarray.Dataset` (originating from `.grd` binary)
- **Variable**: `tmin`
- **Dimensions**: `time: 2, lat: 61, lon: 61`
- **Resolution**: 0.50° x 0.50°
- **Fill Value**: `-999.00` / `99.90`
- **Valid Range**: `[0.43, 99.90]`

### F. imdlib Result
`imdlib` clearly distinguishes between `get_data()` (historical year-wise data) and `get_real_data()` (daily operational data). 
- `get_real_data()` successfully fetches real-time operational data.
- However, `get_real_data()` for temperature *only* points to the 0.5° resolution URLs.

### G. Direct IMD Result
Direct requests to the IMD historical endpoints (`https://imdpune.gov.in/cmpg/Griddata/maxtemp.php`) for the current incomplete year (e.g., 2026) return empty (0 byte) files. The 1.0° historical datasets are compiled and published at the end of the year. The only daily-updating real-time temperature grid published on the IMD real-time portal is at 0.5° resolution.

### H. Resolution Comparison
| Variable | CloudSense Required Contract | Actual IMD Real-Time Product | Status |
|---|---|---|---|
| Rain | 0.25° / 129 x 135 | 0.25° / 129 x 135 | **MATCH** |
| Tmax | 1.0° / 31 x 31 | 0.5° / 61 x 61 | **MISMATCH** |
| Tmin | 1.0° / 31 x 31 | 0.5° / 61 x 61 | **MISMATCH** |

### I. Temporal Semantics Comparison
- The time coordinates correctly parse to 24-hour daily periods matching historical expectations.
- Rainfall data maps to standard 08:30 IST accumulation boundaries.

### J. Missing-Value Comparison
The data utilizes `99.9` or `-999.0` as fill values for masked pixels (e.g., outside the Indian landmass), which matches the expectations that require proper `np.nan` casting downstream.

### K. Current Availability
Real-time data is actively updating and accessible for recent dates via the `get_real_data` API.

### L. Publication Delay
While explicit timestamps of publication versus observation were not scraped, testing shows that requesting data for very recent dates yields files, aligning with IMD's standard 1-2 day operational delay for QC processing.

### M. Authentication Requirements
None. The data is available via public HTTP endpoints.

### N. Problems Encountered
**Critical Blocker:** The 1.0° gridded temperature data required by the CloudSense models (`31x31` array) is strictly a historical product compiled after the year concludes. The operational, daily-updating real-time temperature grid is provided exclusively at a 0.5° resolution (`61x61` array).

### O. Exact Recommended Access Mechanism
N/A due to NO-GO state. (If the contract were amended, `imdlib.get_real_data()` would be used).

### P. Whether the current ingestion interface can be reused
The current `MockIMDProvider` interface (`download_tmax(date, path)`) is cleanly reusable, provided the underlying resolution mismatch is solved.

### Q. Whether validator changes are required
Yes, the `IMDValidator` currently asserts the historical array shape `(31, 31)`. If 0.5° data were used, the validation logic would fail immediately on the `(61, 61)` shape.

### R. Final GO / NO-GO

# FINAL DECISION: NO-GO

The live access investigation has identified a fatal compatibility blocker.
The CloudSense ML Inference Engine is strictly hardcoded to expect a 1.0° temperature grid (31x31 array). 
The official IMD real-time operational feeds for Tmax and Tmin only supply a 0.5° grid (61x61 array).
Because the 1.0° product is a historical, year-end aggregate and does not exist in the daily operational feed, the system cannot function live without either:
1. Modifying the CloudSense Ingestion Pipeline to safely downsample the 0.5° grid to exactly match the historical 1.0° distribution interpolation.
2. Retraining the ML models natively on 0.5° temperature data.

Per the strict constraints to avoid modifying the ML contract or faking a workaround, we must halt operationalization.
