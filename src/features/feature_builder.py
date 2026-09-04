import numpy as np
import pandas as pd
from typing import Dict, Any

from src.features.feature_state import FeatureState
from src.features.grid_mapper import GridMapper
from src.features.providers import HistoricalNetCDFProvider

class ProductionFeatureBuilder:
    """
    Builds the exact 12-feature FeatureState for a given prediction request,
    guaranteeing deterministic parity with the historical Phase 5 pipeline.
    """
    def __init__(self, grid_mapper: GridMapper, provider: HistoricalNetCDFProvider):
        self.grid_mapper = grid_mapper
        self.provider = provider
        
    def build(self, lat: float, lon: float, base_date: str) -> FeatureState:
        date_t = pd.Timestamp(base_date)
        
        # 1. Coordinate Mapping
        snapped_rf_lat, snapped_rf_lon, rf_lat_idx, rf_lon_idx = self.grid_mapper.map_to_rainfall_grid(lat, lon)
        snapped_t_lat, snapped_t_lon, t_lat_idx, t_lon_idx = self.grid_mapper.map_to_temperature_grid(lat, lon)
        
        # 2. Retrieve Data
        # Rainfall requires T-6 to T (7 days)
        rf_history = self.provider.get_rainfall_history(rf_lat_idx, rf_lon_idx, date_t, lookback_days=6)
        
        # 3. Temporal Rainfall Features
        rf_lag_1 = float(rf_history[-1])
        rf_lag_2 = float(rf_history[-2])
        
        # rf_roll7_sum: skipna=True in xarray rolling sum, min_periods=1
        if np.isnan(rf_history).all():
            rf_roll7_sum = np.nan
        else:
            rf_roll7_sum = float(np.nansum(rf_history))
            
        # days_since_rain (Requires scanning backwards)
        days_since_rain = self.provider.get_days_since_rain(rf_lat_idx, rf_lon_idx, date_t)
        
        # 4. Spatial Rainfall Features
        neighborhood = self.provider.get_spatial_neighbors(rf_lat_idx, rf_lon_idx, date_t)
        # flatten and remove NaNs
        valid_neighbors = neighborhood[~np.isnan(neighborhood)]
        
        # minimum valid neighbors = 3
        if len(valid_neighbors) >= 3:
            neighbor_mean_lag1 = float(np.mean(valid_neighbors))
            neighbor_max_lag1 = float(np.max(valid_neighbors))
        else:
            neighbor_mean_lag1 = np.nan
            neighbor_max_lag1 = np.nan
            
        # 5. Temperature Features
        tmax_history, tmin_history = self.provider.get_temperature_history(t_lat_idx, t_lon_idx, date_t, lookback_days=6)
        
        tmax_1deg_lag1 = float(tmax_history[-1])
        tmin_1deg_lag1 = float(tmin_history[-1])
        
        if np.isnan(tmax_history).all():
            tmax_1deg_roll7 = np.nan
        else:
            tmax_1deg_roll7 = float(np.nanmean(tmax_history))
            
        diurnal_range_1deg = tmax_1deg_lag1 - tmin_1deg_lag1
        
        # 6. Seasonal Features
        doy = date_t.dayofyear
        sin_doy = float(np.sin(2 * np.pi * doy / 365.25))
        cos_doy = float(np.cos(2 * np.pi * doy / 365.25))
        
        # 7. Construct and Validate
        # The FeatureState validator will throw an explicit error if any feature is NaN/Inf
        try:
            return FeatureState(
                latitude_snapped=snapped_rf_lat,
                longitude_snapped=snapped_rf_lon,
                base_date=base_date,
                rf_lag_1=rf_lag_1,
                rf_lag_2=rf_lag_2,
                rf_roll7_sum=rf_roll7_sum,
                days_since_rain=days_since_rain,
                neighbor_mean_lag1=neighbor_mean_lag1,
                neighbor_max_lag1=neighbor_max_lag1,
                tmax_1deg_lag1=tmax_1deg_lag1,
                tmin_1deg_lag1=tmin_1deg_lag1,
                tmax_1deg_roll7=tmax_1deg_roll7,
                diurnal_range_1deg=diurnal_range_1deg,
                sin_doy=sin_doy,
                cos_doy=cos_doy
            )
        except ValueError as e:
            raise ValueError(f"FeatureState construction failed due to missing or invalid data: {e}")

