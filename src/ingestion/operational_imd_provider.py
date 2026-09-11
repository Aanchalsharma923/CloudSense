import os
import urllib.request
import numpy as np
import xarray as xr
import pandas as pd
from typing import Optional

class OperationalIMDProvider:
    """
    Fetches real-time operational 1.0 degree temperature data directly from IMD's servers.
    Validates payload sizes, masks missing values, and writes to NetCDF for the ingestion pipeline.
    """
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.base_url_tmax = "https://www.imdpune.gov.in/cmpg/Realtimedata/maxone"
        self.base_url_tmin = "https://www.imdpune.gov.in/cmpg/Realtimedata/minone"
        self.shape = (31, 31)
        self.expected_bytes = 3844
        self.lats = np.arange(7.5, 38.5, 1.0) # 31 elements
        self.lons = np.arange(67.5, 98.5, 1.0) # 31 elements

    def _download_and_convert(self, url: str, date: str, var_name: str, target_path: str) -> bool:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                resp = urllib.request.urlopen(req, timeout=self.timeout)
                
                if resp.status != 200:
                    print(f"Error fetching {url}: HTTP {resp.status}")
                    if resp.status == 404:
                        return False # Fail fast
                    if attempt < max_retries - 1 and resp.status >= 500:
                        import time
                        time.sleep(1)
                        continue
                    return False
                    
                data = resp.read()
                if len(data) != self.expected_bytes:
                    print(f"Error fetching {url}: Expected {self.expected_bytes} bytes, got {len(data)}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)
                        continue
                    return False
                    
                arr = np.frombuffer(data, dtype=np.float32).copy()
                if len(arr) != 961:
                    return False
                    
                arr_2d = arr.reshape(self.shape)
                
                # Mask the IMD 99.9 missing value sentinel
                arr_2d[np.isclose(arr_2d, 99.9)] = np.nan
                
                # Construct Dataset
                dt = pd.Timestamp(date)
                ds = xr.Dataset(
                    data_vars={
                        var_name: (('time', 'lat', 'lon'), arr_2d[np.newaxis, :, :])
                    },
                    coords={
                        'time': [dt],
                        'lat': self.lats,
                        'lon': self.lons
                    }
                )
                
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                ds.to_netcdf(target_path)
                return True
                
            except urllib.error.HTTPError as e:
                print(f"HTTP error fetching {url}: HTTP {e.code}")
                if e.code == 404:
                    return False # Fail fast
                if attempt < max_retries - 1 and e.code >= 500:
                    import time
                    time.sleep(1)
                    continue
                return False
            except urllib.error.URLError as e:
                print(f"Network error fetching {url}: {e.reason}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1)
                    continue
                return False
            except Exception as e:
                print(f"Unexpected error processing {url}: {e}")
                return False
        return False

    def download_tmax(self, date: str, target_path: str) -> bool:
        dt = pd.Timestamp(date)
        date_str = dt.strftime("%d%m%Y")
        url = f"{self.base_url_tmax}/max1_{date_str}.grd"
        return self._download_and_convert(url, date, "tmax", target_path)

    def download_tmin(self, date: str, target_path: str) -> bool:
        dt = pd.Timestamp(date)
        date_str = dt.strftime("%d%m%Y")
        url = f"{self.base_url_tmin}/min1_{date_str}.grd"
        return self._download_and_convert(url, date, "tmin", target_path)
