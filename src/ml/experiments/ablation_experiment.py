import lightgbm as lgb
import polars as pl
import numpy as np
from sklearn.metrics import mean_absolute_error, average_precision_score
import os

def run_ablation():
    print("=== RUNNING PHASE D: ABLATION EXPERIMENT (HORIZON 1) ===")
    
    # Base Features
    base_features = [
        'rf_lag_1', 'rf_lag_2', 'rf_roll7_sum', 'days_since_rain',
        'neighbor_mean_lag1', 'neighbor_max_lag1',
        'tmax_1deg_lag1', 'tmin_1deg_lag1', 'tmax_1deg_roll7', 'diurnal_range_1deg',
        'sin_doy', 'cos_doy'
    ]
    
    spatial_features = ['neighbor_mean_lag1', 'neighbor_max_lag1']
    temp_features = ['tmax_1deg_lag1', 'tmin_1deg_lag1', 'tmax_1deg_roll7', 'diurnal_range_1deg']
    temporal_features = ['sin_doy', 'cos_doy']
    
    target_col = 'target_h1'
    
    print("Loading data...")
    # Using scan_parquet and filter to avoid OOM on Windows machine
    train_df = pl.scan_parquet("data/ml/train/*.parquet").filter(pl.col("time").dt.year() >= 2018).select(base_features + [target_col]).filter(pl.col(target_col).is_not_null()).collect()
    val_df = pl.scan_parquet("data/ml/validation/*.parquet").select(base_features + [target_col]).filter(pl.col(target_col).is_not_null()).collect()
    
    experiments = [
        ("All Features", base_features),
        ("No Spatial", [f for f in base_features if f not in spatial_features]),
        ("No Temperature", [f for f in base_features if f not in temp_features]),
        ("No Temporal", [f for f in base_features if f not in temporal_features])
    ]
    
    results = []
    
    for name, features in experiments:
        print(f"\n--- Training {name} ---")
        X_train = train_df.select(features).to_pandas()
        y_train = train_df[target_col].to_numpy()
        
        X_val = val_df.select(features).to_pandas()
        y_val = val_df[target_col].to_numpy()
        
        model = lgb.LGBMRegressor(
            objective='tweedie',
            tweedie_variance_power=1.5,
            n_estimators=100,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        )
        
        # Suppress deprecation warnings by using early_stopping callback
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(10, verbose=False)])
        
        y_pred = model.predict(X_val)
        
        mae = mean_absolute_error(y_val, y_pred)
        bias = np.mean(y_pred - y_val)
        pr_auc_occ = average_precision_score((y_val > 0.1).astype(int), y_pred)
        
        print(f"Results [{name}]: MAE={mae:.4f}, Bias={bias:.4f}, PR-AUC={pr_auc_occ:.4f}")
        
        results.append({
            'ablation_group': name,
            'mae': mae,
            'bias': bias,
            'pr_auc_occ': pr_auc_occ
        })
        
    results_df = pl.DataFrame(results)
    results_df.write_csv("docs/ml/experiments/ablation_results.csv")
    print("\nSaved ablation results to docs/ml/experiments/ablation_results.csv")

if __name__ == "__main__":
    run_ablation()
