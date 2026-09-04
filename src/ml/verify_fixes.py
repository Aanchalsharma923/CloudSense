import xarray as xr
import numpy as np
import pandas as pd
from src.ml.temporal_features import calculate_temporal_features

def test_days_since_rain():
    # Sequence 1: 0, 0, 5 -> 0
    # Sequence 2: 5, 0, 0 -> 2
    # Sequence 3: 5, NaN, 0 -> 1
    
    times = pd.date_range("2000-01-01", periods=3)
    lats = [10.0]
    lons = [70.0, 71.0, 72.0]
    
    # Create 3x1x3 grid
    data = np.zeros((3, 1, 3), dtype=np.float32)
    # lon index 0 (Sequence 1)
    data[:, 0, 0] = [0.0, 0.0, 5.0]
    # lon index 1 (Sequence 2)
    data[:, 0, 1] = [5.0, 0.0, 0.0]
    # lon index 2 (Sequence 3)
    data[:, 0, 2] = [5.0, np.nan, 0.0]
    
    da = xr.DataArray(data, coords=[times, lats, lons], dims=['time', 'lat', 'lon'])
    
    features = calculate_temporal_features(da)
    dsr = features['days_since_rain'].values
    
    seq1_result = dsr[2, 0, 0]
    seq2_result = dsr[2, 0, 1]
    seq3_result = dsr[2, 0, 2]
    
    print("Days Since Rain Deterministic Tests:")
    print(f"Sequence 1 (0, 0, 5): Expected 0, Got {seq1_result}")
    print(f"Sequence 2 (5, 0, 0): Expected 2, Got {seq2_result}")
    print(f"Sequence 3 (5, NaN, 0): Expected 1, Got {seq3_result}")
    
def check_temp_bounds():
    rain_da = xr.open_dataset('data/processed/rainfall/2000.nc')['rainfall']
    tmax_da = xr.open_dataset('data/processed/max_temperature/2000.nc')['tmax']
    
    tmax_mapped = tmax_da.interp(lat=rain_da.lat, lon=rain_da.lon, method='nearest', kwargs={"fill_value": np.nan})
    
    # Inside bounds check
    inside_lat = 20.25
    inside_lon = 80.25
    native_lat = tmax_da.lat.sel(lat=inside_lat, method='nearest').item()
    mapped_val = tmax_mapped.sel(time='2000-01-01', lat=inside_lat, lon=inside_lon).item()
    native_val = tmax_da.sel(time='2000-01-01', lat=native_lat, lon=tmax_da.lon.sel(lon=inside_lon, method='nearest')).item()
    
    print(f"\nCoordinate Mapping Check:")
    print(f"Rainfall lat {inside_lat} -> Nearest Temperature lat {native_lat}")
    print(f"Mapped value: {mapped_val}, Native value: {native_val}")
    
    # Outside bounds check
    rain_lats = rain_da.lat.values
    rain_lons = rain_da.lon.values
    tmax_lats = tmax_da.lat.values
    tmax_lons = tmax_da.lon.values
    
    out_lat_cells = np.sum((rain_lats < tmax_lats.min()) | (rain_lats > tmax_lats.max())) * len(rain_lons)
    out_lon_cells = np.sum((rain_lons < tmax_lons.min()) | (rain_lons > tmax_lons.max())) * len(rain_lats)
    
    total_rain_cells = len(rain_lats) * len(rain_lons)
    
    print("\nDomain Analysis (Grid cell level):")
    
    # We need to count exact combinations.
    LATS, LONS = np.meshgrid(rain_lats, rain_lons, indexing='ij')
    out_mask = (LATS < tmax_lats.min()) | (LATS > tmax_lats.max()) | (LONS < tmax_lons.min()) | (LONS > tmax_lons.max())
    inside_mask = ~out_mask
    
    print(f"Total rain grid points (spatial): {total_rain_cells}")
    print(f"Rain grid points strictly inside Temperature domain: {np.sum(inside_mask)}")
    print(f"Rain grid points with Lat outside Temperature Lat domain: {np.sum((LATS < tmax_lats.min()) | (LATS > tmax_lats.max()))}")
    print(f"Rain grid points with Lon outside Temperature Lon domain: {np.sum((LONS < tmax_lons.min()) | (LONS > tmax_lons.max()))}")
    print(f"Total Rain grid points outside overall Temperature domain: {np.sum(out_mask)}")
    
    # Check what value they get at time 0
    t_idx = 0
    mapped_vals_0 = tmax_mapped.isel(time=t_idx).values
    
    nan_count_outside = np.isnan(mapped_vals_0[out_mask]).sum()
    print(f"Number of outside cells receiving NaN: {nan_count_outside} out of {np.sum(out_mask)}")
    
    # What about cells over land? We only care if land cells are NaN.
    # We can just report the raw grid logic. The dataset builder filters by land_points.

if __name__ == "__main__":
    test_days_since_rain()
    check_temp_bounds()
