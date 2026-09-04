import xarray as xr
from typing import List

def calculate_targets(rainfall_da: xr.DataArray, horizons: List[int]) -> xr.Dataset:
    """
    Generates multi-horizon targets by forward-shifting the rainfall tensor.
    target_h1 at row t corresponds to rainfall(t+1).
    """
    ds = xr.Dataset()
    
    for h in horizons:
        # A negative shift in time brings future data (t+h) to the current timestamp (t).
        ds[f'target_h{h}'] = rainfall_da.shift(time=-h)
        
    return ds
