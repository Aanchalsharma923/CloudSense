from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from src.api.schemas import ErrorResponse

class CloudSenseAPIError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class InvalidCoordinatesError(CloudSenseAPIError):
    def __init__(self, message: str):
        super().__init__("INVALID_COORDINATES", message, 400)

class LocationUnsupportedError(CloudSenseAPIError):
    def __init__(self, message: str):
        super().__init__("LOCATION_UNSUPPORTED", message, 400)

class DataNotReadyError(CloudSenseAPIError):
    def __init__(self, message: str):
        super().__init__("DATA_NOT_READY", message, 503)

class InsufficientHistoryError(CloudSenseAPIError):
    def __init__(self, message: str):
        super().__init__("INSUFFICIENT_HISTORY", message, 503)

class ModelError(CloudSenseAPIError):
    def __init__(self, message: str):
        super().__init__("MODEL_ERROR", message, 500)

async def cloudsense_exception_handler(request: Request, exc: CloudSenseAPIError):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error_code, message=exc.message).model_dump()
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="INVALID_REQUEST",
            message="Request validation failed. Please check your inputs."
        ).model_dump()
    )

async def general_exception_handler(request: Request, exc: Exception):
    import logging
    logging.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="INTERNAL_ERROR",
            message="An unexpected internal error occurred."
        ).model_dump()
    )
