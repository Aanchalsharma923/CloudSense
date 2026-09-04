import xarray as xr
import numpy as np

def calculate_spatial_features(rainfall_da: xr.DataArray, min_valid: int = 3) -> xr.Dataset:
    """
    Calculates spatial neighbor features based on the 8 immediate neighbors.
    Requires at least `min_valid` valid neighbors, otherwise returns NaN.
    """
    ds = xr.Dataset()
    
    # 8-connected neighborhood shifts (dlat, dlon)
    shifts = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]
    
    neighbors = []
    for dlat, dlon in shifts:
        # Shift along the spatial dimensions
        neighbors.append(rainfall_da.shift(lat=dlat, lon=dlon))
        
    # Concatenate to compute statistics along the new 'neighbor' dimension
    neighbors_da = xr.concat(neighbors, dim='neighbor')
    
    # Count valid neighbors
    valid_count = neighbors_da.notnull().sum(dim='neighbor')
    
    # Calculate mean and max (ignoring NaNs)
    neighbor_mean = neighbors_da.mean(dim='neighbor', skipna=True)
    neighbor_max = neighbors_da.max(dim='neighbor', skipna=True)
    
    # Apply the minimum valid neighbors threshold
    # xr.where(condition, x, y) keeps x where condition is true, otherwise y
    valid_mask = valid_count >= min_valid
    
    ds['neighbor_mean_lag1'] = xr.where(valid_mask, neighbor_mean, np.nan)
    ds['neighbor_max_lag1'] = xr.where(valid_mask, neighbor_max, np.nan)
    ds['neighbor_valid_count'] = valid_count
    
    return ds
