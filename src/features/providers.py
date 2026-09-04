import xarray as xr
import numpy as np
import pandas as pd
from typing import Tuple, Optional
import os

class HistoricalNetCDFProvider:
    """
    Simulates a historical/real-time data provider by reading directly from 
    the Phase 5 NetCDF processed datasets.
    """
    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = data_dir
        self._cache = {}
        
    def _get_dataset(self, variable: str, year: int) -> xr.Dataset:
        key = (variable, year)
        if key in self._cache:
            return self._cache[key]
            
        path = os.path.join(self.data_dir, variable, f"{year}.nc")
        if not os.path.exists(path):
            raise ValueError(f"Data for {variable} in year {year} is not available at {path}.")
            
        ds = xr.open_dataset(path)
        # Load entirely into memory for fast slicing during the thousands of tests
        ds.load()
        self._cache[key] = ds
        return ds
        
    def get_rainfall_history(self, lat_idx: int, lon_idx: int, date_t: pd.Timestamp, lookback_days: int) -> np.ndarray:
        """
        Gets the rainfall history for a single cell from T-lookback_days to T.
        Returns a 1D numpy array of length lookback_days + 1.
        """
        start_date = date_t - pd.Timedelta(days=lookback_days)
        years = list(range(start_date.year, date_t.year + 1))
        
        datasets = [self._get_dataset("rainfall", y) for y in years]
        combined = xr.concat([ds['rainfall'] for ds in datasets], dim='time')
        
        # Select spatial cell and temporal slice
        slice_da = combined.isel(lat=lat_idx, lon=lon_idx).sel(time=slice(start_date, date_t))
        
        # Validate we got the expected number of days
        expected_days = lookback_days + 1
        if len(slice_da) != expected_days:
            raise ValueError(f"Missing historical rainfall data. Expected {expected_days} days, got {len(slice_da)}.")
            
        return slice_da.values
        
    def get_days_since_rain(self, lat_idx: int, lon_idx: int, date_t: pd.Timestamp, rain_threshold: float = 0.0) -> float:
        """
        Scans backwards to find the number of consecutive days with rainfall <= threshold ending on date_t.
        To avoid scanning forever, we limit to 365 days. If no rain is found, we raise an error indicating 
        missing historical context.
        """
        current_date = date_t
        days_dry = 0.0
        
        while current_date.year >= 2000:
            try:
                ds = self._get_dataset("rainfall", current_date.year)
            except ValueError:
                # Missing a year entirely
                break
                
            # Slice up to current_date for this year
            year_start = pd.Timestamp(f"{current_date.year}-01-01")
            slice_da = ds['rainfall'].isel(lat=lat_idx, lon=lon_idx).sel(time=slice(year_start, current_date))
            vals = slice_da.values
            
            # Scan backwards
            for i in range(len(vals)-1, -1, -1):
                val = vals[i]
                if np.isnan(val):
                    return np.nan
                if val > rain_threshold:
                    return days_dry
                days_dry += 1.0
                
            # Need to look at the previous year
            current_date = year_start - pd.Timedelta(days=1)
            
        raise ValueError(f"Could not determine days_since_rain within available history for {date_t}.")

    def get_spatial_neighbors(self, lat_idx: int, lon_idx: int, date_t: pd.Timestamp) -> np.ndarray:
        """
        Gets the 3x3 neighborhood centered on (lat_idx, lon_idx) for date_t.
        Returns a 2D numpy array (3x3).
        """
        ds = self._get_dataset("rainfall", date_t.year)
        
        # Get bounds
        max_lat = len(ds['lat']) - 1
        max_lon = len(ds['lon']) - 1
        
        # Prepare 3x3 array filled with NaNs
        neighborhood = np.full((3, 3), np.nan)
        
        slice_da = ds['rainfall'].sel(time=date_t)
        
        for i, dlat in enumerate([-1, 0, 1]):
            for j, dlon in enumerate([-1, 0, 1]):
                # If center, skip? No, we need center for max/mean?
                # Actually, Phase 5: "8-connected neighborhood shifts (dlat, dlon)"
                if dlat == 0 and dlon == 0:
                    continue
                
                n_lat = lat_idx + dlat
                n_lon = lon_idx + dlon
                
                if 0 <= n_lat <= max_lat and 0 <= n_lon <= max_lon:
                    val = slice_da.isel(lat=n_lat, lon=n_lon).values
                    neighborhood[i, j] = val
                    
        return neighborhood
        
    def get_temperature_history(self, lat_idx: int, lon_idx: int, date_t: pd.Timestamp, lookback_days: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Gets tmax and tmin history.
        Returns (tmax_vals, tmin_vals) arrays.
        """
        start_date = date_t - pd.Timedelta(days=lookback_days)
        years = list(range(start_date.year, date_t.year + 1))
        
        tmax_ds_list = [self._get_dataset("max_temperature", y) for y in years]
        tmin_ds_list = [self._get_dataset("min_temperature", y) for y in years]
        
        tmax_combined = xr.concat([ds['tmax'] for ds in tmax_ds_list], dim='time')
        tmin_combined = xr.concat([ds['tmin'] for ds in tmin_ds_list], dim='time')
        
        tmax_slice = tmax_combined.isel(lat=lat_idx, lon=lon_idx).sel(time=slice(start_date, date_t))
        tmin_slice = tmin_combined.isel(lat=lat_idx, lon=lon_idx).sel(time=slice(start_date, date_t))
        
        if len(tmax_slice) != lookback_days + 1:
            raise ValueError("Missing historical max_temperature data.")
        if len(tmin_slice) != lookback_days + 1:
            raise ValueError("Missing historical min_temperature data.")
            
        return tmax_slice.values, tmin_slice.values

class StateStoreProvider:
    """
    Simulates a real-time provider by reading from the StateStore.
    """
    def __init__(self, state_store=None):
        from src.ingestion.state_store import StateStore
        self.state_store = state_store or StateStore()
        self._cache = {}
        
    def _get_dataset(self, variable: str, year: int) -> xr.Dataset:
        key = (variable, year)
        if key in self._cache:
            return self._cache[key]
            
        ds = self.state_store.get_dataset(variable, year)
        self._cache[key] = ds
        return ds
        
    def get_rainfall_history(self, lat_idx: int, lon_idx: int, date_t: pd.Timestamp, lookback_days: int) -> np.ndarray:
        start_date = date_t - pd.Timedelta(days=lookback_days)
        years = list(range(start_date.year, date_t.year + 1))
        
        datasets = [self._get_dataset("rainfall", y) for y in years]
        combined = xr.concat([ds['rainfall'] for ds in datasets], dim='time')
        slice_da = combined.isel(lat=lat_idx, lon=lon_idx).sel(time=slice(start_date, date_t))
        
        expected_days = lookback_days + 1
        if len(slice_da) != expected_days:
            raise ValueError(f"Missing historical rainfall data. Expected {expected_days} days, got {len(slice_da)}.")
        return slice_da.values
        
    def get_days_since_rain(self, lat_idx: int, lon_idx: int, date_t: pd.Timestamp, rain_threshold: float = 0.0) -> float:
        current_date = date_t
        days_dry = 0.0
        while current_date.year >= 2000:
            try:
                ds = self._get_dataset("rainfall", current_date.year)
            except ValueError:
                break
                
            year_start = pd.Timestamp(f"{current_date.year}-01-01")
            slice_da = ds['rainfall'].isel(lat=lat_idx, lon=lon_idx).sel(time=slice(year_start, current_date))
            vals = slice_da.values
            for i in range(len(vals)-1, -1, -1):
                val = vals[i]
                if np.isnan(val):
                    return np.nan
                if val > rain_threshold:
                    return days_dry
                days_dry += 1.0
            current_date = year_start - pd.Timedelta(days=1)
        raise ValueError(f"Could not determine days_since_rain within available history for {date_t}.")

    def get_spatial_neighbors(self, lat_idx: int, lon_idx: int, date_t: pd.Timestamp) -> np.ndarray:
        ds = self._get_dataset("rainfall", date_t.year)
        max_lat = len(ds['lat']) - 1
        max_lon = len(ds['lon']) - 1
        neighborhood = np.full((3, 3), np.nan)
        slice_da = ds['rainfall'].sel(time=date_t)
        
        for i, dlat in enumerate([-1, 0, 1]):
            for j, dlon in enumerate([-1, 0, 1]):
                if dlat == 0 and dlon == 0:
                    continue
                n_lat = lat_idx + dlat
                n_lon = lon_idx + dlon
                if 0 <= n_lat <= max_lat and 0 <= n_lon <= max_lon:
                    val = slice_da.isel(lat=n_lat, lon=n_lon).values
                    neighborhood[i, j] = val
        return neighborhood
        
    def get_temperature_history(self, lat_idx: int, lon_idx: int, date_t: pd.Timestamp, lookback_days: int) -> Tuple[np.ndarray, np.ndarray]:
        start_date = date_t - pd.Timedelta(days=lookback_days)
        years = list(range(start_date.year, date_t.year + 1))
        
        tmax_ds_list = [self._get_dataset("tmax", y) for y in years]
        tmin_ds_list = [self._get_dataset("tmin", y) for y in years]
        
        tmax_combined = xr.concat([ds['tmax'] for ds in tmax_ds_list], dim='time')
        tmin_combined = xr.concat([ds['tmin'] for ds in tmin_ds_list], dim='time')
        
        tmax_slice = tmax_combined.isel(lat=lat_idx, lon=lon_idx).sel(time=slice(start_date, date_t))
        tmin_slice = tmin_combined.isel(lat=lat_idx, lon=lon_idx).sel(time=slice(start_date, date_t))
        
        if len(tmax_slice) != lookback_days + 1:
            raise ValueError("Missing historical max_temperature data.")
        if len(tmin_slice) != lookback_days + 1:
            raise ValueError("Missing historical min_temperature data.")
        return tmax_slice.values, tmin_slice.values
