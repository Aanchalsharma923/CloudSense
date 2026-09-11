# CLOUDSENSE — PHASE 8.5A.3
## OFFICIAL IMD 1° REAL-TIME TEMPERATURE ACCESS AUDIT

### 1. Objective
Determine whether CloudSense can legitimately, reliably, and reproducibly obtain a native 1.0° IMD Tmax/Tmin product for real-time operational ingestion, matching the exact spatial and statistical contract of the historical training data.

### 2. Sources Investigated
- **IMD Pune Climate Data Portal:** The official host of the historical 1.0° gridded datasets (`imdpune.gov.in`).
- **IMD Mausam Portal & API (`api.imd.gov.in`):** Real-time observation portals.
- **imdlib Documentation & Source:** (`core.py`, `real.py`) to inspect the supported real-time ingestion parameters and endpoints.
- **Web Literature:** For official announcements of real-time 1.0° gridded data availability.

### 3. Official 1° Tmax Findings
- **Product Name:** IMD Gridded Daily Maximum Temperature (1° x 1°)
- **Resolution/Bounds:** 1.0° (Lat 7.5–37.5, Lon 67.5–97.5)
- **Status:** **Historical / Archival.** IMD produces this as a research dataset, updated periodically by appending to a yearly binary file (`Maxtemp_MaxT_{year}.GRD`). It is not exposed as a daily operational API endpoint.

### 4. Official 1° Tmin Findings
- **Product Name:** IMD Gridded Daily Minimum Temperature (1° x 1°)
- **Status:** Same as Tmax. Hosted as historical yearly binary files (`Mintemp_MinT_{year}.GRD`). No real-time daily operational feed exists.

### 5. Actual Retrieval Test
An attempt was made to programmatically query the official IMD Pune endpoint for the 1.0° dataset (`https://imdpune.gov.in/cmpg/Griddata/maxtemp.php`) from the production environment.
- **Result:** **FAILED.** The connection timed out (`ConnectTimeoutError`).
- **Implication:** The server hosting the 1.0° data is unstable, geo-blocked for automated scripts, or severely rate-limited. It cannot be trusted for mission-critical daily retrieval.

### 6. Product Identity Comparison
The historical training files (`Maxtemp_MaxT_{year}.GRD`) are confirmed to be the exact 1.0° historical datasets provided by IMD Pune. The 0.5° operational dataset (which *can* be retrieved via `imdlib.get_real_data()`) is a fundamentally different product derived from a different interpolation of station data, hence the ~3.14°C Mean Absolute Error discovered in Phase 8.5A.2.

### 7. Data-Format Comparison
| Feature | Historical 1° (CloudSense Contract) | Operational Real-Time Feed |
| :--- | :--- | :--- |
| **Grid Size** | 31 x 31 | 61 x 61 |
| **Resolution** | 1.0° | 0.5° |
| **Missing Value** | `99.9` | `99.9` or `-999.0` |
| **Availability** | Yearly `.GRD` file | Daily |

### 8. Temporal Availability
The 1.0° dataset is fundamentally incompatible with the CloudSense `latest_valid_T` operational semantics. It is released as yearly aggregates rather than daily T+1 updates. Waiting for the 1.0° data to become available would stall the forecasting pipeline indefinitely.

### 9. Automation Feasibility
**Zero.**
- No reliable URL/endpoint mechanism for daily 1.0° appends.
- The IMD Pune host server frequently times out.
- The community-standard library (`imdlib`) explicitly only supports 0.5° resolution for its `get_real_data()` operational function.

### 10. 88°C Anomaly Investigation (From Phase 8.5A.2)
The reported ~88.05°C Maximum Absolute Error between the 1.0° and 0.5° datasets is a **Missing-Value Handling Artifact**. 
- The 0.5° real-time dataset uses both `99.9` and `-999.0` as sentinels.
- The 1.0° dataset uses `99.9`.
- When raw values were blindly compared, a valid temperature (e.g., ~11.8°C) was subtracted from a sentinel (`99.9`), resulting in an artificial ~88°C error.
- **Note:** Even when missing values are properly masked, the remaining valid coordinates still exhibit a genuine meteorological discrepancy (Mean Absolute Error ~3.14°C), confirming they are distinct products.

### 11. Security/Access Considerations
Relying on HTTP POST requests to `imdpune.gov.in` for yearly files is highly brittle. The server does not provide modern API authentication or uptime guarantees suitable for an automated production pipeline.

### 12. Decision
> [!CAUTION]
> **NO-GO**
> A native 1° operational source cannot be obtained or reliably automated. The data does not exist as a daily real-time feed, and the historical server is too unstable for production use.

### 13. Evidence
- `imdlib` documentation explicitly restricts `get_real_data()` temperature to 0.5°.
- HTTP requests to the 1.0° endpoint timed out consistently during the audit.
- Meteorological discrepancy (MAE ~3.14°C) proves the 0.5° data cannot be transformed into the 1.0° data.

### 14. Recommended Next Phase
**Retrain CloudSense using 0.5° operational Tmax/Tmin.**
- **Rationale:** Since 0.5° data is the *only* reliably available real-time operational temperature feed, the training pipeline must be aligned with operational reality.
- **Feasibility:** Historical 0.5° data is available and can be backfilled to retrain the ML models.
- **Action:** We must modify the feature builder to ingest 0.5° historical temperature grids, retrain the models, and establish a new 0.5°-based spatial contract before implementing the `OperationalIMDProvider`.

### 15. Explicit Non-Capabilities
- No code was modified.
- No models were retrained.
- No workaround operational providers were created.
- The production ML pipeline remains locked in its 1.0° historical state.
