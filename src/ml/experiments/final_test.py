import lightgbm as lgb
import polars as pl
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_score, recall_score, f1_score, average_precision_score
import shap
import os
import gc

EXTREME_THRESHOLD = 17.9128

def evaluate_predictions(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    bias = np.mean(y_pred - y_true)
    
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

def run_final_test():
    print("=== RUNNING PHASE E: FINAL TEST ===", flush=True)
    
    features = [
        'rf_lag_1', 'rf_lag_2', 'rf_roll7_sum', 'days_since_rain',
        'neighbor_mean_lag1', 'neighbor_max_lag1',
        'tmax_1deg_lag1', 'tmin_1deg_lag1', 'tmax_1deg_roll7', 'diurnal_range_1deg',
        'sin_doy', 'cos_doy'
    ]
    
    print("Loading datasets...", flush=True)
    # Combine Train (recent subset) and Validation to avoid OOM
    train_lazy = pl.scan_parquet("data/ml/train/*.parquet").filter(pl.col("time").dt.year() >= 2018)
    val_lazy = pl.scan_parquet("data/ml/validation/*.parquet")
    combined_lazy = pl.concat([train_lazy, val_lazy])
    
    test_df = pl.scan_parquet("data/ml/test/*.parquet").collect()
    
    results = []
    
    shap_horizons = [1, 3, 7]
    
    for h in range(1, 8):
        print(f"\n--- Training and Evaluating Horizon {h} ---", flush=True)
        target_col = f"target_h{h}"
        
        # Load training data for this horizon
        train_h = combined_lazy.select(features + [target_col]).filter(pl.col(target_col).is_not_null()).collect()
        X_train = train_h.select(features).to_pandas()
        y_train = train_h[target_col].to_numpy()
        del train_h
        gc.collect()
        
        # Load testing data
        test_h = test_df.filter(pl.col(target_col).is_not_null())
        X_test = test_h.select(features).to_pandas()
        y_test = test_h[target_col].to_numpy()
        
        # Train Tweedie model
        model = lgb.LGBMRegressor(
            objective='tweedie',
            tweedie_variance_power=1.5,
            n_estimators=100,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        )
        
        # Train on full Train+Val, no early stopping
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        
        res = evaluate_predictions(y_test, y_pred)
        print(f"H{h} MAE: {res['mae']:.4f}, PR-AUC: {res['pr_auc']:.4f}")
        
        row = {'model': 'Tweedie (p=1.5)', 'horizon': h}
        row.update(res)
        results.append(row)
        
        if h in shap_horizons:
            print(f"Extracting SHAP values for H{h}...", flush=True)
            # Sample for SHAP
            X_sample = X_test.sample(n=2000, random_state=42)
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_sample)
            
            # Save SHAP mean absolute values
            shap_df = pd.DataFrame({
                'feature': features,
                'mean_abs_shap': np.abs(shap_values).mean(axis=0)
            }).sort_values('mean_abs_shap', ascending=False)
            
            shap_df.to_csv(f"docs/ml/experiments/shap_h{h}.csv", index=False)
            print(f"Top 3 features for H{h}: {shap_df['feature'].tolist()[:3]}", flush=True)
            
    # Save results
    results_df = pl.DataFrame(results)
    results_df.write_csv("docs/ml/experiments/final_test_results.csv")
    print("\nSaved final test results to docs/ml/experiments/final_test_results.csv", flush=True)

if __name__ == "__main__":
    run_final_test()
