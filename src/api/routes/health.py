from fastapi import APIRouter, Depends
from src.api.schemas import HealthResponse, ReadyResponse
from src.api.dependencies import get_pipeline
from src.ingestion.pipeline import IngestionPipeline

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Returns the service health status."""
    return HealthResponse(status="ok", service="cloudsense")

@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(pipeline: IngestionPipeline = Depends(get_pipeline)):
    """Checks if a complete prediction state is available."""
    try:
        latest_t = pipeline.get_latest_valid_t()
        if latest_t is None:
            return ReadyResponse(status="not_ready", reason="A complete meteorological observation state is not available.")
        
        return ReadyResponse(status="ready", latest_valid_T=latest_t)
    except Exception as e:
        return ReadyResponse(status="not_ready", reason=f"StateStore error: {str(e)}")
