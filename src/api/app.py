import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health, predictions
from src.api.errors import (
    CloudSenseAPIError,
    cloudsense_exception_handler,
    validation_exception_handler,
    general_exception_handler
)

from src.features.grid_mapper import GridMapper
from src.features.providers import StateStoreProvider
from src.features.feature_builder import ProductionFeatureBuilder
from src.inference.model_loader import CloudSenseModelManager
from src.inference.predictor import CloudSensePredictor
from src.ingestion.state_store import StateStore
from src.ingestion.pipeline import IngestionPipeline

# Configure logging
logging_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=logging_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("cloudsense.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Load Configurations
    base_dir = os.environ.get("CLOUDSENSE_BASE_DIR", ".")
    models_dir = os.environ.get("CLOUDSENSE_MODELS_DIR", os.path.join(base_dir, "models"))
    state_dir = os.environ.get("CLOUDSENSE_STATE_DIR", os.path.join(base_dir, "data", "state"))
    processed_dir = os.environ.get("CLOUDSENSE_PROCESSED_DIR", os.path.join(base_dir, "data", "processed"))
    
    rainfall_nc = os.path.join(processed_dir, "rainfall", "2023.nc")
    tmax_nc = os.path.join(processed_dir, "max_temperature", "2023.nc")
    
    logger.info("Initializing CloudSense API dependencies...")
    
    try:
        # 2. Initialize Models & Predictor
        model_manager = CloudSenseModelManager(models_dir)
        model_manager.load_all_models()
        predictor = CloudSensePredictor(model_manager)
        app.state.predictor = predictor
        
        # 3. Initialize Grid Mapper
        grid_mapper = GridMapper(rainfall_nc, tmax_nc)
        
        # 4. Initialize State Store and Pipeline
        state_store = StateStore(state_dir, processed_dir)
        app.state.state_store = state_store
        
        manifest_path = os.environ.get("CLOUDSENSE_MANIFEST_PATH", os.path.join(base_dir, "data", "raw", "manifest.json"))
        raw_dir = os.environ.get("CLOUDSENSE_RAW_DIR", os.path.join(base_dir, "data", "raw"))
        staging_dir = os.environ.get("CLOUDSENSE_STAGING_DIR", os.path.join(base_dir, "data", "staging"))
        
        pipeline = IngestionPipeline(
            manifest_path=manifest_path,
            staging_dir=staging_dir,
            raw_dir=raw_dir,
            state_dir=state_dir,
            processed_dir=processed_dir
        )
        app.state.pipeline = pipeline
        
        # 5. Initialize Feature Builder
        provider = StateStoreProvider(state_store)
        feature_builder = ProductionFeatureBuilder(grid_mapper, provider)
        app.state.feature_builder = feature_builder
        
        logger.info("CloudSense API dependencies loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize API dependencies: {e}")
        raise RuntimeError(f"Initialization failed: {e}")
        
    yield
    logger.info("Shutting down CloudSense API...")

# Initialize FastAPI App
app = FastAPI(
    title="CloudSense Prediction API",
    description="Local FastAPI Prediction Service for Phase 8.4",
    version="1.0.0",
    lifespan=lifespan
)

# Exception Handlers
app.add_exception_handler(CloudSenseAPIError, cloudsense_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(predictions.router, tags=["Prediction"])
