import os
import argparse
import csv
from datetime import datetime
from typing import Dict, Any, Tuple
from pathlib import Path
import xarray as xr
import numpy as np
from src.data.raw_decoder import decode_raw_grd, load_dataset_config
from src.data.xarray_builder import build_xarray_dataset

MANIFEST_PATH = "docs/data/manifest.csv"

def init_manifest():
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    if not os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "variable", "year", "input_filename", "input_exists", "input_size",
                "expected_size", "days", "grid_dimensions", "valid_count",
                "missing_count", "min", "max", "mean", "validation_status",
                "processing_status", "output_path", "error_message", "processing_timestamp"
            ])

def append_to_manifest(record: Dict[str, Any]):
    # Define order explicitly
    fields = [
        "variable", "year", "input_filename", "input_exists", "input_size",
        "expected_size", "days", "grid_dimensions", "valid_count",
        "missing_count", "min", "max", "mean", "validation_status",
        "processing_status", "output_path", "error_message", "processing_timestamp"
    ]
    with open(MANIFEST_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([record.get(f, "") for f in fields])

def get_file_path(dataset_type: str, year: int) -> str:
    """Gets the raw file path for a given dataset and year."""
    if dataset_type == 'rainfall':
        return f"data/ind{year}_rfp25.grd"
    elif dataset_type == 'max_temp':
        return f"data/Maxtemp_MaxT_{year}.GRD"
    elif dataset_type == 'min_temp':
        return f"data/Mintemp_MinT_{year}.GRD"
    raise ValueError(f"Unknown dataset_type: {dataset_type}")

def validate_file(filepath: str, year: int, dataset_type: str, config: Dict[str, Any]) -> Tuple[bool, str, int, int]:
    """Runs strict validation on the raw file. Returns (is_valid, error_msg, file_size, expected_size)"""
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    expected_size = config['byte_size_leap'] if is_leap else config['byte_size_non_leap']
    
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}", 0, expected_size
        
    file_size = os.path.getsize(filepath)
    if file_size == 0:
        return False, "File is 0 bytes", file_size, expected_size
        
    if file_size != expected_size:
        return False, f"Size mismatch. Expected {expected_size}, got {file_size}", file_size, expected_size
        
    return True, "", file_size, expected_size

def process_year(year: int, overwrite: bool = False):
    datasets = ['rainfall', 'max_temp', 'min_temp']
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    expected_days = 366 if is_leap else 365
    
    for ds_name in datasets:
        print(f"\n--- Processing {ds_name} for year {year} ---")
        
        dir_name = ds_name
        if ds_name == 'max_temp':
            dir_name = 'max_temperature'
        elif ds_name == 'min_temp':
            dir_name = 'min_temperature'
            
        out_dir = Path(f"data/processed/{dir_name}")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{year}.nc"
        
        filepath = get_file_path(ds_name, year)
        config = load_dataset_config(ds_name)['verified']
        
        # Manifest record base
        record = {
            "variable": ds_name,
            "year": year,
            "input_filename": os.path.basename(filepath),
            "input_exists": os.path.exists(filepath),
            "days": expected_days,
            "grid_dimensions": f"{config['grid_y']}x{config['grid_x']}",
            "processing_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if out_path.exists() and not overwrite:
            print(f"SKIP: Output {out_path} already exists.")
            # Still validate to populate manifest correctly for skipped runs
            is_valid, err_msg, file_size, expected_size = validate_file(filepath, year, ds_name, config)
            record.update({
                "input_size": file_size,
                "expected_size": expected_size,
                "validation_status": "PASS" if is_valid else "FAIL",
                "processing_status": "SKIPPED",
                "output_path": str(out_path),
                "error_message": "Skipped because output already exists"
            })
            
            if is_valid:
                # Load existing NetCDF to get stats for manifest
                try:
                    ds = xr.open_dataset(out_path)
                    var_key = list(ds.data_vars.keys())[0]
                    da = ds[var_key]
                    record.update({
                        "valid_count": int(da.count()),
                        "missing_count": int(da.isnull().sum()),
                        "min": float(da.min()),
                        "max": float(da.max()),
                        "mean": float(da.mean())
                    })
                    ds.close()
                except Exception as e:
                    record["error_message"] = f"Skipped but could not read stats: {e}"
            append_to_manifest(record)
            continue
            
        # 1. Validation
        is_valid, err_msg, file_size, expected_size = validate_file(filepath, year, ds_name, config)
        
        record.update({
            "input_size": file_size,
            "expected_size": expected_size,
            "validation_status": "PASS" if is_valid else "FAIL",
        })
        
        if not is_valid:
            print(f"Validation FAILED for {ds_name} {year}: {err_msg}")
            record.update({
                "processing_status": "FAILED",
                "error_message": err_msg
            })
            append_to_manifest(record)
            continue
            
        print(f"Validation PASSED for {ds_name} {year}.")
        
        # 2. Decoding
        try:
            raw_tensor = decode_raw_grd(filepath, year, ds_name)
        except Exception as e:
            print(f"FAIL: Error during raw decoding: {e}")
            record.update({
                "processing_status": "FAILED",
                "error_message": f"Decoding error: {e}"
            })
            append_to_manifest(record)
            continue
            
        # 3. Xarray Building
        try:
            ds = build_xarray_dataset(raw_tensor, year, ds_name, config)
        except Exception as e:
            print(f"FAIL: Error during xarray construction: {e}")
            record.update({
                "processing_status": "FAILED",
                "error_message": f"Xarray error: {e}"
            })
            append_to_manifest(record)
            continue
            
        # Extract stats
        var_key = list(ds.data_vars.keys())[0]
        da = ds[var_key]
        
        record.update({
            "valid_count": int(da.count()),
            "missing_count": int(da.isnull().sum()),
            "min": float(da.min()),
            "max": float(da.max()),
            "mean": float(da.mean())
        })
            
        # 4. Save Output
        try:
            ds.to_netcdf(out_path)
            print(f"SUCCESS: Saved {out_path}")
            record.update({
                "processing_status": "SUCCESS",
                "output_path": str(out_path)
            })
        except Exception as e:
            print(f"FAIL: Error saving NetCDF: {e}")
            record.update({
                "processing_status": "FAILED",
                "error_message": f"Save error: {e}"
            })
            
        append_to_manifest(record)

def run_all_years(start_year: int, end_year: int, overwrite: bool):
    init_manifest()
    for yr in range(start_year, end_year + 1):
        process_year(yr, overwrite)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run CloudSense Phase 3 Pipeline")
    parser.add_argument('--year', type=int, help="Year to process")
    parser.add_argument('--all', action='store_true', help="Process all years 2000-2025")
    parser.add_argument('--overwrite', action='store_true', help="Overwrite existing output files")
    args = parser.parse_args()
    
    if args.all:
        run_all_years(2000, 2025, args.overwrite)
    elif args.year:
        init_manifest()
        process_year(args.year, args.overwrite)
    else:
        print("Please specify --year or --all")
