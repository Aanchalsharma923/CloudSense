import xarray as xr
import numpy as np

def calculate_temporal_features(rainfall_da: xr.DataArray, rain_threshold: float = 0.0) -> xr.Dataset:
    """
    Calculates temporal rainfall features explicitly mapped to t.
    Returns an xr.Dataset with rf_lag_1, rf_lag_2, rf_roll7_sum, and days_since_rain.
    """
    ds = xr.Dataset()
    
    # target_h1 will be rainfall(t+1)
    # rf_lag_1 is rainfall(t), aligning with row index t
    ds['rf_lag_1'] = rainfall_da
    
    # rf_lag_2 is rainfall(t-1)
    ds['rf_lag_2'] = rainfall_da.shift(time=1)
    
    # rf_roll7_sum is sum of rainfall(t-6) through rainfall(t)
    # Using min_periods=1 to retain partial sums if some days are missing, 
    # but we can configure this if strict completeness is required.
    ds['rf_roll7_sum'] = rainfall_da.rolling(time=7, min_periods=1).sum(skipna=True)
    
    # days_since_rain
    # counts consecutive preceding valid observations through t whose rainfall <= threshold
    vals = rainfall_da.values
    is_dry = (vals <= rain_threshold)
    is_valid = ~np.isnan(vals)
    
    dsr = np.zeros_like(vals, dtype=np.float32)
    current_dsr = np.zeros((vals.shape[1], vals.shape[2]), dtype=np.float32)
    
    for t in range(vals.shape[0]):
        # where valid and dry: increment
        current_dsr = np.where(is_valid[t] & is_dry[t], current_dsr + 1, current_dsr)
        # where valid and wet: reset to 0
        current_dsr = np.where(is_valid[t] & (~is_dry[t]), 0, current_dsr)
        
        # output is NaN if observation at t is invalid
        out_t = np.where(is_valid[t], current_dsr, np.nan)
        dsr[t] = out_t
        
    ds['days_since_rain'] = xr.DataArray(dsr, coords=rainfall_da.coords, dims=rainfall_da.dims)
    
    # Seasonal Features
    doy = rainfall_da['time'].dt.dayofyear
    ds['sin_doy'] = np.sin(2 * np.pi * doy / 365.25)
    ds['cos_doy'] = np.cos(2 * np.pi * doy / 365.25)
    
    return ds
