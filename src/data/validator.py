import os
import yaml

def load_config(config_path: str) -> dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def validate_raw_file(filepath: str, year: int, dataset_type: str, config_path: str = "configs/datasets.yaml") -> bool:
    """
    Validates that a raw GRD file meets the verified dimensional requirements.
    Does NOT modify the file.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
        
    config = load_config(config_path)
    if dataset_type not in config['datasets']:
        raise ValueError(f"Unknown dataset type: {dataset_type}")
        
    dataset_cfg = config['datasets'][dataset_type]['verified']
    
    file_size = os.path.getsize(filepath)
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    expected_size = dataset_cfg['byte_size_leap'] if is_leap else dataset_cfg['byte_size_non_leap']
    
    if file_size != expected_size:
        raise ValueError(f"Validation failed for {filepath}: Expected size {expected_size} for year {year}, got {file_size}")
        
    # File is structurally sound according to verified metadata
    return True
