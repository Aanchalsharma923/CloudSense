from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ManifestEntry(BaseModel):
    dataset: str
    observation_date: str  # YYYY-MM-DD
    source: str
    source_identifier: str
    checksum: str
    file_size: int
    local_path: str
    download_timestamp: str
    validation_status: str
    processing_status: str
    error_message: Optional[str] = None

class ValidationResult(BaseModel):
    is_valid: bool
    error_message: Optional[str] = None
