import os
import datetime
import uuid
import pandas as pd
from typing import List, Optional
from src.ingestion.models import ManifestEntry
from src.ingestion.manifest import ManifestManager
from src.ingestion.source import MockIMDProvider
from src.ingestion.operational_imd_provider import OperationalIMDProvider
from src.ingestion.operational_imd_rainfall_provider import OperationalIMDRainfallProvider
from src.ingestion.validator import IMDValidator
from src.ingestion.state_store import StateStore

class IngestionPipeline:
    def __init__(self, manifest_path="data/raw/manifest.json", 
                 staging_dir="data/staging", raw_dir="data/raw", 
                 state_dir="data/state", processed_dir="data/processed",
                 rainfall_provider=None, temp_provider=None):
        self.manifest_manager = ManifestManager(manifest_path=manifest_path)
        self.rainfall_provider = rainfall_provider or OperationalIMDRainfallProvider()
        self.temp_provider = temp_provider or OperationalIMDProvider()
        self.validator = IMDValidator()
        self.state_store = StateStore(state_dir=state_dir, processed_dir=processed_dir)
        self.staging_dir = staging_dir
        self.raw_dir = raw_dir
        
    def _ingest_variable(self, variable: str, date: str, download_func, validate_func) -> Optional[str]:
        """
        Downloads to staging, validates, and returns the path to the valid staging file.
        If any step fails, returns None.
        """
        staging_dir = self.staging_dir
        os.makedirs(staging_dir, exist_ok=True)
        staging_path = os.path.join(staging_dir, f"{variable}_{date}_{uuid.uuid4().hex[:8]}.nc")
        
        # Download
        success = download_func(date, staging_path)
        if not success:
            return None
            
        # Validate
        val_result = validate_func(staging_path)
        if not val_result.is_valid:
            if os.path.exists(staging_path):
                os.remove(staging_path)
            return None
            
        return staging_path

    def run_daily_ingestion(self, date: str) -> bool:
        """
        Attempts to ingest all required datasets for `date`.
        Implements cross-variable atomic commit.
        Returns True if all committed successfully, False otherwise.
        """
        # Step 1: Staging & Validation
        rain_path = self._ingest_variable(
            "rainfall", date, self.rainfall_provider.download_rainfall, self.validator.validate_rainfall)
            
        tmax_path = self._ingest_variable(
            "tmax", date, self.temp_provider.download_tmax, lambda p: self.validator.validate_temperature(p, 'tmax'))
            
        tmin_path = self._ingest_variable(
            "tmin", date, self.temp_provider.download_tmin, lambda p: self.validator.validate_temperature(p, 'tmin'))
            
        # Step 2: Atomic cross-variable check
        if not (rain_path and tmax_path and tmin_path):
            # Rollback: Clean up any successful partial downloads
            for p in filter(None, [rain_path, tmax_path, tmin_path]):
                if os.path.exists(p):
                    os.remove(p)
            return False
            
        # Step 3: Raw Persistence & State Commit
        # Move staging files to raw storage
        raw_dir = self.raw_dir
        timestamp = datetime.datetime.utcnow().isoformat()
        
        for var, p in [('rainfall', rain_path), ('tmax', tmax_path), ('tmin', tmin_path)]:
            raw_var_dir = os.path.join(raw_dir, var)
            os.makedirs(raw_var_dir, exist_ok=True)
            raw_path = os.path.join(raw_var_dir, f"{date}.nc")
            
            # Move from staging to raw
            os.replace(p, raw_path)
            
            # Commit to state store
            self.state_store.append_daily_slice(var, raw_path)
            
            # Write Manifest Entry
            entry = ManifestEntry(
                dataset=var,
                observation_date=date,
                source="MockIMD",
                source_identifier=raw_path,
                checksum="SKIP",  # Simulated checksum
                file_size=os.path.getsize(raw_path),
                local_path=raw_path,
                download_timestamp=timestamp,
                validation_status="VALID",
                processing_status="PROCESSED"
            )
            self.manifest_manager.add_entry(entry)
            
        return True

    def get_latest_valid_t(self) -> Optional[str]:
        """
        Determines the latest date where ALL required variables are PROCESSED.
        """
        # Scan manifest for rainfall, find the latest date where all 3 exist.
        entries = self.manifest_manager.read_manifest()
        
        dates = set(e.observation_date for e in entries if e.processing_status == "PROCESSED")
        valid_dates = []
        
        for d in dates:
            has_rain = self.manifest_manager.get_latest_successful("rainfall", d) is not None
            has_tmax = self.manifest_manager.get_latest_successful("tmax", d) is not None
            has_tmin = self.manifest_manager.get_latest_successful("tmin", d) is not None
            
            if has_rain and has_tmax and has_tmin:
                valid_dates.append(pd.Timestamp(d))
                
        if not valid_dates:
            return None
            
        return max(valid_dates).strftime("%Y-%m-%d")

