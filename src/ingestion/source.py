import os
import xarray as xr
import pandas as pd
from typing import Optional

class MockIMDProvider:
    """
    Simulates a daily real-time ingestion source by fetching exactly one day 
    of data from the historical processed archive.
    """
    def __init__(self, historical_archive_dir: str = "data/processed"):
        self.archive_dir = historical_archive_dir
        
    def _fetch_daily_slice(self, dataset: str, variable: str, date: str, target_path: str) -> bool:
        """
        Extracts exactly one day and saves it to a new NetCDF, simulating a downloaded daily file.
        Returns True if successful, False if the data does not exist in the archive.
        """
        try:
            dt = pd.Timestamp(date)
            year = dt.year
            source_path = os.path.join(self.archive_dir, dataset, f"{year}.nc")
            
            if not os.path.exists(source_path):
                return False
                
            ds = xr.open_dataset(source_path)
            # Check if date is in ds
            if dt not in ds.time.values:
                return False
                
            # Extract daily slice (keeping time dimension with size 1)
            daily_ds = ds.sel(time=[dt])
            
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            daily_ds.to_netcdf(target_path)
            return True
        except Exception:
            return False

    def download_rainfall(self, date: str, target_path: str) -> bool:
        return self._fetch_daily_slice("rainfall", "rainfall", date, target_path)

    def download_tmax(self, date: str, target_path: str) -> bool:
        return self._fetch_daily_slice("max_temperature", "tmax", date, target_path)

    def download_tmin(self, date: str, target_path: str) -> bool:
        return self._fetch_daily_slice("min_temperature", "tmin", date, target_path)
