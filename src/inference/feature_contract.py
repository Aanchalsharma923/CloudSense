import numpy as np
from src.inference.schemas import InferenceInput

# The one canonical authoritative feature list, frozen as per Phase 7.1.
EXPECTED_FEATURES = [
    "rf_lag_1",
    "rf_lag_2",
    "rf_roll7_sum",
    "days_since_rain",
    "neighbor_mean_lag1",
    "neighbor_max_lag1",
    "tmax_1deg_lag1",
    "tmin_1deg_lag1",
    "tmax_1deg_roll7",
    "diurnal_range_1deg",
    "sin_doy",
    "cos_doy"
]

def build_feature_vector(input_data: InferenceInput) -> np.ndarray:
    """
    Safely converts the validated InferenceInput into a 2D numpy array
    preserving the exact frozen feature ordering.
    
    Returns:
        np.ndarray of shape (1, 12)
    """
    # Extract features using the canonical ordering explicitly.
    data_dict = input_data.model_dump()
    vector = [data_dict[feature_name] for feature_name in EXPECTED_FEATURES]
    
    # Return as 2D array expected by LightGBM Booster.predict()
    return np.array([vector], dtype=np.float64)
