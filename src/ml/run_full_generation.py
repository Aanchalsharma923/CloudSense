import os
import time
import psutil
import pandas as pd
import xarray as xr
import polars as pl
from pathlib import Path

from src.ml.config import ML_CONFIG
from src.ml.dataset_builder import build_features_for_years, export_to_parquet
from src.ml.leakage_tests import run_leakage_tests

def run_full_generation():
    print("Running full historical dataset generation (2000-2025)...")
    
    # Run Leakage Tests first to ensure safety
    print("Running leakage tests...")
    run_leakage_tests(ML_CONFIG)
    
    # Run the full pipeline in chunks to avoid blowing up memory with the Xarray Concat
    # 26 years of data in Xarray might be a bit large, but the user requested bounded memory.
    # Actually, build_features_for_years concats everything, which might be up to 10GB for 26 years.
    # To be extremely safe with memory, let's process it in chunks of 5 years.
    # Wait, the temporal features (roll7, lag2) cross year boundaries. We can't strictly chunk unless we overlap.
    # But xarray dataset isn't that massive when lazy. However `values` loading is eager.
    # Let's just process it all at once since xarray is relatively memory efficient until we do `to_dataframe()`,
    # which is explicitly chunked by year in `export_to_parquet`.
    
    total_start_time = time.time()
    
    full_ds, rain_da = build_features_for_years(ML_CONFIG['all_years'], ML_CONFIG)
    
    manifest_records = export_to_parquet(full_ds, rain_da, ML_CONFIG)
    
    total_time = time.time() - total_start_time
    print(f"Total processing time: {total_time:.2f}s")
    
    # Write manifest
    import os
    import pandas as pd
    os.makedirs("docs/ml", exist_ok=True)
    manifest_df = pd.DataFrame(manifest_records)
    manifest_df.to_csv("docs/ml/full_dataset_manifest.csv", index=False)
    print("Wrote docs/ml/full_dataset_manifest.csv")
    
if __name__ == "__main__":
    run_full_generation()
