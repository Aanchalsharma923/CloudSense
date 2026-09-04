from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator
import math

class FeatureState(BaseModel):
    """
    The canonical, strict feature contract required by the CloudSensePredictor.
    All features must be provided, must be finite, and must not be NaN.
    """
    latitude_snapped: float
    longitude_snapped: float
    base_date: str
    
    rf_lag_1: float
    rf_lag_2: float
    rf_roll7_sum: float
    days_since_rain: float
    neighbor_mean_lag1: float
    neighbor_max_lag1: float
    tmax_1deg_lag1: float
    tmin_1deg_lag1: float
    tmax_1deg_roll7: float
    diurnal_range_1deg: float
    sin_doy: float
    cos_doy: float

    @field_validator(
        "rf_lag_1", "rf_lag_2", "rf_roll7_sum", "days_since_rain",
        "neighbor_mean_lag1", "neighbor_max_lag1", "tmax_1deg_lag1",
        "tmin_1deg_lag1", "tmax_1deg_roll7", "diurnal_range_1deg",
        "sin_doy", "cos_doy"
    )
    def check_finite(cls, v):
        if math.isnan(v):
            raise ValueError("Feature value cannot be NaN")
        if math.isinf(v):
            raise ValueError("Feature value cannot be Infinity")
        return v
    
    def to_dict(self) -> Dict[str, float]:
        """
        Returns the features exactly in the order required by the model.
        """
        return {
            "rf_lag_1": self.rf_lag_1,
            "rf_lag_2": self.rf_lag_2,
            "rf_roll7_sum": self.rf_roll7_sum,
            "days_since_rain": self.days_since_rain,
            "neighbor_mean_lag1": self.neighbor_mean_lag1,
            "neighbor_max_lag1": self.neighbor_max_lag1,
            "tmax_1deg_lag1": self.tmax_1deg_lag1,
            "tmin_1deg_lag1": self.tmin_1deg_lag1,
            "tmax_1deg_roll7": self.tmax_1deg_roll7,
            "diurnal_range_1deg": self.diurnal_range_1deg,
            "sin_doy": self.sin_doy,
            "cos_doy": self.cos_doy
        }
