import pytest
import numpy as np
import pyarrow.parquet as pq
import lightgbm as lgb
from src.inference.schemas import InferenceInput
from src.inference.predictor import CloudSensePredictor
from src.inference.model_loader import CloudSenseModelManager
from src.inference.feature_contract import EXPECTED_FEATURES

def get_test_sample():
    """
    Extracts the first valid row from the testing parquet files 
    for deterministic equivalence testing.
    """
    # Just take one of the test files
    table = pq.read_table("data/ml/test/2023.parquet")
    # Convert first row to dict
    df = table.slice(0, 1).to_pandas()
    row = df.iloc[0]
    
    # Extract only the 12 expected features
    input_dict = {f: float(row[f]) for f in EXPECTED_FEATURES}
    return input_dict

def test_real_model_equivalence():
    """
    Verifies that the inference wrapper produces the exact same numerical result
    as calling lightgbm.Booster.predict() directly.
    """
    input_dict = get_test_sample()
    
    # 1. Run through wrapper
    manager = CloudSenseModelManager()
    manager.load_all_models()
    predictor = CloudSensePredictor(manager)
    
    inf_input = InferenceInput(**input_dict)
    wrapper_output = predictor.predict(inf_input)
    
    # 2. Run through raw booster directly
    raw_vector = np.array([[input_dict[f] for f in EXPECTED_FEATURES]], dtype=np.float64)
    
    diffs = []
    
    for h in range(1, 8):
        booster = lgb.Booster(model_file=f"models/cloudsense_rainfall_h{h}.txt")
        raw_pred = float(booster.predict(raw_vector)[0])
        
        wrapper_pred = getattr(wrapper_output, f"h{h}")
        
        # Calculate absolute difference
        diff = abs(raw_pred - wrapper_pred)
        diffs.append(diff)
        
        # Tolerance check
        assert diff <= 1e-6, f"H{h} difference {diff} exceeds tolerance. Raw: {raw_pred}, Wrapper: {wrapper_pred}"

    max_diff = max(diffs)
    mean_diff = sum(diffs) / len(diffs)
    print(f"\nREAL MODEL EQUIVALENCE PASS.")
    print(f"Max Diff: {max_diff}")
    print(f"Mean Diff: {mean_diff}")

def test_determinism():
    """
    Verifies multiple passes yield exactly the same result.
    """
    input_dict = get_test_sample()
    
    manager = CloudSenseModelManager()
    manager.load_all_models()
    predictor = CloudSensePredictor(manager)
    
    inf_input = InferenceInput(**input_dict)
    
    # Run multiple times
    out1 = predictor.predict(inf_input)
    out2 = predictor.predict(inf_input)
    out3 = predictor.predict(inf_input)
    
    for h in range(1, 8):
        v1 = getattr(out1, f"h{h}")
        v2 = getattr(out2, f"h{h}")
        v3 = getattr(out3, f"h{h}")
        
        assert v1 == v2 == v3, "Predictions are not deterministic"
