import pytest
from src.inference.schemas import InferenceInput, InferenceOutput

def test_inference_output_schema():
    """
    Test the strictness of the inference output schema.
    """
    valid_output = {
        "h1": 0.0,
        "h2": 1.0,
        "h3": 2.5,
        "h4": 0.1,
        "h5": 5.5,
        "h6": 10.2,
        "h7": 0.0
    }
    
    out = InferenceOutput(**valid_output)
    assert out.h1 == 0.0
    
    invalid_output = dict(valid_output)
    invalid_output["h1"] = -1.0
    
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        InferenceOutput(**invalid_output)
