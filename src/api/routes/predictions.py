from fastapi import APIRouter, Depends
from src.api.schemas import PredictionRequest, PredictionResponse, LocationData, ForecastsData
from src.api.dependencies import get_feature_builder, get_predictor, get_pipeline
from src.api.errors import InvalidCoordinatesError, LocationUnsupportedError, DataNotReadyError, InsufficientHistoryError, ModelError
from src.features.feature_builder import ProductionFeatureBuilder
from src.inference.predictor import CloudSensePredictor
from src.inference.schemas import InferenceInput
from src.ingestion.pipeline import IngestionPipeline
import logging

router = APIRouter()
logger = logging.getLogger("cloudsense.api")

@router.post("/predict", response_model=PredictionResponse)
async def predict_rainfall(
    request: PredictionRequest,
    feature_builder: ProductionFeatureBuilder = Depends(get_feature_builder),
    predictor: CloudSensePredictor = Depends(get_predictor),
    pipeline: IngestionPipeline = Depends(get_pipeline)
):
    """Generates a 7-day rainfall forecast for a given location."""
    
    # 1. Determine base date T
    if request.base_date:
        base_date_t = request.base_date
    else:
        latest_t = pipeline.get_latest_valid_t()
        if not latest_t:
            raise DataNotReadyError("A complete meteorological observation state is not available.")
        base_date_t = latest_t

    # 2. Build feature state
    try:
        feature_state = feature_builder.build(request.latitude, request.longitude, base_date_t)
    except ValueError as e:
        error_msg = str(e)
        if "outside the supported" in error_msg:
            raise InvalidCoordinatesError(error_msg)
        elif "invalid/ocean cell" in error_msg:
            raise LocationUnsupportedError(error_msg)
        elif "FeatureState construction failed" in error_msg or "history" in error_msg.lower() or "missing" in error_msg.lower():
            raise InsufficientHistoryError(f"Required historical rainfall/temperature state is unavailable. Details: {error_msg}")
        else:
            raise InsufficientHistoryError(error_msg)
    except Exception as e:
        logger.error(f"Error building features: {e}")
        raise InsufficientHistoryError(f"Failed to build feature state: {e}")

    # 3. Predict
    try:
        inference_input = InferenceInput(**feature_state.to_dict())
        prediction_output = predictor.predict(inference_input)
    except ValueError as e:
        raise ModelError(f"Prediction failed: {e}")
    except Exception as e:
        logger.error(f"Predictor error: {e}")
        raise ModelError("Prediction model could not be loaded or executed.")

    # 4. Construct response
    location_data = LocationData(
        latitude=request.latitude,
        longitude=request.longitude,
        latitude_snapped=feature_state.latitude_snapped,
        longitude_snapped=feature_state.longitude_snapped
    )

    forecasts_data = ForecastsData(
        h1=prediction_output.h1,
        h2=prediction_output.h2,
        h3=prediction_output.h3,
        h4=prediction_output.h4,
        h5=prediction_output.h5,
        h6=prediction_output.h6,
        h7=prediction_output.h7
    )

    response = PredictionResponse(
        status="success",
        location=location_data,
        base_date_T=base_date_t,
        forecasts=forecasts_data,
        unit="mm"
    )

    logger.info(f"Prediction successful for lat={request.latitude}, lon={request.longitude}, T={base_date_t}")
    return response
