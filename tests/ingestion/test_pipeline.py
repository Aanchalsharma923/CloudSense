import os
import pandas as pd
import xarray as xr
import pytest
from unittest.mock import patch
from src.ingestion.pipeline import IngestionPipeline

@pytest.fixture
def test_dirs(tmp_path):
    dirs = {
        "manifest": str(tmp_path / "manifest.json"),
        "staging": str(tmp_path / "staging"),
        "raw": str(tmp_path / "raw"),
        "state": str(tmp_path / "state"),
        "processed": "data/processed"
    }
    return dirs

def get_pipeline(test_dirs):
    return IngestionPipeline(
        manifest_path=test_dirs["manifest"],
        staging_dir=test_dirs["staging"],
        raw_dir=test_dirs["raw"],
        state_dir=test_dirs["state"],
        processed_dir=test_dirs["processed"]
    )

def test_successful_ingestion(test_dirs):
    pipeline = get_pipeline(test_dirs)
    date = "2021-06-01"
    
    success = pipeline.run_daily_ingestion(date)
    assert success is True
    
    entries = pipeline.manifest_manager.read_manifest()
    assert len(entries) == 3
    for e in entries:
        assert e.observation_date == date
        assert e.processing_status == "PROCESSED"
        
    assert os.path.exists(os.path.join(test_dirs["state"], "rainfall", "2021.nc"))
    assert os.path.exists(os.path.join(test_dirs["state"], "tmax", "2021.nc"))
    assert os.path.exists(os.path.join(test_dirs["state"], "tmin", "2021.nc"))
    
    ds = xr.open_dataset(os.path.join(test_dirs["state"], "rainfall", "2021.nc"))
    assert pd.Timestamp(date) in ds.time.values
    ds.close()

def test_missing_data_rollback(test_dirs):
    pipeline = get_pipeline(test_dirs)
    date = "2099-01-01"
    
    success = pipeline.run_daily_ingestion(date)
    assert success is False
    
    if os.path.exists(test_dirs["staging"]):
        assert len(os.listdir(test_dirs["staging"])) == 0
        
    entries = pipeline.manifest_manager.read_manifest()
    assert len(entries) == 0

def test_idempotent_ingestion(test_dirs):
    pipeline = get_pipeline(test_dirs)
    date = "2021-06-01"
    
    assert pipeline.run_daily_ingestion(date) is True
    
    ds = xr.open_dataset(os.path.join(test_dirs["state"], "rainfall", "2021.nc"))
    ds.load()
    assert len(ds.time) == 1
    ds.close()
    
    assert pipeline.run_daily_ingestion(date) is True
    
    ds = xr.open_dataset(os.path.join(test_dirs["state"], "rainfall", "2021.nc"))
    ds.load()
    assert len(ds.time) == 1
    ds.close()

def test_get_latest_valid_t(test_dirs):
    pipeline = get_pipeline(test_dirs)
    assert pipeline.get_latest_valid_t() is None
    
    pipeline.run_daily_ingestion("2021-06-01")
    assert pipeline.get_latest_valid_t() == "2021-06-01"
    
    pipeline.run_daily_ingestion("2021-06-02")
    assert pipeline.get_latest_valid_t() == "2021-06-02"
