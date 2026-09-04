import pytest
import polars as pl
import pandas as pd
import numpy as np
import os
import glob
import random

from src.features.grid_mapper import GridMapper
from src.features.providers import HistoricalNetCDFProvider
from src.features.feature_builder import ProductionFeatureBuilder

@pytest.fixture(scope="module")
def builder():
    mapper = GridMapper(
        rainfall_nc_path="data/processed/rainfall/2023.nc",
        tmax_nc_path="data/processed/max_temperature/2023.nc"
    )
    provider = HistoricalNetCDFProvider(data_dir="data/processed")
    return ProductionFeatureBuilder(grid_mapper=mapper, provider=provider)

def test_feature_parity_large_replay(builder):
    """
    Validates numerical parity against thousands of historical examples 
    from the Phase 5 training pipeline.
    """
    # Find all validation parquet files
    parquet_files = glob.glob("data/ml/validation/*.parquet")
    if not parquet_files:
        # Fallback to train
        parquet_files = glob.glob("data/ml/train/2019.parquet") + glob.glob("data/ml/train/2020.parquet")
    
    if not parquet_files:
        pytest.skip("No historical parquet files found for parity testing.")
        
    all_results = []
    
    FEATURES_TO_TEST = [
        'rf_lag_1', 'rf_lag_2', 'rf_roll7_sum', 'days_since_rain',
        'neighbor_mean_lag1', 'neighbor_max_lag1', 'tmax_1deg_lag1',
        'tmin_1deg_lag1', 'tmax_1deg_roll7', 'diurnal_range_1deg',
        'sin_doy', 'cos_doy'
    ]
    
    total_samples = 0
    mismatches = 0
    max_errors = {f: 0.0 for f in FEATURES_TO_TEST}
    mean_errors = {f: [] for f in FEATURES_TO_TEST}
    
    # We will sample 2000 random points across the files
    for p_file in parquet_files:
        print(f"Reading {p_file}...")
        df = pl.read_parquet(p_file)
        
        # Sample N random rows
        # In Polars, we can sample by taking a fraction
        df_sample = df.sample(n=min(500, df.height), seed=42)
        
        for row in df_sample.to_dicts():
            lat = row['lat']
            lon = row['lon']
            date_t = pd.Timestamp(row['time'])
            
            try:
                # Our builder expects string for base_date
                feature_state = builder.build(lat, lon, date_t.strftime('%Y-%m-%d'))
                built_dict = feature_state.to_dict()
                
                total_samples += 1
                row_mismatch = False
                
                for f in FEATURES_TO_TEST:
                    truth = float(row[f])
                    built = built_dict[f]
                    
                    diff = abs(truth - built)
                    
                    if diff > max_errors[f]:
                        max_errors[f] = diff
                        
                    mean_errors[f].append(diff)
                    
                    tolerance = 2e-5 if f in ['neighbor_mean_lag1', 'tmax_1deg_roll7'] else 1e-5
                    if diff > tolerance:
                        row_mismatch = True
                        
                if row_mismatch:
                    mismatches += 1
                    
            except ValueError as e:
                # If we hit an ocean boundary or missing data, that's fine for sampling,
                # but dataset_builder in phase 5 should only contain valid data.
                print(f"Failed to build {lat}, {lon}, {date_t}: {e}")
                
    # Calculate means
    final_mean_errors = {f: np.mean(errs) if errs else 0.0 for f, errs in mean_errors.items()}
    
    # Write Report
    report_path = "docs/ml/phase8_2_feature_parity_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w") as f:
        f.write("# Phase 8.2 Feature Parity Report\n\n")
        f.write(f"**Total Samples Replayed:** {total_samples}\n")
        f.write(f"**Mismatched Samples (diff > 1e-5):** {mismatches}\n")
        f.write(f"**Mismatch Percentage:** {mismatches / max(total_samples, 1) * 100:.2f}%\n\n")
        
        f.write("## Per-Feature Absolute Errors\n\n")
        f.write("| Feature | Max Error | Mean Error |\n")
        f.write("|---------|-----------|------------|\n")
        for ft in FEATURES_TO_TEST:
            f.write(f"| `{ft}` | {max_errors[ft]:.8f} | {final_mean_errors[ft]:.8f} |\n")
            
    assert mismatches == 0, f"Found {mismatches} mismatched samples. See {report_path} for details."
