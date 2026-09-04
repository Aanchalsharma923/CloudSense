import pytest
from fastapi.testclient import TestClient
from src.api.app import app

# Use TestClient with `with` block so lifespan events (loading models, NetCDF) are triggered
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "cloudsense"}

def test_ready_check(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ready", "not_ready"]
    if data["status"] == "ready":
        assert "latest_valid_T" in data

def test_predict_invalid_coordinates_range(client):
    response = client.post("/predict", json={
        "latitude": 95.0,  # Invalid
        "longitude": 72.75
    })
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_REQUEST"

def test_predict_out_of_bounds_grid(client):
    response = client.post("/predict", json={
        "latitude": 10.0,
        "longitude": 10.0, # Somewhere not in India grid
        "base_date": "2023-07-01"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["error"] in ["INVALID_COORDINATES", "LOCATION_UNSUPPORTED"]

def test_predict_ocean_location(client):
    # Arab sea location within the bounding box but over ocean
    response = client.post("/predict", json={
        "latitude": 15.0,
        "longitude": 70.0,
        "base_date": "2023-07-01"
    })
    assert response.status_code == 400
    assert response.json()["error"] == "LOCATION_UNSUPPORTED"

def test_predict_valid_location_real_model(client):
    # Mumbai coordinates
    response = client.post("/predict", json={
        "latitude": 19.25,
        "longitude": 72.75,
        "base_date": "2023-07-01" # Given our test data is 1901-2023
    })
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["base_date_T"] == "2023-07-01"
    
    # Check horizons
    forecasts = data["forecasts"]
    for i in range(1, 8):
        assert f"h{i}" in forecasts
        assert isinstance(forecasts[f"h{i}"], float)
        assert forecasts[f"h{i}"] >= 0.0

    # Check snapped location
    location = data["location"]
    assert location["latitude_snapped"] == 19.25
    assert location["longitude_snapped"] == 72.75
