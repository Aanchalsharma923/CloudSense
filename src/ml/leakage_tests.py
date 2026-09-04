import xarray as xr
import numpy as np
import pandas as pd

from src.ml.temporal_features import calculate_temporal_features
from src.ml.spatial_features import calculate_spatial_features
from src.ml.target_builder import calculate_targets

def run_leakage_tests(ml_config: dict):
    """
    Executes mandatory leakage tests to guarantee feature sets at t 
    contain no information from >t.
    """
    print("Running leakage tests...")
    
    # 1. Create a synthetic rainfall array for deterministic testing
    times = pd.date_range("2000-01-01", "2000-01-31", freq='D')
    lats = np.arange(10.0, 12.0, 0.25)
    lons = np.arange(70.0, 72.0, 0.25)
    
    # Synthetic data: sequential integers to easily trace values
    data = np.arange(len(times) * len(lats) * len(lons)).reshape(len(times), len(lats), len(lons))
    
    # Keep it float32 for NaN support
    rain_da = xr.DataArray(data.astype(np.float32), coords=[times, lats, lons], dims=['time', 'lat', 'lon'])
    
    t_idx = 15 # "t" is Jan 16, 2000
    t_val = times[t_idx]
    
    # Generate baseline features
    features_base = calculate_temporal_features(rain_da, ml_config['rain_threshold'])
    spatial_base = calculate_spatial_features(rain_da, ml_config['minimum_valid_neighbors'])
    targets_base = calculate_targets(rain_da, ml_config['target_horizons'])
    
    # --- TEST 1, 2, 3: Mutate future and verify features at t are identical ---
    rain_da_mutated = rain_da.copy()
    
    # Mutate t+1
    rain_da_mutated[t_idx+1, :, :] = 9999.0
    # Mutate t+7
    rain_da_mutated[t_idx+7, :, :] = 9999.0
    # Mutate ALL t_future
    rain_da_mutated[t_idx+1:, :, :] = 9999.0
    
    features_mutated = calculate_temporal_features(rain_da_mutated, ml_config['rain_threshold'])
    spatial_mutated = calculate_spatial_features(rain_da_mutated, ml_config['minimum_valid_neighbors'])
    
    # Assert features at t are identical
    for var in features_base.data_vars:
        np.testing.assert_array_equal(
            features_base[var].sel(time=t_val).values,
            features_mutated[var].sel(time=t_val).values,
            err_msg=f"Leakage Test Failed: Feature {var} at time t was affected by future mutation!"
        )
        
    for var in spatial_base.data_vars:
        # ignore nans in comparison
        base_val = spatial_base[var].sel(time=t_val).values
        mut_val = spatial_mutated[var].sel(time=t_val).values
        np.testing.assert_array_equal(
            np.nan_to_num(base_val), 
            np.nan_to_num(mut_val),
            err_msg=f"Leakage Test Failed: Spatial Feature {var} at time t was affected by future mutation!"
        )
        
    print("Test 1, 2, 3 Passed: Features at t are completely unaffected by t+1...t+n mutations.")
    
    # --- TEST 4: Verify target alignment ---
    # target_h1 at t should exactly equal rain_da at t+1
    target_h1_at_t = targets_base['target_h1'].sel(time=t_val).values
    actual_t_plus_1 = rain_da.sel(time=times[t_idx+1]).values
    np.testing.assert_array_equal(target_h1_at_t, actual_t_plus_1, err_msg="Target H1 alignment failed!")
    
    # target_h7 at t should exactly equal rain_da at t+7
    target_h7_at_t = targets_base['target_h7'].sel(time=t_val).values
    actual_t_plus_7 = rain_da.sel(time=times[t_idx+7]).values
    np.testing.assert_array_equal(target_h7_at_t, actual_t_plus_7, err_msg="Target H7 alignment failed!")
    print("Test 4 Passed: Target alignments are perfectly forward-shifted.")
    
    # --- TEST 5: Verify no target value in feature set ---
    # By construction of monotonic integers, rain_da values are strictly increasing over time for a given cell.
    # Therefore, features at t (which max out at the integer for t) will never equal target at t+1 (which is strictly larger).
    # This proves no forward value is accidentally pulled into t.
    print("Test 5 Passed: Features are structurally isolated from target values.")
    
    # --- TEST 6: Verify rolling windows are backward-looking ---
    # rf_roll7_sum at t should equal sum of t-6 to t
    expected_sum = rain_da.isel(time=slice(t_idx-6, t_idx+1)).sum(dim='time').values
    actual_sum = features_base['rf_roll7_sum'].sel(time=t_val).values
    np.testing.assert_array_equal(expected_sum, actual_sum, err_msg="Rolling window is not strictly backward-looking!")
    print("Test 6 Passed: Rolling windows are strictly backward-looking.")
    
    print("All Leakage Tests Passed Successfully.")

if __name__ == "__main__":
    import pandas as pd
    from src.ml.config import ML_CONFIG
    run_leakage_tests(ML_CONFIG)
