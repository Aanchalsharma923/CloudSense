import pytest
from pathlib import Path
from src.inference.model_loader import CloudSenseModelManager

def test_model_loading_success():
    """
    Test that the actual models load correctly and pass the strict checks.
    Depends on models/ existing.
    """
    manager = CloudSenseModelManager(models_dir="models")
    manager.load_all_models()
    
    # Check we have 7 models
    assert len(manager.models) == 7
    assert "h1" in manager.models
    assert "h7" in manager.models
    
    # Check a specific property is set by our loading process
    booster = manager.get_model("h1")
    assert booster.num_feature() == 12

def test_model_loading_missing_directory(tmp_path):
    """
    Test that pointing to an empty directory fails safely.
    """
    manager = CloudSenseModelManager(models_dir=str(tmp_path))
    with pytest.raises(RuntimeError, match="Missing model artifact"):
        manager.load_all_models()

def test_get_unloaded_model():
    """
    Test that requesting an unloaded model throws an error.
    """
    manager = CloudSenseModelManager(models_dir="models")
    with pytest.raises(ValueError, match="not loaded"):
        manager.get_model("h1")
