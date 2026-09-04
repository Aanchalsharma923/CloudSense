import xarray as xr
import polars as pl
import numpy as np
import pandas as pd
import os
import psutil
from datetime import datetime

from src.ml.config import ML_CONFIG
from src.ml.temporal_features import calculate_temporal_features
from src.ml.spatial_features import calculate_spatial_features

def audit_target_alignment(ml_config):
    print("Running Audit 1: Target Alignment")
    # Load 2000 parquet
    df = pl.read_parquet(f"{ml_config['ml_output_dir']}/2000.parquet")
    
    # Load 2000 rainfall nc
    rain_da_2000 = xr.open_dataset(f"{ml_config['processed_data_dir']}/rainfall/2000.nc")['rainfall']
    
    # Pick a random sample point: 2000-01-15, lat=10.25, lon=70.25 (ensure it's land)
    sample_rows = df.filter((pl.col('time') == datetime(2000, 1, 15)) & pl.col('target_h1').is_not_null())
    if sample_rows.height == 0:
        sample_rows = df.filter(pl.col('time') == datetime(2000, 1, 15)).head(1)
        
    row = sample_rows.row(0, named=True)
    lat, lon = row['lat'], row['lon']
    
    # Check targets manually against nc
    failures = 0
    for h in range(1, 8):
        future_date = pd.Timestamp(row['time']) + pd.Timedelta(days=h)
        if future_date.year == 2000:
            expected_val = rain_da_2000.sel(time=future_date, lat=lat, lon=lon).values.item()
            actual_val = row[f'target_h{h}']
            if not np.isclose(np.nan_to_num(expected_val), np.nan_to_num(actual_val)):
                print(f"ALIGNMENT FAILURE H{h}: expected {expected_val}, got {actual_val}")
                failures += 1
    
    print(f"Target alignment failures: {failures}")
    return failures == 0

def audit_leakage(ml_config):
    print("Running Audit 2: Feature Leakage")
    # We will do mutation test on a synthetic slice
    times = pd.date_range("2000-01-01", "2000-01-31", freq='D')
    lats = np.arange(10.0, 12.0, 0.25)
    lons = np.arange(70.0, 72.0, 0.25)
    
    data = np.arange(len(times) * len(lats) * len(lons)).reshape(len(times), len(lats), len(lons)).astype(np.float32)
    rain_da = xr.DataArray(data, coords=[times, lats, lons], dims=['time', 'lat', 'lon'])
    
    t_idx = 15 # "t" is Jan 16, 2000
    t_val = times[t_idx]
    
    features_base = calculate_temporal_features(rain_da, ml_config['rain_threshold'])
    
    # Mutations
    for mutation_name, slice_mut in [
        ("t+1", [t_idx+1]),
        ("t+3", [t_idx+3]),
        ("t+7", [t_idx+7]),
        ("all_t_gt", slice(t_idx+1, None))
    ]:
        mutated_da = rain_da.copy()
        mutated_da[slice_mut, :, :] = 9999.0
        
        features_mut = calculate_temporal_features(mutated_da, ml_config['rain_threshold'])
        
        # compare at t
        for var in features_base.data_vars:
            if not np.array_equal(
                np.nan_to_num(features_base[var].sel(time=t_val).values),
                np.nan_to_num(features_mut[var].sel(time=t_val).values)
            ):
                print(f"LEAKAGE DETECTED on {var} with mutation {mutation_name}")
                return False
    print("Leakage audit passed.")
    return True

def audit_temperature_bounds(ml_config):
    print("Running Audit 3: Temperature Extrapolation")
    rain_da = xr.open_dataset(f"{ml_config['processed_data_dir']}/rainfall/2000.nc")['rainfall']
    tmax_da = xr.open_dataset(f"{ml_config['processed_data_dir']}/max_temperature/2000.nc")['tmax']
    
    rain_lats = rain_da.lat.values
    rain_lons = rain_da.lon.values
    
    tmax_lats = tmax_da.lat.values
    tmax_lons = tmax_da.lon.values
    
    # Check bounds
    outside_lat = np.sum((rain_lats < tmax_lats.min()) | (rain_lats > tmax_lats.max()))
    outside_lon = np.sum((rain_lons < tmax_lons.min()) | (rain_lons > tmax_lons.max()))
    
    print(f"Rainfall latitudes outside temperature domain: {outside_lat}")
    print(f"Rainfall longitudes outside temperature domain: {outside_lon}")
    
    # Because of `kwargs={"fill_value": "extrapolate"}`, we know it extrapolates.
    return outside_lat, outside_lon

def run_all_audits():
    df = pl.concat([
        pl.read_parquet(f"{ML_CONFIG['ml_output_dir']}/{y}.parquet")
        for y in ML_CONFIG['pilot_years']
    ])
    
    print("--- Audit 8: End of Pilot Targets ---")
    dec_2002 = df.filter(pl.col('time') >= datetime(2002, 12, 25))
    h7_missing_dec_2002 = dec_2002.filter(pl.col('target_h7').is_null()).height
    print(f"H7 missing in late Dec 2002: {h7_missing_dec_2002}")
    
    print("--- Audit 10: Parquet Validation ---")
    print(f"Total Rows: {df.height}")
    print(f"Total Columns: {len(df.columns)}")
    print("Data Types:")
    for col, dtype in zip(df.columns, df.dtypes):
        print(f"  {col}: {dtype}")
        
    print("--- Audit 12: Duplicates ---")
    dupes = df.group_by(['time', 'lat', 'lon']).len().filter(pl.col('len') > 1).height
    print(f"Duplicate spatial observations: {dupes}")
    
    print("--- Audit 13/14: Distributions ---")
    stats = df.describe()
    print("Computing stats... saved to stats_dump.csv")
    stats.write_csv("docs/ml/stats_dump.csv")
        
    audit_target_alignment(ML_CONFIG)
    audit_leakage(ML_CONFIG)
    audit_temperature_bounds(ML_CONFIG)

if __name__ == "__main__":
    run_all_audits()
