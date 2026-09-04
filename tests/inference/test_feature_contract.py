import pytest
import math
from pydantic import ValidationError
from src.inference.schemas import InferenceInput

def get_valid_input_dict():
    return {
        "rf_lag_1": 0.0,
        "rf_lag_2": 1.5,
        "rf_roll7_sum": 5.0,
        "days_since_rain": 2.0,
        "neighbor_mean_lag1": 0.5,
        "neighbor_max_lag1": 2.0,
        "tmax_1deg_lag1": 30.5,
        "tmin_1deg_lag1": 20.0,
        "tmax_1deg_roll7": 29.8,
        "diurnal_range_1deg": 10.5,
        "sin_doy": 0.5,
        "cos_doy": 0.866
    }

def test_valid_input():
    data = get_valid_input_dict()
    model = InferenceInput(**data)
    assert model.rf_lag_1 == 0.0

def test_missing_feature():
    data = get_valid_input_dict()
    del data["rf_lag_1"]
    with pytest.raises(ValidationError, match="Field required"):
        InferenceInput(**data)

def test_nan_rejection():
    data = get_valid_input_dict()
    data["tmax_1deg_lag1"] = float('nan')
    with pytest.raises(ValidationError, match="must be a finite number"):
        InferenceInput(**data)

def test_inf_rejection():
    data = get_valid_input_dict()
    data["rf_roll7_sum"] = float('inf')
    with pytest.raises(ValidationError, match="must be a finite number"):
        InferenceInput(**data)
    
    data["rf_roll7_sum"] = float('-inf')
    with pytest.raises(ValidationError, match="must be a finite number"):
        InferenceInput(**data)

def test_none_rejection():
    data = get_valid_input_dict()
    data["days_since_rain"] = None
    with pytest.raises(ValidationError, match="cannot be None"):
        InferenceInput(**data)

def test_string_conversion():
    # Pydantic will convert valid strings to floats, which is acceptable
    data = get_valid_input_dict()
    data["tmin_1deg_lag1"] = "20.5"
    model = InferenceInput(**data)
    assert model.tmin_1deg_lag1 == 20.5

def test_invalid_type_rejection():
    data = get_valid_input_dict()
    data["tmin_1deg_lag1"] = "not_a_number"
    with pytest.raises(ValidationError, match="must be a valid float"):
        InferenceInput(**data)
