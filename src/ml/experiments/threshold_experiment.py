import lightgbm as lgb
import polars as pl
import numpy as np
from sklearn.metrics import average_precision_score, precision_score, recall_score, f1_score
import os

def evaluate_threshold(y_true, y_pred_prob, threshold):
    # Determine the actual true occurrences based on the given threshold
    y_true_occ = (y_true > threshold).astype(int)
    
    # Check if there are any positive samples
    if np.sum(y_true_occ) == 0:
        return {'pr_auc': np.nan, 'precision': np.nan, 'recall': np.nan, 'f1': np.nan}
        
    pr_auc = average_precision_score(y_true_occ, y_pred_prob)
    
    # Binarize predictions based on 0.5 default prob threshold
    y_pred_bin = (y_pred_prob >= 0.5).astype(int)
    
    precision = precision_score(y_true_occ, y_pred_bin, zero_division=0)
    recall = recall_score(y_true_occ, y_pred_bin, zero_division=0)
    f1 = f1_score(y_true_occ, y_pred_bin, zero_division=0)
    
    return {'pr_auc': pr_auc, 'precision': precision, 'recall': recall, 'f1': f1}

def run_threshold_experiment():
    print("=== RUNNING PHASE B: OCCURRENCE THRESHOLD EXPERIMENT ===")
    
    # V1 Features
    features = [
        'rf_lag_1', 'rf_lag_2', 'rf_roll7_sum', 'days_since_rain',
        'neighbor_mean_lag1', 'neighbor_max_lag1',
        'tmax_1deg_lag1', 'tmin_1deg_lag1', 'tmax_1deg_roll7', 'diurnal_range_1deg',
        'sin_doy', 'cos_doy'
    ]
    
    print("Loading data...")
    train_df = pl.scan_parquet("data/ml/train/*.parquet").filter(pl.col("time").dt.year() >= 2018).collect()
    val_df = pl.read_parquet("data/ml/validation/*.parquet")
    
    thresholds = [0.0, 0.1, 1.0]
    results = []
    
    # We will test this on Horizon 1 as the representative horizon for threshold selection
    target_col = 'target_h1'
    
    # Drop NaNs
    train_df = train_df.filter(pl.col(target_col).is_not_null())
    val_df = val_df.filter(pl.col(target_col).is_not_null())
    
    X_train = train_df.select(features).to_pandas()
    y_train = train_df[target_col].to_numpy()
    
    X_val = val_df.select(features).to_pandas()
    y_val = val_df[target_col].to_numpy()
    
    for thresh in thresholds:
        print(f"\n--- Testing Threshold > {thresh} mm ---")
        
        y_train_bin = (y_train > thresh).astype(int)
        y_val_bin = (y_val > thresh).astype(int)
        
        # LightGBM Classifier
        clf = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        )
        
        print("Training LightGBM Classifier...")
        # Since LightGBM logs a lot, use callbacks to handle early stopping properly
        clf.fit(X_train, y_train_bin, 
                eval_set=[(X_val, y_val_bin)], 
                eval_metric='logloss',
                callbacks=[lgb.early_stopping(stopping_rounds=10, verbose=False)])
        
        print("Evaluating...")
        y_val_pred_prob = clf.predict_proba(X_val)[:, 1]
        
        res = evaluate_threshold(y_val, y_val_pred_prob, thresh)
        print(f"Results for > {thresh} mm: {res}")
        
        row = {'threshold': thresh}
        row.update(res)
        results.append(row)
        
    results_df = pl.DataFrame(results)
    results_df.write_csv("docs/ml/experiments/threshold_results.csv")
    print("\nSaved threshold results to docs/ml/experiments/threshold_results.csv")

if __name__ == "__main__":
    run_threshold_experiment()
