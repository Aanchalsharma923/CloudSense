import xarray as xr

def calculate_temperature_features(rainfall_da: xr.DataArray, tmax_da: xr.DataArray, tmin_da: xr.DataArray) -> xr.Dataset:
    """
    Maps native 1° temperature data to 0.25° rainfall grid using nearest-neighbor lookup.
    Calculates temperature-based features at time t.
    """
    ds = xr.Dataset()
    
    # Map to rainfall grid (nearest neighbor)
    import numpy as np
    tmax_mapped = tmax_da.interp(lat=rainfall_da.lat, lon=rainfall_da.lon, method='nearest', kwargs={"fill_value": np.nan})
    tmin_mapped = tmin_da.interp(lat=rainfall_da.lat, lon=rainfall_da.lon, method='nearest', kwargs={"fill_value": np.nan})
    
    # Temporal alignment: these values at row t correspond to temperature at time t
    ds['tmax_1deg_lag1'] = tmax_mapped
    ds['tmin_1deg_lag1'] = tmin_mapped
    
    # Rolling 7-day mean (backward-looking from t)
    ds['tmax_1deg_roll7'] = tmax_mapped.rolling(time=7, min_periods=1).mean(skipna=True)
    
    # Diurnal range at t
    ds['diurnal_range_1deg'] = tmax_mapped - tmin_mapped
    
    return ds
