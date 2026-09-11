# CLOUDSENSE — PHASE 8.5H REPORT
## OPERATIONAL IMD 0.25° RAINFALL PROVIDER

## 1. Goal
Replace the rainfall portion of `MockIMDProvider` with the real `OperationalIMDRainfallProvider` to pull the official IMD operational 0.25° rainfall product directly into the pipeline without changing the 0.25° locked rainfall contract.

## 2. Validation Constraints Verified
- Exact URL and HTTP method: `https://www.imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php` via `POST`
- 129 × 135 rainfall grid
- Latitude 6.5–38.5 ascending
- Longitude 66.5–100.0 ascending
- -999.0 → NaN
- 0-byte rainfall response means unpublished
- Unpublished data is not committed
- Secure HTTPS/TLS verification
- Bounded retries: Up to 3 attempts, applied strictly to HTTP 500+ errors and transient network timeouts.

## 3. Implementation Details
- `OperationalIMDRainfallProvider` implemented with explicit payload size validation (69,660 bytes).
- Pipeline default provider injection updated to use the operational providers natively.
- `MockIMDProvider` retained only for deterministic/offline regression tests.
- Retry behavior strictly bounds transient failures and fails immediately on 404 or 0-byte responses.
- Integrates securely into the raw staging directory, relying on the pipeline to move to the state-store post-validation.

## 4. End-to-End Real Data Replay
- REAL IMD 0.25° rainfall
- REAL IMD 1° Tmax
- REAL IMD 1° Tmin
- No `MockIMDProvider` was used in the real E2E replay
- Successfully ingested dates: 2026-08-30 through 2026-09-05
- 2026-09-06 was unpublished
- Rainfall 0-byte on 2026-09-06
- Tmax/Tmin unavailable on 2026-09-06
- 2026-09-06 not committed
- latest_valid_T = 2026-09-05
- Exactly 12 canonical features
- H1-H7 predictions from frozen models

## 5. Regression Testing
46 passed, 0 failed, 204 warnings
(Note: The previous count of 47 tests included a transient scratch test that was subsequently removed).

## 6. Decision
Phase 8.5H CLOSED — GO. CloudSense's operational ingestion path has been locally validated against the official IMD 0.25° rainfall and 1.0° temperature feeds while preserving the frozen feature and model contracts. AWS deployment is a separate next phase and is not claimed as completed by Phase 8.5H.
