# CLOUDSENSE — PHASE 8.5D
## OFFICIAL IMD 1° OPERATIONAL DATA VALIDATION

### 1. Objective
Following the closure of the 0.5° feasibility path, this phase investigates the availability, structure, and reliability of the official IMD real-time 1.0° Tmax and Tmin products. The goal is to determine if CloudSense can operationally retrieve these 1.0° products and preserve the frozen 1.0° ML model contract without modification.

### 2. Locked CloudSense Data Contract
- **Rainfall:** 0.25°
- **Tmax:** 1.0°
- **Tmin:** 1.0°
- **Historical Period:** 2000–2025
- **Temperature Features:** The semantics remain strictly `tmax_1deg_lag1`, `tmin_1deg_lag1`, `tmax_1deg_roll7`, and `diurnal_range_1deg`.

*(Note: The 0.5° data path was investigated and rejected as a project direction due to catastrophic loss of historical training data. The current CloudSense temperature contract is permanently locked at 1.0°.)*

### 3. Official IMD 1° Products
We have identified the official endpoints for the IMD real-time 1.0° temperature products:
- **Daily Maximum Temperature 1.0° (`tmaxone`)**
  - **URL Structure:** `https://www.imdpune.gov.in/cmpg/Realtimedata/maxone/max1_{DDMMYYYY}.grd`
- **Daily Minimum Temperature 1.0° (`tminone`)**
  - **URL Structure:** `https://www.imdpune.gov.in/cmpg/Realtimedata/minone/min1_{DDMMYYYY}.grd`

**Product Metadata:**
- **File Format:** Raw Binary (`.grd`) containing a flattened 32-bit float array.
- **Dimensions:** 31 × 31
- **Spatial Bounds:** Lat: 7.5 to 37.5, Lon: 67.5 to 97.5
- **Missing-Value Convention:** `99.9`

### 4. Actual Retrieval Tests
Retrieval tests were executed on recent dates using simple HTTP GET requests.
- **Downloaded:** `max1_01092026.grd` and `min1_01092026.grd`
- **File Size:** Exactly 3,844 bytes.
- **Math Verification:** 31 * 31 = 961 pixels. 961 * 4 bytes (float32) = 3,844 bytes. This confirms the payload is a raw, uncompressed binary array.

### 5. Product Structure
Inspecting the raw arrays from `01/09/2026`:
- **Shape:** Both resolve cleanly to a 31x31 grid.
- **Missing Values:** Out of 961 total pixels, 578 pixels are set to `99.9` (missing). This perfectly corresponds to the IMD's standard land/sea mask. No pixels used `-999.0`.
- **Temperature Ranges:** 
  - **Tmax:** Min 22.40°C, Max 39.58°C, Mean 30.47°C.
  - **Tmin:** Min 16.47°C, Max 28.64°C, Mean 23.52°C.
- **Conclusion:** The binary data is valid, structured correctly, and physically realistic.

### 6. Historical/Operational Compatibility
Comparing the real-time operational 1.0° product to the CloudSense historical 1.0° contract:
- **Dimensions:** 31 × 31 (Match)
- **Resolution:** 1.0° (Match)
- **Spatial Bounds:** Lat: 7.5–37.5, Lon: 67.5–97.5 (Match)
- **Missing-value Convention:** Both utilize `99.9` as the sentinel for masked regions (Match)

**Conclusion:** The official real-time 1.0° products belong to the identical product family as the historical CloudSense training data. There are no structural differences.

### 7. Temporal Availability
Real-time availability was tested for consecutive days preceding the current operational date:
- `05092026`: AVAILABLE
- `04092026`: AVAILABLE
- `03092026`: AVAILABLE
- `02092026`: AVAILABLE
- `01092026`: AVAILABLE

**Conclusion:** Both Tmax and Tmin products become available reliably on a daily schedule, aligning perfectly with the existing `latest_valid_T` logic (which expects T-1 completion).

### 8. Automation Reliability
- The URLs are fully deterministic and rely purely on the target date string (e.g., `DDMMYYYY`).
- No complex web scraping, session cookies, or CSRF tokens are required.
- Standard `urllib` / `requests` clients successfully fetch the data with response times averaging ~2 seconds. 
- Automation is entirely realistic and highly robust.

### 9. StateStore Compatibility
The existing CloudSense architecture is completely compatible with these files.
- `src/ingestion/validator.py` (`IMDValidator`) natively expects `self.expected_temp_dims = {'lat': 31, 'lon': 31}`.
- Because the structural parameters perfectly match, the existing StateStore, ProductionFeatureBuilder, and 12-feature predictor require **ZERO** modifications.

### 10. Required Implementation Changes
To implement operational ingestion without modifying the downstream pipeline, only the following isolated changes are required:
1. **New Provider Class:** Create an `OperationalIMDProvider` in `src/ingestion/source.py` to construct the deterministic URLs.
2. **Binary Decoder:** Write a utility to fetch the `.grd` binary (3,844 bytes), reshape it to `(31, 31)`, mask `99.9` to `NaN`, and apply the `lat`/`lon` coordinates.
3. **NetCDF Conversion:** Output the decoded array as an `xarray.Dataset` (NetCDF) to fulfill the `IMDValidator` contract.

### 11. Risks
- **Network Timeouts:** While IMD servers were responsive during the audit, they are known to occasionally drop connections. The new provider must include robust `urllib` retry and timeout logic.

### 12. Decision
> [!IMPORTANT]
> **GO**
> The official IMD 1.0° Tmax/Tmin operational products are highly accessible, structurally identical to our historical training data, and perfectly compatible with the existing `IMDValidator` and CloudSense feature engineering pipeline.

### 13. Exact Next Engineering Phase
**Phase 8.5E: Operational Provider Implementation.**
Develop the `OperationalIMDProvider` and the binary `.grd` to NetCDF decoder, integrate it into `src/ingestion/pipeline.py`, and test the end-to-end ingestion pipeline using the frozen 1.0° models.
