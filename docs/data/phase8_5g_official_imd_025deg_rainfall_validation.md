# Phase 8.5G: Official IMD 0.25° Operational Rainfall Validation

## Objective
Determine whether the official IMD 0.25° daily operational rainfall product can be used directly by CloudSense without changing the 12 feature definitions, model artifacts, model architecture, rainfall semantics, grid mapper architecture, or StateStore architecture.

## 1. Source Location
The official real-time rainfall data is not exposed via a standard open directory listing. Instead, it is served through a PHP script endpoint:
- **URL**: `https://www.imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php`
- **Method**: `POST`
- **Payload**: `{'rain': 'DDMMYYYY'}`
- **Response**: Directly returns the binary `.grd` file content if available, or a 0-byte payload if the data is not yet published for that date.

## 2. Binary Forensic Analysis
A test payload for 2026-09-06 was downloaded and analyzed:
- **Payload Size**: Exactly 69,660 bytes.
- **Data Type**: `float32` (little-endian, 4 bytes per value).
- **Element Count**: 69,660 / 4 = 17,415 elements.
- **Shape**: $129 \times 135 = 17,415$. This exactly matches the expected 129 latitudes and 135 longitudes for a 0.25° grid over India.
- **Missing Value Sentinel**: `-999.0` (standard for IMD rainfall).
- **Value Range**: Min: 0.0 mm, Max: ~120.9 mm (after masking missing values).

## 3. Comparison with Historical Contract
The binary grid was directly compared against the CloudSense historical archive (`data/processed/rainfall/2024.nc`):
- **Historical Dimensions**: `(lat: 129, lon: 135)`
- **Historical Latitudes**: `6.5` to `38.5` (step 0.25)
- **Historical Longitudes**: `66.5` to `100.0` (step 0.25)

The binary `.grd` file natively follows this exact row-major `(lat, lon)` structure. When reshaped to `(129, 135)`, the valid data mask precisely aligns with the Indian landmass (valid rows 7–123, valid cols 6–123). **No transposition or flipping is required** to align the binary payload with the historical CloudSense coordinate system.

## 4. Publication Behavior
- **Success**: Returns HTTP 200 with exactly 69,660 bytes.
- **Missing Data (Future/Unpublished)**: Returns HTTP 200 with 0 bytes. The ingestion pipeline must handle this by checking `len(response.content) == 69660`.

## 5. Compatibility Assessment
- **Feature Definitions**: Unchanged. The spatial resolution remains 0.25°.
- **Model Artifacts/Architecture**: Unchanged. The grid size is identical.
- **Rainfall Semantics**: Unchanged. The data represents standard daily rainfall (mm).
- **Grid Mapper & StateStore**: Unchanged. The resulting NetCDF file matches the historical schema perfectly.

## Final Recommendation: GO
The official IMD 0.25° operational rainfall feed is **100% compatible** with the current frozen data contract.

It natively provides the exact grid (`129 x 135`) expected by the ingestion pipeline and historical `MockIMDProvider`, and can seamlessly replace it. With this validated, the CloudSense live ingestion architecture can be fully operationalized for all three parameters (Rainfall, Tmax, Tmin).
