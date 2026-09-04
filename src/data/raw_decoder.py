import numpy as np
import os
import yaml

def load_dataset_config(dataset_type: str, config_path: str = "configs/datasets.yaml") -> dict:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    if dataset_type not in config['datasets']:
        raise ValueError(f"Unknown dataset type: {dataset_type}")
    return config['datasets'][dataset_type]

def decode_raw_grd(filepath: str, year: int, dataset_type: str, config_path: str = "configs/datasets.yaml") -> np.ndarray:
    """
    Decodes the raw contiguous Fortran GRD binary file into a 3D numpy array.
    Does NOT mask missing values (leaves them raw).
    Shape output: (days, lat, lon)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
        
    config = load_dataset_config(dataset_type, config_path)
    verified = config['verified']
    
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    days = 366 if is_leap else 365
    
    expected_size = verified['byte_size_leap'] if is_leap else verified['byte_size_non_leap']
    file_size = os.path.getsize(filepath)
    
    if file_size != expected_size:
        raise ValueError(f"Corrupted or truncated file: Expected {expected_size} bytes, got {file_size}")
    
    # Read raw as float32 little endian (verified)
    endianness = verified['endianness']
    if endianness != 'little':
        raise NotImplementedError(f"Unsupported endianness: {endianness}")
        
    raw_array = np.fromfile(filepath, dtype='<f4')
    
    grid_x = verified['grid_x']
    grid_y = verified['grid_y']
    
    # Reshape: IMD uses X (Lon) then Y (Lat) ordering for direct access
    # So the flat array varies: Lon fastest, then Lat, then Day.
    # In C-contiguous numpy, that means shape = (days, grid_y, grid_x)
    # where grid_y is Lat, grid_x is Lon.
    expected_values = days * grid_y * grid_x
    if raw_array.size != expected_values:
        raise ValueError(f"Decoded size mismatch: Expected {expected_values} floats, got {raw_array.size}")
        
    tensor_3d = raw_array.reshape((days, grid_y, grid_x))
    
    return tensor_3d
