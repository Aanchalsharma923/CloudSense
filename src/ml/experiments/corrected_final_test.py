import lightgbm as lgb
import polars as pl
import pandas as pd
import numpy as np
import pyarrow as pa
from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_score, recall_score, f1_score, average_precision_score
import os
import gc
import psutil

EXTREME_THRESHOLD = 17.9128

def evaluate_predictions(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    bias = np.mean(y_pred - y_true)
    
    # Rainy cases only Amount
    rainy_mask = y_true > 0
    if np.any(rainy_mask):
        rainy_mae = mean_absolute_error(y_true[rainy_mask], y_pred[rainy_mask])
        rainy_rmse = np.sqrt(mean_squared_error(y_true[rainy_mask], y_pred[rainy_mask]))
        rainy_bias = np.mean(y_pred[rainy_mask] - y_true[rainy_mask])
    else:
        rainy_mae, rainy_rmse, rainy_bias = np.nan, np.nan, np.nan
        
    y_true_occ = (y_true > 0.1).astype(int)
    y_pred_occ_bin = (y_pred > 0.1).astype(int)
    
    if np.any(y_true_occ):
        pr_auc = average_precision_score(y_true_occ, y_pred)
        precision = precision_score(y_true_occ, y_pred_occ_bin, zero_division=0)
        recall = recall_score(y_true_occ, y_pred_occ_bin, zero_division=0)
        f1 = f1_score(y_true_occ, y_pred_occ_bin, zero_division=0)
    else:
        pr_auc, precision, recall, f1 = np.nan, np.nan, np.nan, np.nan
    
    y_true_ext = (y_true > EXTREME_THRESHOLD).astype(int)
    y_pred_ext_bin = (y_pred > EXTREME_THRESHOLD).astype(int)
    
    if np.any(y_true_ext):
        ext_pr_auc = average_precision_score(y_true_ext, y_pred)
        ext_precision = precision_score(y_true_ext, y_pred_ext_bin, zero_division=0)
        ext_recall = recall_score(y_true_ext, y_pred_ext_bin, zero_division=0)
        ext_f1 = f1_score(y_true_ext, y_pred_ext_bin, zero_division=0)
    else:
        ext_pr_auc, ext_precision, ext_recall, ext_f1 = np.nan, np.nan, np.nan, np.nan
        
    return {
        'mae': mae, 'rmse': rmse, 'bias': bias,
        'rainy_mae': rainy_mae, 'rainy_rmse': rainy_rmse, 'rainy_bias': rainy_bias,
        'pr_auc': pr_auc, 'precision': precision, 'recall': recall, 'f1': f1,
        'ext_pr_auc': ext_pr_auc, 'ext_precision': ext_precision, 'ext_recall': ext_recall, 'ext_f1': ext_f1
    }

def print_memory():
    process = psutil.Process(os.getpid())
    print(f"Current Memory Usage: {process.memory_info().rss / 1024**2:.2f} MB")

def run_corrected_final_test():
    print("=== RUNNING PHASE 7.1: CORRECTED FINAL TEST ===", flush=True)
    os.makedirs("docs/ml/experiments", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    features = [
        'rf_lag_1', 'rf_lag_2', 'rf_roll7_sum', 'days_since_rain',
        'neighbor_mean_lag1', 'neighbor_max_lag1',
        'tmax_1deg_lag1', 'tmin_1deg_lag1', 'tmax_1deg_roll7', 'diurnal_range_1deg',
        'sin_doy', 'cos_doy'
    ]
    
    print("Computing Climatology from 2000-2018 Train...", flush=True)
    train_climatology = pl.scan_parquet("data/ml/train/*.parquet").select(['time', 'lat', 'lon', 'target_h1'])
    train_climatology = train_climatology.with_columns(
        (pl.col("time") + pl.duration(days=1)).dt.ordinal_day().alias("doy_h1")
    )
    climatology = train_climatology.group_by(["lat", "lon", "doy_h1"]).agg(
        pl.col("target_h1").mean().alias("clim_rain")
    ).collect(streaming=True)
    
    val_results = []
    test_results = []
    
    for h in range(1, 8):
        print(f"\n--- Training and Evaluating Horizon {h} ---", flush=True)
        target_col = f"target_h{h}"
        
        # 1. LOAD TRAIN USING PYARROW
        print("Loading Train Dataset (2000-2018)...", flush=True)
        train_df = pl.scan_parquet("data/ml/train/*.parquet").select(features + [target_col]).filter(pl.col(target_col).is_not_null()).collect()
        
        total_rows = len(train_df)
        print(f"H{h} Train Valid Target Rows: {total_rows}", flush=True)
        print_memory()
        
        print("Constructing LightGBM Dataset natively via PyArrow...", flush=True)
        X_train_arrow = train_df.select(features).to_arrow()
        y_train_arrow = train_df.select(target_col).to_arrow().column(0)
        
        lgb_train = lgb.Dataset(X_train_arrow, label=y_train_arrow, feature_name=features, free_raw_data=False)
        lgb_train.construct()
        print("LightGBM Dataset built.", flush=True)
        print_memory()
        
        del train_df
        del X_train_arrow
        del y_train_arrow
        gc.collect()
        
        # 2. LOAD VALIDATION
        print("Loading Validation Dataset (2019-2021)...", flush=True)
        val_df = pl.scan_parquet("data/ml/validation/*.parquet").filter(pl.col(target_col).is_not_null()).collect()
        X_val = val_df.select(features).to_pandas()
        y_val = val_df[target_col].to_numpy()
        
        lgb_val = lgb.Dataset(X_val, label=y_val, reference=lgb_train, feature_name=features, free_raw_data=False)
        
        # 3. TRAIN TWEEDIE MODEL
        print(f"Training LightGBM Tweedie for H{h}...", flush=True)
        params = {
            'objective': 'tweedie',
            'tweedie_variance_power': 1.5,
            'learning_rate': 0.1,
            'random_state': 42,
            'n_jobs': -1,
            'verbosity': -1
        }
        
        model = lgb.train(
            params,
            lgb_train,
            num_boost_round=100,
            valid_sets=[lgb_val],
            callbacks=[lgb.early_stopping(stopping_rounds=10)]
        )
        print("Training complete.", flush=True)
        print_memory()
        
        # Evaluate Validation Baselines
        vdf_clim = val_df.with_columns(
            (pl.col("time") + pl.duration(days=h)).dt.ordinal_day().alias("doy_h1")
        )
        vdf_clim = vdf_clim.join(climatology, on=["lat", "lon", "doy_h1"], how="left")
        y_pred_clim = vdf_clim["clim_rain"].fill_null(0.0).to_numpy()
        y_pred_pers = val_df["rf_lag_1"].fill_null(0.0).to_numpy()
        y_pred_rec = (val_df["rf_roll7_sum"] / 7.0).fill_null(0.0).to_numpy()
        
        # Evaluate Validation ML
        y_pred_ml_val = model.predict(X_val)
        
        res_clim_val = evaluate_predictions(y_val, y_pred_clim)
        res_pers_val = evaluate_predictions(y_val, y_pred_pers)
        res_rec_val = evaluate_predictions(y_val, y_pred_rec)
        res_ml_val = evaluate_predictions(y_val, y_pred_ml_val)
        
        for name, res in [("Climatology", res_clim_val), ("Persistence", res_pers_val), ("RecentHistory", res_rec_val), ("LightGBM Tweedie", res_ml_val)]:
            row = {'split': 'validation', 'horizon': h, 'model': name}
            row.update(res)
            val_results.append(row)
            
        print(f"[Validation H{h}] ML MAE: {res_ml_val['mae']:.4f} vs Recent: {res_rec_val['mae']:.4f}")
        
        # 4. FINAL TEST EVALUATION
        print("Loading Final Test Dataset (2022-2025)...", flush=True)
        test_df = pl.scan_parquet("data/ml/test/*.parquet").filter(pl.col(target_col).is_not_null()).collect()
        X_test = test_df.select(features).to_pandas()
        y_test = test_df[target_col].to_numpy()
        
        # Baselines for Test
        tdf_clim = test_df.with_columns(
            (pl.col("time") + pl.duration(days=h)).dt.ordinal_day().alias("doy_h1")
        )
        tdf_clim = tdf_clim.join(climatology, on=["lat", "lon", "doy_h1"], how="left")
        y_pred_clim_test = tdf_clim["clim_rain"].fill_null(0.0).to_numpy()
        y_pred_pers_test = test_df["rf_lag_1"].fill_null(0.0).to_numpy()
        y_pred_rec_test = (test_df["rf_roll7_sum"] / 7.0).fill_null(0.0).to_numpy()
        
        # ML for Test
        y_pred_ml_test = model.predict(X_test)
        
        res_clim_test = evaluate_predictions(y_test, y_pred_clim_test)
        res_pers_test = evaluate_predictions(y_test, y_pred_pers_test)
        res_rec_test = evaluate_predictions(y_test, y_pred_rec_test)
        res_ml_test = evaluate_predictions(y_test, y_pred_ml_test)
        
        for name, res in [("Climatology", res_clim_test), ("Persistence", res_pers_test), ("RecentHistory", res_rec_test), ("LightGBM Tweedie", res_ml_test)]:
            row = {'split': 'test', 'horizon': h, 'model': name}
            row.update(res)
            test_results.append(row)
            
        print(f"[Test H{h}] ML MAE: {res_ml_test['mae']:.4f} vs Recent: {res_rec_test['mae']:.4f}")
        
        # 5. SERIALIZE MODEL
        model_path = f"models/cloudsense_rainfall_h{h}.txt"
        model.save_model(model_path)
        print(f"Saved model artifact: {model_path}")
        
        del lgb_train
        del lgb_val
        del X_val
        del X_test
        del val_df
        del test_df
        gc.collect()

    # Save results
    pl.DataFrame(val_results).write_csv("docs/ml/experiments/corrected_validation_results.csv")
    pl.DataFrame(test_results).write_csv("docs/ml/experiments/corrected_test_results.csv")
    print("\nSaved all evaluation results.")

if __name__ == "__main__":
    run_corrected_final_test()
