# Phase 3 Ingestion Report: Historical Dataset (2000-2025)

## Overview

The Phase 3 processing pipeline successfully ingested the complete local historical dataset (2000–2025). The pipeline translated raw, little-endian, direct-access binary GRD files into strictly validated, CF-compliant NetCDF files based on the baseline 2000 validation standards.

The dataset contains three meteorological variables:
- **Rainfall** (`ind{year}_rfp25.grd`)
- **Max Temperature** (`Maxtemp_MaxT_{year}.GRD`)
- **Min Temperature** (`Mintemp_MinT_{year}.GRD`)

## Processing Summary

- **Total Expected Years:** 26 (2000-2025)
- **Total Variables per Year:** 3
- **Total Processing Targets:** 78
- **Successfully Processed:** 78 (100% completion)

> [!NOTE]
> The automated pipeline dynamically handles both regular (365 days) and leap (366 days) years by checking the byte size of each source file against predefined variable constraints.

## Structural Consistency Audit

A `consistency_audit.py` script was deployed across all generated `.nc` files to ensure strict alignment with the benchmark (2000) processing logic. 

**Validated criteria included:**
- Variable dimensions matching expectations `(time, lat, lon)`
- Constant latitude/longitude coordinate bounds and resolution
- Adherence to leap-year rules (dimension sizing)
- Explicit missing-value masking (`-999.0` for rainfall, `99.9` for temperatures)
- Coordinate ordering mapped accurately for time, latitude, and longitude
- Consistent units (mm for rainfall, Celsius for temperatures)

**Audit Results:** **PASS**. No structural anomalies were found. All 26 years are structurally identical to the 2000 year baseline.

## Statistical Review

A statistical review was conducted to ensure data integrity across the timeline.

### 1. Rainfall
- **Min:** 0.0 mm (Consistent)
- **Max:** Range from 349.6 mm (2012) up to 979.1 mm (2022)
- **Mean:** ~2.5 to 3.5 mm/day
- **Missing Value Count:** Exactly 4,557,066 on leap years and 4,544,615 on non-leap years.
- **Anomaly Flag:** None.

### 2. Max Temperature
- **Min:** Range from -1.19°C (2008) to 6.72°C (2016)
- **Max:** Range from 44.4°C (2008) up to 48.77°C (2016)
- **Mean:** ~30.4 to 31.5°C
- **Missing Value Count:** Fluctuates slightly between 219k - 223k (Valid missing value bounds based on observed bounds). 
- **Anomaly Flag:** The 2019 MaxT file (`Maxtemp_MaxT_2019.GRD`), originally flagged as a potentially corrupted/0-byte file in previous listings, was successfully discovered and processed. It had a byte size of 1,403,060 bytes, correctly matching 365 days.

### 3. Min Temperature
- **Min:** Range from -11.45°C (2008) to -2.46°C (2025)
- **Max:** Range from 29.53°C (2008) up to 33.2°C (2010)
- **Mean:** ~18.6 to 19.6°C
- **Missing Value Count:** Fluctuates slightly between 219k - 223k.
- **Anomaly Flag:** None.

## Conclusion and Next Steps

The entire historical 26-year timeline has been locally processed into `data/processed/{variable}/{year}.nc`, heavily validated, and catalogued in `manifest.csv`. 

**Next Steps**:
1. Review the data artifacts and metrics provided above.
2. We have not accessed AWS. As per project constraints, the processed netCDF structures are only local. A Phase 4 could include AWS interaction for deployment of this data.
3. Transition to architecture design for the remaining layers of the system: ML, backend, and API layers.
