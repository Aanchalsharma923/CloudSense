import numpy as np
import xarray as xr
from typing import Tuple

class GridMapper:
    """
    Maps arbitrary lat/lon coordinates to the nearest valid grid cell in the
    reference NetCDF datasets used in training (Phase 5).
    """
    def __init__(self, rainfall_nc_path: str, tmax_nc_path: str):
        # Load Rainfall Grid (0.25 deg)
        with xr.open_dataset(rainfall_nc_path) as ds_rain:
            self.rain_lats = ds_rain['lat'].values
            self.rain_lons = ds_rain['lon'].values
            # Determine valid land cells by checking if there's any non-null observation across time
            # For efficiency and consistency, we can just check the first time slice if it's mostly static,
            # but to be robust we check any time. Since this is initialized once, it's fine.
            # However, doing `any(dim='time')` on a large NetCDF can be slow. 
            # We'll just read one slice, assume land mask is static.
            first_slice = ds_rain['rainfall'].isel(time=0).values
            self.rain_mask = ~np.isnan(first_slice)

        # Load Temperature Grid (1.0 deg)
        with xr.open_dataset(tmax_nc_path) as ds_temp:
            self.temp_lats = ds_temp['lat'].values
            self.temp_lons = ds_temp['lon'].values
            
    def map_to_rainfall_grid(self, lat: float, lon: float) -> Tuple[float, float, int, int]:
        """
        Maps (lat, lon) to the nearest rainfall grid cell.
        Returns: (snapped_lat, snapped_lon, lat_idx, lon_idx)
        Raises ValueError if out of bounds or ocean.
        """
        if lat < self.rain_lats.min() or lat > self.rain_lats.max():
            raise ValueError(f"Latitude {lat} is outside the supported rainfall grid.")
        if lon < self.rain_lons.min() or lon > self.rain_lons.max():
            raise ValueError(f"Longitude {lon} is outside the supported rainfall grid.")

        # Nearest selection
        lat_idx = (np.abs(self.rain_lats - lat)).argmin()
        lon_idx = (np.abs(self.rain_lons - lon)).argmin()
        
        snapped_lat = float(self.rain_lats[lat_idx])
        snapped_lon = float(self.rain_lons[lon_idx])
        
        # Check land mask
        if not self.rain_mask[lat_idx, lon_idx]:
            raise ValueError(f"Coordinate ({lat}, {lon}) mapped to an invalid/ocean cell at ({snapped_lat}, {snapped_lon}).")
            
        return snapped_lat, snapped_lon, lat_idx, lon_idx

    def map_to_temperature_grid(self, lat: float, lon: float) -> Tuple[float, float, int, int]:
        """
        Maps (lat, lon) to the nearest temperature grid cell.
        Returns: (snapped_lat, snapped_lon, lat_idx, lon_idx)
        """
        if lat < self.temp_lats.min() or lat > self.temp_lats.max():
            raise ValueError(f"Latitude {lat} is outside the supported temperature grid.")
        if lon < self.temp_lons.min() or lon > self.temp_lons.max():
            raise ValueError(f"Longitude {lon} is outside the supported temperature grid.")

        lat_idx = (np.abs(self.temp_lats - lat)).argmin()
        lon_idx = (np.abs(self.temp_lons - lon)).argmin()
        
        snapped_lat = float(self.temp_lats[lat_idx])
        snapped_lon = float(self.temp_lons[lon_idx])
        
        return snapped_lat, snapped_lon, lat_idx, lon_idx
