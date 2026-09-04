import xarray as xr
import pandas as pd
import numpy as np

def calculate_climatology(rainfall_da: xr.DataArray, train_start: str, train_end: str) -> xr.DataArray:
    """
    Calculates Pixel x Day-Of-Year climatology using strictly the training period.
    """
    train_da = rainfall_da.sel(time=slice(train_start, train_end))
    climatology = train_da.groupby('time.dayofyear').mean(dim='time', skipna=True)
    return climatology

def calculate_persistence(rainfall_da: xr.DataArray, horizons: list) -> xr.Dataset:
    """
    Calculates the persistence baseline for each horizon.
    For each horizon h, the prediction for time t+h is the observation at time t.
    """
    ds = xr.Dataset()
    for h in horizons:
        ds[f'baseline_persistence_h{h}'] = rainfall_da
    return ds
