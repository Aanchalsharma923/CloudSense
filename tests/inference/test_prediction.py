import pytest
import numpy as np
from src.inference.schemas import InferenceInput
from src.inference.predictor import CloudSensePredictor
from src.inference.model_loader import CloudSenseModelManager
from tests.inference.test_feature_contract import get_valid_input_dict

class MockBooster:
    def __init__(self, return_val):
        self.return_val = return_val
        
    def predict(self, features):
        return np.array([self.return_val])

class MockManager(CloudSenseModelManager):
    def __init__(self, return_val):
        super().__init__()
        self.mock_booster = MockBooster(return_val)
        
    def get_model(self, horizon):
        return self.mock_booster

def test_negative_clamping():
    """
    Test that if a LightGBM model returns a negative value, it is clamped to 0.0.
    """
    manager = MockManager(-1.5)
    predictor = CloudSensePredictor(manager)
    
    input_data = InferenceInput(**get_valid_input_dict())
    output = predictor.predict(input_data)
    
    assert output.h1 == 0.0
    assert output.h7 == 0.0

def test_positive_values():
    """
    Test that normal positive values are passed through intact.
    """
    manager = MockManager(4.2)
    predictor = CloudSensePredictor(manager)
    
    input_data = InferenceInput(**get_valid_input_dict())
    output = predictor.predict(input_data)
    
    assert output.h1 == 4.2

def test_nan_prediction():
    """
    Test that if the model returns NaN, it throws an error and does not return 0.
    """
    manager = MockManager(float('nan'))
    predictor = CloudSensePredictor(manager)
    
    input_data = InferenceInput(**get_valid_input_dict())
    with pytest.raises(ValueError, match="non-finite prediction"):
        predictor.predict(input_data)
