import xarray as xr
import pandas as pd
from pathlib import Path
import os
import argparse
from typing import Dict, Any

def audit_all_years(base_dir: str):
    datasets = ['rainfall', 'max_temperature', 'min_temperature']
    
    anomalies = []
    
    print("\n==========================================")
    print("STARTING FULL CONSISTENCY AUDIT")
    print("==========================================")
    
    for ds_name in datasets:
        ds_dir = Path(base_dir) / ds_name
        if not ds_dir.exists():
            continue
            
        print(f"\n--- Auditing {ds_name} ---")
        
        # Load the year 2000 reference
        ref_path = ds_dir / "2000.nc"
        if not ref_path.exists():
            print(f"ERROR: Reference file {ref_path} not found.")
            continue
            
        ref_ds = xr.open_dataset(ref_path)
        var_key = list(ref_ds.data_vars.keys())[0]
        
        ref_lat = ref_ds.lat.values
        ref_lon = ref_ds.lon.values
        ref_units = ref_ds.attrs.get('units', 'Celsius' if 'temperature' in ds_name else 'mm')
        
        for file_path in sorted(ds_dir.glob("*.nc")):
            year_str = file_path.stem
            try:
                year = int(year_str)
            except ValueError:
                continue
                
            is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
            expected_days = 366 if is_leap else 365
            
            try:
                ds = xr.open_dataset(file_path)
            except Exception as e:
                anomalies.append(f"{ds_name} {year}: Failed to open NetCDF: {e}")
                continue
                
            # Check dimensions and coordinates
            if len(ds.time) != expected_days:
                anomalies.append(f"{ds_name} {year}: Time dimension mismatch. Expected {expected_days}, got {len(ds.time)}")
                
            if not (ds.lat.values == ref_lat).all():
                anomalies.append(f"{ds_name} {year}: Latitude coordinates changed.")
                
            if not (ds.lon.values == ref_lon).all():
                anomalies.append(f"{ds_name} {year}: Longitude coordinates changed.")
                
            # Verify units
            current_units = ds.attrs.get('units', 'Celsius' if 'temperature' in ds_name else 'mm')
            if current_units != ref_units:
                anomalies.append(f"{ds_name} {year}: Units changed from {ref_units} to {current_units}")
                
            # Check coordinate ordering implicitly by dimensions order
            # The dimension names should be ('time', 'lat', 'lon')
            dims = ds[var_key].dims
            if dims != ('time', 'lat', 'lon'):
                anomalies.append(f"{ds_name} {year}: Coordinate ordering changed. Expected ('time', 'lat', 'lon'), got {dims}")

            # Check time coordinate range
            first_time = pd.Timestamp(ds.time.values[0])
            last_time = pd.Timestamp(ds.time.values[-1])
            if first_time.year != year or first_time.month != 1 or first_time.day != 1:
                anomalies.append(f"{ds_name} {year}: First timestamp is {first_time}, expected {year}-01-01")
            
            if last_time.year != year or last_time.month != 12 or last_time.day != 31:
                anomalies.append(f"{ds_name} {year}: Last timestamp is {last_time}, expected {year}-12-31")
                
            ds.close()
            
        ref_ds.close()
        
    print("\n==========================================")
    print("AUDIT COMPLETE")
    print("==========================================")
    if anomalies:
        print("\nSTRUCTURAL ANOMALIES FOUND:")
        for anomaly in anomalies:
            print(f"- {anomaly}")
    else:
        print("\nNo structural anomalies found. Datasets are structurally consistent with year 2000.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', type=str, default='data/processed', help='Base processed directory')
    args = parser.parse_args()
    audit_all_years(args.dir)
