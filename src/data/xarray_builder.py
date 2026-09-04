import numpy as np
import xarray as xr
import pandas as pd
from typing import Dict, Any

def build_xarray_dataset(
    raw_tensor: np.ndarray,
    year: int,
    dataset_name: str,
    verified_metadata: Dict[str, Any]
) -> xr.Dataset:
    """
    Constructs an xarray Dataset from the raw numpy tensor using verified geographic metadata.
    Applies the missing value mask without modifying the raw tensor.
    """
    days, grid_y, grid_x = raw_array_shape = raw_tensor.shape
    
    # Calculate coordinate arrays
    # Longitude varies fastest on disk (X axis). Latitude is Y axis.
    # We verify that lengths match the grid config
    assert grid_x == verified_metadata['grid_x']
    assert grid_y == verified_metadata['grid_y']
    
    lon_min = verified_metadata['lon_min']
    lat_min = verified_metadata['lat_min']
    res = verified_metadata.get('resolution', 1.0)
    
    # Generate monotonic coordinates
    # The source states for both: "first data is at {lat_min}, {lon_min}, second is at {lat_min}, {lon_min+res}"
    # So longitude and latitude strictly increase.
    lons = lon_min + np.arange(grid_x) * res
    lats = lat_min + np.arange(grid_y) * res
    
    # Generate time coordinates
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    expected_days = 366 if is_leap else 365
    assert days == expected_days
    
    times = pd.date_range(start=f"{year}-01-01", periods=days, freq='D')
    
    # Identify the variable name
    var_name_map = {
        'rainfall': 'rainfall',
        'max_temp': 'tmax',
        'min_temp': 'tmin'
    }
    var_name = var_name_map.get(dataset_name, 'value')
    
    # Construct the base DataArray from raw data
    da = xr.DataArray(
        data=raw_tensor,
        dims=['time', 'lat', 'lon'],
        coords={
            'time': times,
            'lat': lats,
            'lon': lons
        },
        name=var_name
    )
    
    # Apply missing-value mask
    missing_val = verified_metadata['missing_value']
    
    # We use xr.where to mask out missing values (replaces with NaN)
    # isclose handles floating point imperfections
    masked_da = xr.where(np.isclose(da, missing_val, rtol=1e-5, atol=1e-5), np.nan, da)
    
    # Create final Dataset
    ds = xr.Dataset({var_name: masked_da})
    
    # Attach dataset-level attributes
    ds.attrs['year'] = year
    ds.attrs['dataset_type'] = dataset_name
    ds.attrs['missing_value_used'] = missing_val
    ds.attrs['original_shape'] = str(raw_array_shape)
    
    return ds
