import pytest
from src.features.grid_mapper import GridMapper

@pytest.fixture(scope="module")
def mapper():
    return GridMapper(
        rainfall_nc_path="data/processed/rainfall/2023.nc",
        tmax_nc_path="data/processed/max_temperature/2023.nc"
    )

def test_valid_interior_cell(mapper):
    # Somewhere in central India
    # Let's say Lat 20.0, Lon 78.0
    slat, slon, _, _ = mapper.map_to_rainfall_grid(20.0, 78.0)
    assert slat == 20.0
    assert slon == 78.0

def test_rounding_nearest(mapper):
    # 20.124 should snap to 20.0
    # 20.126 should snap to 20.25
    slat1, _, _, _ = mapper.map_to_rainfall_grid(20.124, 78.0)
    assert slat1 == 20.0
    
    slat2, _, _, _ = mapper.map_to_rainfall_grid(20.126, 78.0)
    assert slat2 == 20.25

def test_temperature_grid_snapping(mapper):
    # Temp is on 1 degree boundary
    slat, slon, _, _ = mapper.map_to_temperature_grid(20.25, 78.25)
    # Nearest to 20.25 is 20.5
    # Nearest to 78.25 is 78.5
    assert slat == 20.5
    assert slon == 78.5
    
def test_out_of_bounds_raises(mapper):
    with pytest.raises(ValueError):
        mapper.map_to_rainfall_grid(5.0, 78.0)
    with pytest.raises(ValueError):
        mapper.map_to_rainfall_grid(40.0, 78.0)
    with pytest.raises(ValueError):
        mapper.map_to_rainfall_grid(20.0, 60.0)
    with pytest.raises(ValueError):
        mapper.map_to_rainfall_grid(20.0, 110.0)

def test_ocean_cell_raises(mapper):
    # Lat 10.0, Lon 90.0 is in the Bay of Bengal
    with pytest.raises(ValueError, match="invalid/ocean cell"):
        mapper.map_to_rainfall_grid(10.0, 90.0)
