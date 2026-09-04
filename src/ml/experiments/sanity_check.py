import polars as pl
import numpy as np

def run_sanity_checks():
    print("=== RUNNING DATASET SANITY CHECKS ===")
    
    splits = {
        'train': ('2000-01-01', '2018-12-31', 'data/ml/train/*.parquet'),
        'validation': ('2019-01-01', '2021-12-31', 'data/ml/validation/*.parquet'),
        'test': ('2022-01-01', '2025-12-31', 'data/ml/test/*.parquet')
    }
    
    for split_name, (start_date, end_date, glob_path) in splits.items():
        print(f"\n--- Checking {split_name.upper()} split ---")
        df = pl.scan_parquet(glob_path)
        
        # 1. Correct chronological ranges
        time_stats = df.select([
            pl.col('time').min().alias('min_time'),
            pl.col('time').max().alias('max_time'),
            pl.len().alias('count')
        ]).collect()
        
        min_t = time_stats['min_time'][0].strftime('%Y-%m-%d')
        max_t = time_stats['max_time'][0].strftime('%Y-%m-%d')
        row_count = time_stats['count'][0]
        print(f"Date range: {min_t} to {max_t} (Expected approx {start_date} to {end_date})")
        print(f"Row count: {row_count}")
        
        # 7. No duplicates
        dup_count = df.select(['time', 'lat', 'lon']).group_by(['time', 'lat', 'lon']).count().filter(pl.col('count') > 1).select(pl.len()).collect().item()
        print(f"Duplicates (time, lat, lon): {dup_count}")
        assert dup_count == 0, "Duplicate rows found!"
        
        cols = df.collect_schema().names()
        
        # 9. Schema check
        expected_cols = ['time', 'lat', 'lon', 'rf_lag_1', 'tmax_1deg_lag1', 'target_h1', 'target_h7']
        missing_cols = [c for c in expected_cols if c not in cols]
        print(f"Schema check missing cols: {missing_cols}")
        assert len(missing_cols) == 0, f"Missing columns: {missing_cols}"
        
        # Expressions for aggregations
        exprs = []
        for c in ['rf_lag_1', 'target_h1', 'target_h7', 'tmax_1deg_lag1', 'tmin_1deg_lag1']:
            exprs.extend([
                pl.col(c).min().alias(f'{c}_min'),
                pl.col(c).max().alias(f'{c}_max'),
                pl.col(c).is_null().sum().alias(f'{c}_nulls'),
                pl.col(c).is_infinite().sum().alias(f'{c}_infs')
            ])
            
        stats = df.select(exprs).collect()
        
        # 1. No infinite values
        infs = sum(stats[f'{c}_infs'][0] for c in ['rf_lag_1', 'target_h1', 'target_h7', 'tmax_1deg_lag1', 'tmin_1deg_lag1'])
        print(f"Infinite values: {infs}")
        assert infs == 0, "Infinite values found!"
        
        # 2. No impossible negative rainfall
        rf_min = stats['rf_lag_1_min'][0]
        th1_min = stats['target_h1_min'][0]
        print(f"Rainfall Min: rf_lag_1={rf_min}, target_h1={th1_min}")
        assert rf_min >= 0 or np.isnan(rf_min), f"Negative rainfall found! {rf_min}"
        
        # 3. No fabricated temperature values (reasonable limits)
        tmax_min = stats['tmax_1deg_lag1_min'][0]
        tmax_max = stats['tmax_1deg_lag1_max'][0]
        tmin_min = stats['tmin_1deg_lag1_min'][0]
        tmin_max = stats['tmin_1deg_lag1_max'][0]
        print(f"Temperature bounds: TMAX [{tmax_min}, {tmax_max}], TMIN [{tmin_min}, {tmin_max}]")
        assert -30 < tmax_min < 60 and -30 < tmax_max < 60, "Unreasonable TMAX!"
        
        # 4 & 5 & 6. Missingness bounds
        rf_nulls = stats['rf_lag_1_nulls'][0]
        tmax_nulls = stats['tmax_1deg_lag1_nulls'][0]
        
        print(f"Missingness: rf_lag_1={rf_nulls}/{row_count}, tmax_1deg_lag1={tmax_nulls}/{row_count}")
        # TMAX must have missingness because of native domain mapping
        assert tmax_nulls > 0, "Temperature missingness is 0! Extrapolation might have occurred."
        # RF missingness should be extremely low (only edges)
        assert rf_nulls / row_count < 0.001, f"High rainfall missingness! {rf_nulls}"

    print("\n=== SANITY CHECKS PASSED ===")

if __name__ == "__main__":
    run_sanity_checks()
