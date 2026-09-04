import os
import lightgbm as lgb
from pathlib import Path
from src.inference.feature_contract import EXPECTED_FEATURES

class CloudSenseModelManager:
    """
    Manager class responsible for strictly loading and verifying the frozen
    CloudSense ML V1 model artifacts.
    """
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models = {}
        
    def load_all_models(self):
        """
        Loads H1-H7 models and performs strict architectural checks.
        Throws RuntimeError if any check fails.
        """
        for h in range(1, 8):
            model_name = f"cloudsense_rainfall_h{h}.txt"
            model_path = self.models_dir / model_name
            
            if not model_path.exists():
                raise RuntimeError(f"Missing model artifact: {model_path}")
                
            try:
                booster = lgb.Booster(model_file=str(model_path))
            except Exception as e:
                raise RuntimeError(f"Failed to load LightGBM Booster from {model_path}: {e}")
                
            self._verify_model_architecture(booster, model_name)
            self.models[f"h{h}"] = booster
            
    def _verify_model_architecture(self, booster: lgb.Booster, model_name: str):
        """
        Strictly verifies that the frozen architecture hasn't been modified.
        """
        # 1. Verify Objective
        params = booster.params
        if params.get('objective') != 'tweedie':
            raise RuntimeError(f"Model {model_name} has invalid objective: {params.get('objective')}. Expected: tweedie.")
            
        # 2. Verify Tweedie variance power
        if params.get('tweedie_variance_power') != 1.5:
            raise RuntimeError(f"Model {model_name} has invalid variance power: {params.get('tweedie_variance_power')}. Expected: 1.5.")
            
        # 3. Verify Feature Count
        if booster.num_feature() != 12:
            raise RuntimeError(f"Model {model_name} expects {booster.num_feature()} features, but 12 are required.")
            
        # 4. Verify Feature Names & Ordering
        actual_features = booster.feature_name()
        if actual_features != EXPECTED_FEATURES:
            raise RuntimeError(
                f"Model {model_name} feature contract mismatch.\n"
                f"Expected: {EXPECTED_FEATURES}\n"
                f"Actual:   {actual_features}"
            )
            
    def get_model(self, horizon: str) -> lgb.Booster:
        """
        Returns the requested model (e.g., 'h1').
        """
        if horizon not in self.models:
            raise ValueError(f"Model for {horizon} not loaded.")
        return self.models[horizon]
