import os
import urllib.request
import urllib.parse
import numpy as np
import xarray as xr
import pandas as pd

class OperationalIMDRainfallProvider:
    """
    Fetches real-time operational 0.25 degree rainfall data directly from IMD's servers via POST.
    Validates payload size, masks missing values, and writes to NetCDF.
    """
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.url = "https://www.imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php"
        self.shape = (129, 135)
        self.expected_bytes = 69660
        self.lats = np.linspace(6.5, 38.5, 129)
        self.lons = np.linspace(66.5, 100.0, 135)

    def download_rainfall(self, date: str, target_path: str) -> bool:
        dt = pd.Timestamp(date)
        date_str = dt.strftime("%d%m%Y")
        data = urllib.parse.urlencode({'rain': date_str}).encode('utf-8')
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(self.url, data=data, method="POST")
                req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
                
                resp = urllib.request.urlopen(req, timeout=self.timeout)
                
                if resp.status != 200:
                    print(f"Error fetching {self.url}: HTTP {resp.status}")
                    if attempt < max_retries - 1 and resp.status >= 500:
                        import time
                        time.sleep(1)
                        continue
                    return False
                    
                content = resp.read()
                
                if len(content) == 0:
                    # 0-byte payload means data is not yet published for this date
                    return False
                    
                if len(content) != self.expected_bytes:
                    print(f"Error fetching {self.url}: Expected {self.expected_bytes} bytes, got {len(content)}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)
                        continue
                    return False
                    
                arr = np.frombuffer(content, dtype=np.float32).copy()
                if len(arr) != 17415:
                    return False
                    
                arr_2d = arr.reshape(self.shape)
                
                # Mask the IMD -999.0 missing value sentinel
                arr_2d[np.isclose(arr_2d, -999.0)] = np.nan
                
                # Construct Dataset
                ds = xr.Dataset(
                    data_vars={
                        'rainfall': (('time', 'lat', 'lon'), arr_2d[np.newaxis, :, :])
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
                print(f"HTTP error fetching {self.url}: HTTP {e.code}")
                if attempt < max_retries - 1 and e.code >= 500:
                    import time
                    time.sleep(1)
                    continue
                return False
            except urllib.error.URLError as e:
                print(f"Network error fetching {self.url}: {e.reason}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1)
                    continue
                return False
            except Exception as e:
                print(f"Unexpected error processing {self.url}: {e}")
                return False
        return False
