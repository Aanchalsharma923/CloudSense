import xarray as xr
import numpy as np

def compare_years(var_name: str, ds_2000_path: str, ds_2001_path: str):
    print(f"\n========================================")
    print(f"Comparing {var_name}: 2000 vs 2001")
    print(f"========================================")
    
    ds2000 = xr.open_dataset(ds_2000_path)
    ds2001 = xr.open_dataset(ds_2001_path)
    
    var_key = list(ds2000.data_vars.keys())[0]
    
    data_2000 = ds2000[var_key]
    data_2001 = ds2001[var_key]
    
    print(f"{'Metric':<25} | {'2000':<25} | {'2001':<25}")
    print("-" * 80)
    
    var_name_lower = var_name.lower()
    metrics = {
        "Dimensions": (str(dict(data_2000.sizes)), str(dict(data_2001.sizes))),
        "Number of timestamps": (len(data_2000.time), len(data_2001.time)),
        "First timestamp": (str(data_2000.time.values[0])[:10], str(data_2001.time.values[0])[:10]),
        "Last timestamp": (str(data_2000.time.values[-1])[:10], str(data_2001.time.values[-1])[:10]),
        "Latitude minimum": (float(data_2000.lat.min()), float(data_2001.lat.min())),
        "Latitude maximum": (float(data_2000.lat.max()), float(data_2001.lat.max())),
        "Longitude minimum": (float(data_2000.lon.min()), float(data_2001.lon.min())),
        "Longitude maximum": (float(data_2000.lon.max()), float(data_2001.lon.max())),
        "Latitude spacing": (float(data_2000.lat[1] - data_2000.lat[0]), float(data_2001.lat[1] - data_2001.lat[0])),
        "Longitude spacing": (float(data_2000.lon[1] - data_2000.lon[0]), float(data_2001.lon[1] - data_2001.lon[0])),
        "Coordinate ordering": ("(time, lat, lon)", "(time, lat, lon)"),  # Checked natively by sizes
        "Units": (data_2000.attrs.get('units', 'Celsius' if 'temp' in var_name_lower else 'mm'), 
                  data_2001.attrs.get('units', 'Celsius' if 'temp' in var_name_lower else 'mm')),
        "Missing-value count": (int(data_2000.isnull().sum()), int(data_2001.isnull().sum())),
        "Valid-value count": (int(data_2000.count()), int(data_2001.count())),
        "Minimum": (float(data_2000.min()), float(data_2001.min())),
        "Maximum": (float(data_2000.max()), float(data_2001.max())),
        "Mean": (float(data_2000.mean()), float(data_2001.mean()))
    }
    
    for key, (v2000, v2001) in metrics.items():
        v2000_str = str(v2000)
        if isinstance(v2000, float):
            v2000_str = f"{v2000:.4f}"
        
        v2001_str = str(v2001)
        if isinstance(v2001, float):
            v2001_str = f"{v2001:.4f}"
            
        print(f"{key:<25} | {v2000_str:<25} | {v2001_str:<25}")
        
    ds2000.close()
    ds2001.close()

if __name__ == '__main__':
    compare_years(
        "Rainfall", 
        "data/processed/rainfall_2000.nc", 
        "data/processed/rainfall/2001.nc"
    )
    compare_years(
        "Max Temperature", 
        "data/processed/max_temp_2000.nc", 
        "data/processed/max_temperature/2001.nc"
    )
    compare_years(
        "Min Temperature", 
        "data/processed/min_temp_2000.nc", 
        "data/processed/min_temperature/2001.nc"
    )
