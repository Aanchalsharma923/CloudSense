import os
import pytest
import datetime
from unittest.mock import patch, MagicMock
from src.ingestion.operational_imd_rainfall_provider import OperationalIMDRainfallProvider

@pytest.fixture
def provider():
    return OperationalIMDRainfallProvider(timeout=2)

def test_operational_rainfall_provider_success(provider, tmp_path):
    date = "2024-05-01"
    target = tmp_path / "rain.nc"
    
    # Mock valid payload of 69660 bytes
    dummy_payload = b'\x00' * 69660
    
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = dummy_payload
    
    with patch('urllib.request.urlopen', return_value=mock_resp):
        res = provider.download_rainfall(date, str(target))
        assert res is True
        assert target.exists()

def test_operational_rainfall_provider_0byte_payload(provider, tmp_path):
    date = "2024-05-02"
    target = tmp_path / "rain2.nc"
    
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'' # 0-byte
    
    with patch('urllib.request.urlopen', return_value=mock_resp):
        res = provider.download_rainfall(date, str(target))
        # Should return False gracefully
        assert res is False
        assert not target.exists()

def test_operational_rainfall_provider_http_error(provider, tmp_path):
    date = "2024-05-03"
    target = tmp_path / "rain3.nc"
    
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.read.return_value = b'Server Error'
    
    with patch('urllib.request.urlopen', return_value=mock_resp):
        # We also mock time.sleep to not wait during tests
        with patch('time.sleep', return_value=None):
            res = provider.download_rainfall(date, str(target))
            assert res is False
            assert not target.exists()
