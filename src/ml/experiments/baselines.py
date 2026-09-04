import polars as pl
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_score, recall_score, f1_score, average_precision_score
import os

EXTREME_THRESHOLD = 17.9128

def evaluate_predictions(y_true, y_pred):
    # Overall Amount
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
        
    # Occurrence
    # For persistence/recent history, y_pred can be used as continuous score for PR-AUC
    # Binary predictions for P/R/F1 > 0
    y_true_occ = (y_true > 0).astype(int)
    y_pred_occ_bin = (y_pred > 0).astype(int)
    
    pr_auc = average_precision_score(y_true_occ, y_pred)
    precision = precision_score(y_true_occ, y_pred_occ_bin, zero_division=0)
    recall = recall_score(y_true_occ, y_pred_occ_bin, zero_division=0)
    f1 = f1_score(y_true_occ, y_pred_occ_bin, zero_division=0)
    
    # Extremes
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

def run_baselines():
    print("=== RUNNING PHASE A: BASELINES ===")
    os.makedirs("docs/ml/experiments", exist_ok=True)
    
    # Load Validation Set
    val_df = pl.read_parquet("data/ml/validation/*.parquet")
    
    # Prepare Climatology (from Train)
    print("Computing Climatology from Train...")
    train_lazy = pl.scan_parquet("data/ml/train/*.parquet").select(['time', 'lat', 'lon', 'target_h1'])
    # For H1, time t target_h1 is day t+1. 
    # We want climatology for day t+h. So for day t+1 (which is target_h1's date), 
    # the date is time + 1d.
    train_lazy = train_lazy.with_columns(
        (pl.col("time") + pl.duration(days=1)).dt.ordinal_day().alias("doy_h1")
    )
    climatology = train_lazy.group_by(["lat", "lon", "doy_h1"]).agg(
        pl.col("target_h1").mean().alias("clim_rain")
    ).collect(streaming=True)
    
    results = []
    
    for h in range(1, 8):
        print(f"--- Evaluating Horizon {h} ---")
        target_col = f"target_h{h}"
        
        # Valid data mask for this horizon (drop NaNs due to edge)
        vdf = val_df.filter(pl.col(target_col).is_not_null())
        y_true = vdf[target_col].to_numpy()
        
        # Baseline A: Climatology
        # DOY for t+h
        vdf_clim = vdf.with_columns(
            (pl.col("time") + pl.duration(days=h)).dt.ordinal_day().alias("doy_h1")
        )
        vdf_clim = vdf_clim.join(climatology, on=["lat", "lon", "doy_h1"], how="left")
        # Fill any leap year mismatches with overall mean or 0
        y_pred_clim = vdf_clim["clim_rain"].fill_null(0.0).to_numpy()
        
        # Baseline B: Persistence
        y_pred_pers = vdf["rf_lag_1"].to_numpy()
        
        # Baseline C: Recent History (7-day sum / 7)
        y_pred_rec = (vdf["rf_roll7_sum"] / 7.0).to_numpy()
        
        # Evaluate
        res_clim = evaluate_predictions(y_true, y_pred_clim)
        res_pers = evaluate_predictions(y_true, y_pred_pers)
        res_rec = evaluate_predictions(y_true, y_pred_rec)
        
        for model_name, res in [("Climatology", res_clim), ("Persistence", res_pers), ("RecentHistory", res_rec)]:
            row = {'model': model_name, 'horizon': h}
            row.update(res)
            results.append(row)
            
    # Save results
    results_df = pl.DataFrame(results)
    results_df.write_csv("docs/ml/experiments/baseline_results.csv")
    print(f"\nSaved baseline results to docs/ml/experiments/baseline_results.csv")
    
if __name__ == "__main__":
    run_baselines()
