import math
from pydantic import BaseModel, Field, field_validator

class InferenceInput(BaseModel):
    """
    Strict representation of the 12-feature contract required by CloudSense models.
    """
    rf_lag_1: float = Field(..., description="Rainfall from previous day (t-1)")
    rf_lag_2: float = Field(..., description="Rainfall from two days ago (t-2)")
    rf_roll7_sum: float = Field(..., description="Rolling 7-day sum of rainfall")
    days_since_rain: float = Field(..., description="Consecutive days since last rainfall > 0.1mm")
    neighbor_mean_lag1: float = Field(..., description="Mean rainfall of 8 spatial neighbors at t-1")
    neighbor_max_lag1: float = Field(..., description="Max rainfall of 8 spatial neighbors at t-1")
    tmax_1deg_lag1: float = Field(..., description="Maximum temperature at t-1")
    tmin_1deg_lag1: float = Field(..., description="Minimum temperature at t-1")
    tmax_1deg_roll7: float = Field(..., description="Rolling 7-day average of maximum temperature")
    diurnal_range_1deg: float = Field(..., description="Difference between max and min temperature at t-1")
    sin_doy: float = Field(..., description="Sine of day of year")
    cos_doy: float = Field(..., description="Cosine of day of year")

    @field_validator('*', mode='before')
    @classmethod
    def reject_nan_inf(cls, v, info):
        if v is None:
            raise ValueError(f"Field {info.field_name} cannot be None.")
        try:
            val = float(v)
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Field {info.field_name} must be a finite number. Got {v}.")
        except (TypeError, ValueError) as e:
            if "finite number" in str(e):
                raise
            raise ValueError(f"Field {info.field_name} must be a valid float.")
        return val


class InferenceOutput(BaseModel):
    """
    Output predictions for Horizons 1 through 7 (rainfall in mm).
    """
    h1: float = Field(..., ge=0.0)
    h2: float = Field(..., ge=0.0)
    h3: float = Field(..., ge=0.0)
    h4: float = Field(..., ge=0.0)
    h5: float = Field(..., ge=0.0)
    h6: float = Field(..., ge=0.0)
    h7: float = Field(..., ge=0.0)
