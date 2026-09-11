import os
import pytest
import datetime
import urllib.request
from unittest.mock import patch, MagicMock
import pandas as pd
import xarray as xr
import numpy as np

from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.state_store import StateStore
from src.features.feature_builder import ProductionFeatureBuilder
from src.features.grid_mapper import GridMapper
from src.features.providers import StateStoreProvider
from src.ingestion.operational_imd_provider import OperationalIMDProvider
from src.api.routes.health import readiness_check

@pytest.fixture
def test_dirs(tmp_path):
    dirs = {
        'raw': tmp_path / "raw",
        'staging': tmp_path / "staging",
        'state': tmp_path / "state",
        'processed': tmp_path / "processed",
        'manifest': tmp_path / "raw" / "manifest.json"
    }
    for d in dirs.values():
        if not str(d).endswith('.json'):
            d.mkdir(parents=True, exist_ok=True)
    return dirs

from src.ingestion.source import MockIMDProvider

@pytest.fixture
def mock_pipeline(test_dirs):
    mock_rain = MockIMDProvider(historical_archive_dir=str(test_dirs['processed']))
    pipeline = IngestionPipeline(
        manifest_path=str(test_dirs['manifest']),
        staging_dir=str(test_dirs['staging']),
        raw_dir=str(test_dirs['raw']),
        state_dir=str(test_dirs['state']),
        processed_dir=str(test_dirs['processed']),
        rainfall_provider=mock_rain
    )
    return pipeline

def create_dummy_netcdf(path, var_name, date, value, lats=None, lons=None):
    if var_name == 'rainfall':
        if lats is None: lats = np.arange(129, dtype=np.float32)
        if lons is None: lons = np.arange(135, dtype=np.float32)
    else:
        if lats is None: lats = np.arange(7.5, 38.5, 1.0)
        if lons is None: lons = np.arange(67.5, 98.5, 1.0)
    dt = pd.Timestamp(date)
    arr_2d = np.full((len(lats), len(lons)), value, dtype=np.float32)
    ds = xr.Dataset(
        data_vars={var_name: (('time', 'lat', 'lon'), arr_2d[np.newaxis, :, :])},
        coords={'time': [dt], 'lat': lats, 'lon': lons}
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ds.to_netcdf(path)
    return path

def mock_download_success(var_name, val):
    def mock_download(date, target_path):
        create_dummy_netcdf(target_path, var_name, date, val)
        return True
    return mock_download

def mock_download_failure(*args, **kwargs):
    return False

# 1. Latest Complete Date Validation
def test_latest_complete_date_validation(mock_pipeline):
    date = "2024-05-01"
    
    # Rainfall fails
    mock_pipeline.rainfall_provider.download_rainfall = mock_download_failure
    mock_pipeline.temp_provider.download_tmax = mock_download_success('tmax', 35.0)
    mock_pipeline.temp_provider.download_tmin = mock_download_success('tmin', 25.0)
    assert mock_pipeline.run_daily_ingestion(date) is False
    assert mock_pipeline.get_latest_valid_t() is None

    # Tmax fails
    mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', 10.0)
    mock_pipeline.temp_provider.download_tmax = mock_download_failure
    mock_pipeline.temp_provider.download_tmin = mock_download_success('tmin', 25.0)
    assert mock_pipeline.run_daily_ingestion(date) is False
    assert mock_pipeline.get_latest_valid_t() is None

    # All succeed
    mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', 10.0)
    mock_pipeline.temp_provider.download_tmax = mock_download_success('tmax', 35.0)
    mock_pipeline.temp_provider.download_tmin = mock_download_success('tmin', 25.0)
    assert mock_pipeline.run_daily_ingestion(date) is True
    assert mock_pipeline.get_latest_valid_t() == date

# 2. Operational Publication Delay (Partial/Failed Transaction)
def test_partial_transaction_rollback(mock_pipeline, test_dirs):
    date = "2024-05-02"
    # Tmin fails
    mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', 10.0)
    mock_pipeline.temp_provider.download_tmax = mock_download_success('tmax', 35.0)
    mock_pipeline.temp_provider.download_tmin = mock_download_failure
    
    assert mock_pipeline.run_daily_ingestion(date) is False
    
    # Check that staging is empty (cleaned up)
    staging_files = os.listdir(test_dirs['staging'])
    assert len(staging_files) == 0
    
    # Check that state store does not have 2024 data
    assert not os.path.exists(os.path.join(test_dirs['state'], 'rainfall', '2024.nc'))
    assert mock_pipeline.get_latest_valid_t() is None

# 3. Duplicate Ingestion
def test_duplicate_ingestion(mock_pipeline, test_dirs):
    date = "2024-05-03"
    mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', 10.0)
    mock_pipeline.temp_provider.download_tmax = mock_download_success('tmax', 35.0)
    mock_pipeline.temp_provider.download_tmin = mock_download_success('tmin', 25.0)
    
    # First ingest
    assert mock_pipeline.run_daily_ingestion(date) is True
    
    # Verify state
    ds = xr.open_dataset(os.path.join(test_dirs['state'], 'rainfall', '2024.nc'))
    assert len(ds.time) == 1
    ds.close()
    
    # Second ingest
    mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', 20.0) # change value to track
    assert mock_pipeline.run_daily_ingestion(date) is True
    
    # Verify it gracefully overwrote without duplicate times
    ds2 = xr.open_dataset(os.path.join(test_dirs['state'], 'rainfall', '2024.nc'))
    assert len(ds2.time) == 1
    assert float(ds2['rainfall'].sel(time=date).isel(lat=0, lon=0).values) == 20.0
    ds2.close()

# 4. Historical -> Operational Transition & Temperature Provenance
def test_historical_operational_transition(mock_pipeline, test_dirs):
    # Create historical data for 2024-04-24 to 2024-04-29 (T-7 to T-2)
    # Tmax will be 30.0 for 6 days
    # At T-1, we will mock Operational ingestion of Tmax = 50.0 to prove provenance.
    dates = pd.date_range("2024-04-24", "2024-04-29")
    for d in dates:
        d_str = d.strftime("%Y-%m-%d")
        mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', 5.0)
        mock_pipeline.temp_provider.download_tmax = mock_download_success('tmax', 30.0)
        mock_pipeline.temp_provider.download_tmin = mock_download_success('tmin', 20.0)
        mock_pipeline.run_daily_ingestion(d_str)

    # Now explicitly move them to "processed" to simulate historical archive
    for var, vdir in [('rainfall', 'rainfall'), ('tmax', 'max_temperature'), ('tmin', 'min_temperature')]:
        src = os.path.join(test_dirs['state'], var, '2024.nc')
        dst_dir = os.path.join(test_dirs['processed'], vdir)
        os.makedirs(dst_dir, exist_ok=True)
        os.replace(src, os.path.join(dst_dir, '2024.nc'))

    # Clean manifest/state to pretend starting fresh for operational
    mock_pipeline.state_store = StateStore(str(test_dirs['state']), str(test_dirs['processed']))

    # T-1 Operational Ingest: Tmax = 50.0
    date_t_minus_1 = "2024-04-30"
    mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', 10.0)
    mock_pipeline.temp_provider.download_tmax = mock_download_success('tmax', 50.0)
    mock_pipeline.temp_provider.download_tmin = mock_download_success('tmin', 25.0)
    mock_pipeline.run_daily_ingestion(date_t_minus_1)
    
    # Build features for date_t_minus_1
    provider = StateStoreProvider(state_store=mock_pipeline.state_store)
    
    # Create a dummy GridMapper that just returns idx=0
    class DummyGridMapper:
        def map_to_rainfall_grid(self, lat, lon): return lat, lon, 0, 0
        def map_to_temperature_grid(self, lat, lon): return lat, lon, 0, 0
        
    builder = ProductionFeatureBuilder(DummyGridMapper(), provider)
    features = builder.build(20.0, 80.0, date_t_minus_1)
    
    # Provenance check: tmax_1deg_lag1 for prediction date T should be 50.0
    assert features.tmax_1deg_lag1 == 50.0
    
    # tmax_1deg_roll7 should average T-7 to T-1
    # T-7 to T-2: 30.0 (6 days)
    # T-1: 50.0
    # Total: (30*6 + 50) / 7 = 230 / 7 = 32.857
    assert np.isclose(features.tmax_1deg_roll7, 230/7)
    
    # days_since_rain: Rainfall was 5.0 (T-7 to T-2), 10.0 (T-1). 
    # Both > 0, so days_since_rain should be 0.
    assert features.days_since_rain == 0.0

# 5. Days Since Rain Semantics (Cross-year)
def test_days_since_rain_cross_year(mock_pipeline, test_dirs):
    # T = 2024-01-02
    # Rain at 2023-12-30 (T-3)
    # 2023-12-31 (T-2) = 0.0
    # 2024-01-01 (T-1) = 0.0
    # 2024-01-02 (T) = 0.0
    # days_since_rain should be 3
    
    # Historical 2023
    dates_2023 = pd.date_range("2023-12-25", "2023-12-31")
    for i, d in enumerate(dates_2023):
        rf = 10.0 if d.strftime("%Y-%m-%d") == "2023-12-30" else 0.0
        mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', rf)
        mock_pipeline.temp_provider.download_tmax = mock_download_success('tmax', 30.0)
        mock_pipeline.temp_provider.download_tmin = mock_download_success('tmin', 20.0)
        mock_pipeline.run_daily_ingestion(d.strftime("%Y-%m-%d"))
        
    for var, vdir in [('rainfall', 'rainfall'), ('tmax', 'max_temperature'), ('tmin', 'min_temperature')]:
        src = os.path.join(test_dirs['state'], var, '2023.nc')
        dst_dir = os.path.join(test_dirs['processed'], vdir)
        os.makedirs(dst_dir, exist_ok=True)
        os.replace(src, os.path.join(dst_dir, '2023.nc'))
        
    # Operational 2024
    dates_2024 = ["2024-01-01", "2024-01-02"]
    for d in dates_2024:
        mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', 0.0)
        mock_pipeline.temp_provider.download_tmax = mock_download_success('tmax', 30.0)
        mock_pipeline.temp_provider.download_tmin = mock_download_success('tmin', 20.0)
        mock_pipeline.run_daily_ingestion(d)
        
    provider = StateStoreProvider(state_store=mock_pipeline.state_store)
    
    class DummyGridMapper:
        def map_to_rainfall_grid(self, lat, lon): return lat, lon, 0, 0
        def map_to_temperature_grid(self, lat, lon): return lat, lon, 0, 0
        
    builder = ProductionFeatureBuilder(DummyGridMapper(), provider)
    features = builder.build(20.0, 80.0, "2024-01-02")
    
    assert features.days_since_rain == 3.0

import asyncio

# 6. API Readiness Test
def test_api_readiness(mock_pipeline):
    # Empty state -> Not Ready
    res = asyncio.run(readiness_check(pipeline=mock_pipeline))
    assert res.status == "not_ready"
    
    # Ingest partial -> Not Ready
    date = "2024-05-01"
    mock_pipeline.rainfall_provider.download_rainfall = mock_download_success('rainfall', 10.0)
    mock_pipeline.temp_provider.download_tmax = mock_download_success('tmax', 30.0)
    mock_pipeline.temp_provider.download_tmin = mock_download_failure
    mock_pipeline.run_daily_ingestion(date)
    
    res2 = asyncio.run(readiness_check(pipeline=mock_pipeline))
    assert res2.status == "not_ready"
    
    # Complete state -> Ready
    mock_pipeline.temp_provider.download_tmin = mock_download_success('tmin', 20.0)
    mock_pipeline.run_daily_ingestion(date)
    
    res3 = asyncio.run(readiness_check(pipeline=mock_pipeline))
    assert res3.status == "ready"
    assert res3.latest_valid_T == date
