import xarray as xr
import polars as pl
import numpy as np
import os

from src.ml.temporal_features import calculate_temporal_features
from src.ml.spatial_features import calculate_spatial_features
from src.ml.temperature_features import calculate_temperature_features
from src.ml.target_builder import calculate_targets

def build_features_for_years(years: list, ml_config: dict) -> xr.Dataset:
    """
    Constructs the chronological xarray dataset by loading raw datasets and applying feature generators.
    """
    rain_paths = [f"{ml_config['processed_data_dir']}/rainfall/{y}.nc" for y in years]
    tmax_paths = [f"{ml_config['processed_data_dir']}/max_temperature/{y}.nc" for y in years]
    tmin_paths = [f"{ml_config['processed_data_dir']}/min_temperature/{y}.nc" for y in years]
    
    # Load and concatenate chronologically
    rain_da = xr.concat([xr.open_dataset(p)['rainfall'] for p in rain_paths], dim='time')
    tmax_da = xr.concat([xr.open_dataset(p)['tmax'] for p in tmax_paths], dim='time')
    tmin_da = xr.concat([xr.open_dataset(p)['tmin'] for p in tmin_paths], dim='time')
    
    # Calculate Features
    temporal_ds = calculate_temporal_features(rain_da, ml_config['rain_threshold'])
    spatial_ds = calculate_spatial_features(rain_da, ml_config['minimum_valid_neighbors'])
    temperature_ds = calculate_temperature_features(rain_da, tmax_da, tmin_da)
    targets_ds = calculate_targets(rain_da, ml_config['target_horizons'])
    
    # Merge into a single wide dataset
    full_ds = xr.merge([temporal_ds, spatial_ds, temperature_ds, targets_ds])
    
    return full_ds, rain_da

import time
import psutil

def export_to_parquet(full_ds: xr.Dataset, rain_da: xr.DataArray, ml_config: dict):
    """
    Converts xarray dataset to partitioned Parquet files using Polars.
    Retains only land grid cells based on historical validity.
    """
    is_land_da = rain_da.notnull().any(dim='time')
    land_df = is_land_da.to_dataframe(name='is_land').reset_index()
    land_points = land_df[land_df['is_land'] == True][['lat', 'lon']]
    
    manifest_records = []
    years = np.unique(full_ds['time'].dt.year)
    for y in years:
        year_start = time.time()
        print(f"Exporting year {y} to Parquet...")
        
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / (1024 * 1024)
        
        ds_year = full_ds.sel(time=str(y))
        df_pd = ds_year.to_dataframe().reset_index()
        df_pd = df_pd.merge(land_points, on=['lat', 'lon'], how='inner')
        df_pl = pl.from_pandas(df_pd)
        
        mem_after = process.memory_info().rss / (1024 * 1024)
        peak_mem = max(mem_before, mem_after)
        
        if y in ml_config.get('train_years', []):
            split = 'train'
        elif y in ml_config.get('val_years', []):
            split = 'validation'
        else:
            split = 'test'
            
        base_dir = ml_config.get('ml_output_base', ml_config.get('ml_output_dir', 'data/ml/pilot'))
        os.makedirs(f"{base_dir}/{split}", exist_ok=True)
        out_path = f"{base_dir}/{split}/{y}.parquet"
        
        # Validations
        assert not df_pl.is_empty(), f"Year {y} is empty!"
        
        dupes = df_pl.group_by(['time', 'lat', 'lon']).len().filter(pl.col('len') > 1).height
        assert dupes == 0, f"Year {y} has duplicate spatial observations!"
        
        # Write
        df_pl.write_parquet(out_path)
        
        file_size_mb = os.path.getsize(out_path) / (1024 * 1024)
        process_time = time.time() - year_start
        rows = df_pl.height
        
        print(f"  Finished {y}: {rows} rows, {file_size_mb:.2f} MB, {process_time:.2f}s, Mem ~{peak_mem:.2f} MB")
        
        import pandas as pd
        manifest_records.append({
            'year': y,
            'split': split,
            'rows': rows,
            'file_path': out_path,
            'file_size_mb': round(file_size_mb, 2),
            'processing_time_s': round(process_time, 2),
            'peak_memory_mb': round(peak_mem, 2),
            'feature_count': 13,
            'target_count': 7,
            'validation_status': 'PASS',
            'generation_timestamp': pd.Timestamp.utcnow().isoformat()
        })
        
    return manifest_records
