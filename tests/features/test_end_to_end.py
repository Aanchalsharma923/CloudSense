import pytest
import pandas as pd
from src.features.grid_mapper import GridMapper
from src.features.providers import HistoricalNetCDFProvider
from src.features.feature_builder import ProductionFeatureBuilder
from src.inference.predictor import CloudSensePredictor
from src.inference.model_loader import CloudSenseModelManager

@pytest.fixture(scope="module")
def end_to_end():
    mapper = GridMapper(
        rainfall_nc_path="data/processed/rainfall/2023.nc",
        tmax_nc_path="data/processed/max_temperature/2023.nc"
    )
    provider = HistoricalNetCDFProvider(data_dir="data/processed")
    builder = ProductionFeatureBuilder(grid_mapper=mapper, provider=provider)
    
    # We also need the predictor
    model_manager = CloudSenseModelManager(models_dir="models")
    model_manager.load_all_models()
    predictor = CloudSensePredictor(model_manager)
    
    return builder, predictor

def test_feature_builder_to_predictor(end_to_end):
    builder, predictor = end_to_end
    
    # Example valid location and date
    lat = 19.25
    lon = 72.75
    base_date = "2023-08-15"
    
    # 1. Build Feature State
    feature_state = builder.build(lat, lon, base_date)
    
    # 2. Extract 12 features as dict matching inference schema
    # Pydantic InferenceInput takes a dict
    input_data = feature_state.to_dict()
    
    # 3. Call predictor
    from src.inference.schemas import InferenceInput
    inference_input = InferenceInput(**input_data)
    result = predictor.predict(inference_input)
    
    assert hasattr(result, 'h1')
    assert hasattr(result, 'h7')
    assert result.h1 >= 0.0
    assert result.h7 >= 0.0
