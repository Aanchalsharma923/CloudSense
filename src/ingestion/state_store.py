import os
import xarray as xr
import pandas as pd
from typing import Optional

class StateStore:
    def __init__(self, state_dir: str = "data/state", processed_dir: str = "data/processed"):
        self.state_dir = state_dir
        self.processed_dir = processed_dir
        
    def _get_yearly_path(self, variable: str, year: int) -> str:
        return os.path.join(self.state_dir, variable, f"{year}.nc")
        
    def _get_processed_path(self, variable: str, year: int) -> str:
        # Match phase 5 naming structure
        if variable == 'rainfall':
            var_dir = 'rainfall'
        elif variable == 'tmax':
            var_dir = 'max_temperature'
        elif variable == 'tmin':
            var_dir = 'min_temperature'
        else:
            var_dir = variable
        return os.path.join(self.processed_dir, var_dir, f"{year}.nc")

    def append_daily_slice(self, variable: str, daily_path: str):
        """
        Atomically appends a validated daily NetCDF to the yearly state store.
        If the year doesn't exist in state, it starts a new file.
        """
        daily_ds = xr.open_dataset(daily_path)
        date = pd.Timestamp(daily_ds.time.values[0])
        year = date.year
        
        target_path = self._get_yearly_path(variable, year)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        if os.path.exists(target_path):
            existing_ds = xr.open_dataset(target_path)
            existing_ds.load()
            
            # Idempotency check: if date already exists, replace it or skip?
            # We will drop the existing date and concatenate to ensure overwrite.
            if date in existing_ds.time.values:
                existing_ds = existing_ds.drop_sel(time=[date])
                
            combined = xr.concat([existing_ds, daily_ds], dim='time').sortby('time')
            existing_ds.close()
        else:
            combined = daily_ds
            
        tmp_path = target_path + ".tmp"
        combined.to_netcdf(tmp_path)
        
        # Atomic replace
        os.replace(tmp_path, target_path)
        daily_ds.close()

    def get_dataset(self, variable: str, year: int) -> xr.Dataset:
        """
        Returns the dataset for a year. 
        It prioritizes data/state. If data/state doesn't have the year, 
        it falls back to data/processed to provide historical continuity.
        If data/state DOES have the year, it returns ONLY data/state 
        (we assume ingestion for that year is comprehensive or we are simulating real-time starting Jan 1).
        Wait, if we simulate starting mid-year (e.g. 2022-06-01), the state store will only have June onwards, 
        and missing Jan-May! So we must merge them dynamically.
        """
        state_path = self._get_yearly_path(variable, year)
        processed_path = self._get_processed_path(variable, year)
        
        has_state = os.path.exists(state_path)
        has_processed = os.path.exists(processed_path)
        
        if not has_state and not has_processed:
            raise ValueError(f"No state or processed data found for {variable} in {year}")
            
        if has_state and not has_processed:
            return xr.open_dataset(state_path).load()
            
        if has_processed and not has_state:
            return xr.open_dataset(processed_path).load()
            
        # Both exist - we must merge them, preferring state data where dates overlap.
        state_ds = xr.open_dataset(state_path).load()
        processed_ds = xr.open_dataset(processed_path).load()
        
        # Remove overlapping dates from processed_ds
        overlap_dates = state_ds.time.values
        # Only keep dates in processed that are NOT in state
        processed_keep = [t for t in processed_ds.time.values if t not in overlap_dates]
        
        if len(processed_keep) > 0:
            processed_ds = processed_ds.sel(time=processed_keep)
            combined = xr.concat([processed_ds, state_ds], dim='time').sortby('time')
            return combined
        else:
            return state_ds
