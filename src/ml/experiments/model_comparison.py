import lightgbm as lgb
import polars as pl
import numpy as np
from sklearn.metrics import mean_absolute_error, average_precision_score, mean_squared_error
import os
import gc

def run_model_comparison():
    print("=== RUNNING PHASE C: TWEEDIE VS HURDLE (HORIZON 1) ===", flush=True)
    
    features = [
        'rf_lag_1', 'rf_lag_2', 'rf_roll7_sum', 'days_since_rain',
        'neighbor_mean_lag1', 'neighbor_max_lag1',
        'tmax_1deg_lag1', 'tmin_1deg_lag1', 'tmax_1deg_roll7', 'diurnal_range_1deg',
        'sin_doy', 'cos_doy'
    ]
    target_col = 'target_h1'
    
    print("Loading data...", flush=True)
    # Using scan_parquet and collect to be memory efficient if possible
    train_df = pl.scan_parquet("data/ml/train/*.parquet").filter(pl.col("time").dt.year() >= 2018).select(features + [target_col]).filter(pl.col(target_col).is_not_null()).collect()
    val_df = pl.scan_parquet("data/ml/validation/*.parquet").select(features + [target_col]).filter(pl.col(target_col).is_not_null()).collect()
    
    X_train = train_df.select(features).to_pandas()
    y_train = train_df[target_col].to_numpy()
    
    X_val = val_df.select(features).to_pandas()
    y_val = val_df[target_col].to_numpy()
    
    del train_df, val_df
    gc.collect()
    
    results = []
    
    # 1. Single-Stage Tweedie
    print("Training Single-Stage Tweedie...", flush=True)
    model_tweedie = lgb.LGBMRegressor(
        objective='tweedie',
        tweedie_variance_power=1.5,
        n_estimators=100,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1
    )
    model_tweedie.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(10, verbose=False)])
    
    y_pred_tweedie = model_tweedie.predict(X_val)
    # Tweedie predicts amount directly. We can use y_pred > thresh for classification, but we evaluate on MAE and PR-AUC.
    mae_tweedie = mean_absolute_error(y_val, y_pred_tweedie)
    bias_tweedie = np.mean(y_pred_tweedie - y_val)
    # Estimate PR-AUC using prediction magnitude as probability proxy
    pr_auc_tweedie = average_precision_score((y_val > 0.1).astype(int), y_pred_tweedie)
    
    results.append({
        'model': 'Tweedie (p=1.5)',
        'mae': mae_tweedie,
        'bias': bias_tweedie,
        'pr_auc_occ': pr_auc_tweedie
    })
    print(f"Tweedie MAE: {mae_tweedie:.4f}, Bias: {bias_tweedie:.4f}, PR-AUC(>0.1): {pr_auc_tweedie:.4f}", flush=True)
    
    # 2. Hurdle Stage 1 (Occurrence > 0.1 mm)
    print("Training Hurdle Stage 1 (Occurrence)...", flush=True)
    y_train_occ = (y_train > 0.1).astype(int)
    y_val_occ = (y_val > 0.1).astype(int)
    
    model_occ = lgb.LGBMClassifier(
        n_estimators=100,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1
    )
    model_occ.fit(X_train, y_train_occ, eval_set=[(X_val, y_val_occ)], eval_metric='logloss', callbacks=[lgb.early_stopping(10, verbose=False)])
    y_pred_prob = model_occ.predict_proba(X_val)[:, 1]
    
    pr_auc_hurdle = average_precision_score(y_val_occ, y_pred_prob)
    
    # Hurdle Stage 2 Data (Train only on y > 0.1)
    mask_train = y_train > 0.1
    X_train_amt = X_train[mask_train]
    y_train_amt = y_train[mask_train]
    
    mask_val = y_val > 0.1
    X_val_amt = X_val[mask_val]
    y_val_amt = y_val[mask_val]
    
    # 3. Hurdle Stage 2 (Raw Amount)
    print("Training Hurdle Stage 2 (Raw Amount L2)...", flush=True)
    model_amt_raw = lgb.LGBMRegressor(
        objective='regression',
        n_estimators=100,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1
    )
    model_amt_raw.fit(X_train_amt, y_train_amt, eval_set=[(X_val_amt, y_val_amt)], callbacks=[lgb.early_stopping(10, verbose=False)])
    y_pred_amt_raw = model_amt_raw.predict(X_val)
    
    y_pred_hurdle_raw = y_pred_prob * y_pred_amt_raw
    mae_hurdle_raw = mean_absolute_error(y_val, y_pred_hurdle_raw)
    bias_hurdle_raw = np.mean(y_pred_hurdle_raw - y_val)
    
    results.append({
        'model': 'Hurdle (Raw Amount L2)',
        'mae': mae_hurdle_raw,
        'bias': bias_hurdle_raw,
        'pr_auc_occ': pr_auc_hurdle
    })
    print(f"Hurdle (Raw Amount) MAE: {mae_hurdle_raw:.4f}, Bias: {bias_hurdle_raw:.4f}", flush=True)
    
    # 4. Hurdle Stage 2 (log1p Amount)
    print("Training Hurdle Stage 2 (log1p Amount L2)...", flush=True)
    y_train_log = np.log1p(y_train_amt)
    y_val_log = np.log1p(y_val_amt)
    
    model_amt_log = lgb.LGBMRegressor(
        objective='regression',
        n_estimators=100,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1
    )
    model_amt_log.fit(X_train_amt, y_train_log, eval_set=[(X_val_amt, y_val_log)], callbacks=[lgb.early_stopping(10, verbose=False)])
    y_pred_log = model_amt_log.predict(X_val)
    
    # Reconstruction: P * (exp(E[log1p(y)]) - 1)
    y_pred_amt_exp = np.expm1(y_pred_log)
    y_pred_hurdle_log = y_pred_prob * y_pred_amt_exp
    mae_hurdle_log = mean_absolute_error(y_val, y_pred_hurdle_log)
    bias_hurdle_log = np.mean(y_pred_hurdle_log - y_val)
    
    results.append({
        'model': 'Hurdle (log1p Amount L2)',
        'mae': mae_hurdle_log,
        'bias': bias_hurdle_log,
        'pr_auc_occ': pr_auc_hurdle
    })
    print(f"Hurdle (log1p Amount) MAE: {mae_hurdle_log:.4f}, Bias: {bias_hurdle_log:.4f}", flush=True)
    
    results_df = pl.DataFrame(results)
    results_df.write_csv("docs/ml/experiments/model_comparison_results.csv")
    print("\nSaved model comparison results to docs/ml/experiments/model_comparison_results.csv", flush=True)

if __name__ == "__main__":
    run_model_comparison()
