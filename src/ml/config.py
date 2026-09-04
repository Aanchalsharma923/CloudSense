# ML Pipeline Configuration

ML_CONFIG = {
    # Rain occurrence definition (used for days_since_rain)
    'rain_threshold': 0.0,
    
    # Minimum valid neighbors required for spatial calculations (neighbor_mean_lag1, neighbor_max_lag1)
    'minimum_valid_neighbors': 3,
    
    # Horizons to predict
    'target_horizons': [1, 2, 3, 4, 5, 6, 7],
    
    # Years for the full generation
    'all_years': list(range(2000, 2026)),
    
    # Train/Val/Test Splits
    'train_years': list(range(2000, 2019)),
    'val_years': list(range(2019, 2022)),
    'test_years': list(range(2022, 2026)),
    
    # Paths
    'processed_data_dir': 'data/processed',
    'ml_output_base': 'data/ml'
}
