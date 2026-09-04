import xarray as xr
import numpy as np
from src.ingestion.models import ValidationResult

class IMDValidator:
    def __init__(self):
        # We expect the exact grid dimensions from Phase 5
        self.expected_rainfall_dims = {'lat': 129, 'lon': 135}
        self.expected_temp_dims = {'lat': 31, 'lon': 31}
        
    def validate_rainfall(self, path: str) -> ValidationResult:
        try:
            ds = xr.open_dataset(path)
            if 'rainfall' not in ds:
                return ValidationResult(is_valid=False, error_message="Missing 'rainfall' variable")
            
            # Check dimensions
            for dim, expected_size in self.expected_rainfall_dims.items():
                if dim not in ds.dims:
                    return ValidationResult(is_valid=False, error_message=f"Missing dimension {dim}")
                if ds.sizes[dim] != expected_size:
                    return ValidationResult(is_valid=False, error_message=f"Wrong size for {dim}. Expected {expected_size}, got {ds.sizes[dim]}")
                    
            # Check for exactly one time step for a daily download
            if 'time' not in ds.dims or ds.sizes['time'] != 1:
                return ValidationResult(is_valid=False, error_message="Expected exactly 1 time step")
                
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            return ValidationResult(is_valid=False, error_message=f"Corrupted or invalid NetCDF: {str(e)}")

    def validate_temperature(self, path: str, variable: str) -> ValidationResult:
        try:
            ds = xr.open_dataset(path)
            if variable not in ds:
                return ValidationResult(is_valid=False, error_message=f"Missing '{variable}' variable")
            
            # Check dimensions
            for dim, expected_size in self.expected_temp_dims.items():
                if dim not in ds.dims:
                    return ValidationResult(is_valid=False, error_message=f"Missing dimension {dim}")
                if ds.sizes[dim] != expected_size:
                    return ValidationResult(is_valid=False, error_message=f"Wrong size for {dim}. Expected {expected_size}, got {ds.sizes[dim]}")
                    
            if 'time' not in ds.dims or ds.sizes['time'] != 1:
                return ValidationResult(is_valid=False, error_message="Expected exactly 1 time step")
                
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            return ValidationResult(is_valid=False, error_message=f"Corrupted or invalid NetCDF: {str(e)}")
