import os
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from src.ingestion.operational_imd_provider import OperationalIMDProvider
import urllib.error

@pytest.fixture
def mock_imd_response():
    # 31x31 float32 array
    arr = np.full((31, 31), 25.0, dtype=np.float32)
    # add a sentinel value
    arr[0, 0] = 99.9
    return arr.tobytes()

@patch("urllib.request.urlopen")
def test_download_tmax_success(mock_urlopen, tmp_path, mock_imd_response):
    # Setup mock
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = mock_imd_response
    mock_urlopen.return_value = mock_resp
    
    provider = OperationalIMDProvider(timeout=2)
    target_path = str(tmp_path / "tmax.nc")
    
    assert provider.download_tmax("2021-06-01", target_path) is True
    assert os.path.exists(target_path)
    
    # Check NetCDF contents
    import xarray as xr
    ds = xr.open_dataset(target_path)
    assert 'tmax' in ds.data_vars
    # 99.9 should be nan
    assert np.isnan(ds['tmax'].values[0, 0, 0])
    assert ds['tmax'].values[0, 1, 1] == 25.0
    ds.close()

@patch("urllib.request.urlopen")
def test_download_invalid_size(mock_urlopen, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"tooshort"
    mock_urlopen.return_value = mock_resp
    
    provider = OperationalIMDProvider(timeout=2)
    target_path = str(tmp_path / "tmax.nc")
    
    assert provider.download_tmax("2021-06-01", target_path) is False
    assert not os.path.exists(target_path)

@patch("urllib.request.urlopen")
def test_download_http_error(mock_urlopen, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status = 404
    mock_urlopen.return_value = mock_resp
    
    provider = OperationalIMDProvider(timeout=2)
    target_path = str(tmp_path / "tmax.nc")
    
    assert provider.download_tmax("2021-06-01", target_path) is False

@patch("urllib.request.urlopen")
def test_download_timeout(mock_urlopen, tmp_path):
    mock_urlopen.side_effect = urllib.error.URLError("timeout")
    
    provider = OperationalIMDProvider(timeout=2)
    target_path = str(tmp_path / "tmax.nc")
    
    assert provider.download_tmax("2021-06-01", target_path) is False
