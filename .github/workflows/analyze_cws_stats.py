"""
Analyze CWS Final Four team stats vs. the D1 population.

Compares the 2024-2025 era to 2014-2023 to find which stats have
become more/less important for reaching the CWS Final Four.

Usage:
    python analyze_cws_stats.py [--data-dir data] [--output-dir results]
"""

import os
import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from cws_teams import (
    CWS_FINAL_FOUR, RECENT_YEARS, HISTORICAL_YEARS, ALL_YEARS,
    get_final_four_by_era
)

warnings.filterwarnings("ignore")


# ============================================================
# DATA LOADING
# ============================================================

def load_all_team_stats(data_dir="data"):
    """
    Load scraped NCAA team stats from CSV files.
    
    Expects files named like:
      - ncaa_team_stats_{year}.csv  (from direct scraping)
      - OR batting_{year}.csv + pitching_{year}.csv (from collegebaseball/baseballr)
    """
    all_data = []
    
    for year in ALL_YEARS:
        # Try direct scrape format first
        direct_file = os.path.join(data_dir, f"ncaa_team_stats_{year}.csv")
        if os.path.exists(direct_file):
            df = pd.read_csv(direct_file)
            df["year"] = year
            all_data.append(df)
            continue
        
        # Try batting/pitching split format
        bat_file = os.path.join(data_dir, f"batting_{year}.csv")
        pitch_file = os.path.join(data_dir, f"pitching_{year}.csv")
        
        if os.path.exists(bat_file):
            bat = pd.read_csv(bat_file)
            bat["year"] = year
            all_data.append(bat)
        
        if os.path.exists(pitch_file):
            pitch = pd.read_csv(pitch_file)
            pitch["year"] = year
            all_data.append(pitch)
    
    if not all_data:
        raise FileNotFoundError(
            f"No data files found in {data_dir}. Run scrape_ncaa_stats.py first."
        )
    
    combined = pd.concat(all_data, ignore_index=True)
    return combined


def build_team_stat_matrix(raw_data):
    """
    Transform raw scraped data into a wide-format matrix:
    Each row = one team-year, columns = stat values.
    
    This function handles both data formats (direct scrape vs. collegebaseball).
    """
    # If data is in long format (stat_name, stat_value columns):
    if "stat_name" in raw_data.columns and "stat_value" in raw_data.columns:
        pivot = raw_data.pivot_table(
            index=["year", "team"],
            columns="stat_name",
            values="stat_value",
            aggfunc="first"
        ).reset_index()
        return pivot
    
    # If data is in wide format from baseballr/collegebaseball, 
    # it will have columns like BA, OBP, SLG, ERA, etc.
    # Just ensure year and team columns exist
    team_col = None
    for col in ["team", "team_name", "team_name_clean", "school"]:
        if col in raw_data.columns:
            team_col = col
            break
    
    if team_col and team_col != "team":
        raw_data = raw_data.rename(columns={team_col: "team"})
    
    return raw_data


# ============================================================
# NORMALIZATION
# ============================================================

def compute_percentile_ranks(df, stat_columns, year_col="year"):
    """
    For each stat in each year, compute each team's percentile rank 
    (0-100) within that year's D1 population.
    
    Returns a new DataFrame with {stat}_pctile columns added.
    """
    result = df.copy()
    
    for stat in stat_columns:
        if stat not in df.columns:
            continue
        
        pctile_col = f"{stat}_pctile"
        result[pctile_col] = np.nan
        
        for year in df[year_col].unique():
            mask = df[year_col] == year
            values = df.loc[mask, stat].dropna()
            
            if len(values) < 10:
                continue
            
            # For stats where lower is better (ERA, WHIP, walks/9, hits/9),
            # invert the percentile so higher = better
            lower_is_better = stat in [
                "era", "whip", "walks_per_nine", "hits_per_nine",
                "ERA", "WHIP", "BB9", "H9"
            ]
            
            for idx in df.loc[mask].index:
                val = df.loc[idx, stat]
                if pd.isna(val):
                    continue
                pctile = scipy_stats.percentileofscore(values, val, kind="rank")
                if lower_is_better:
                    pctile = 100 - pctile
                result.loc[idx, pctile_col] = pctile
    
    return result


def compute_z_scores(df, stat_columns, year_col="year"):
    """
    For each stat in each year, compute z-scores (standard deviations 
    from the year's D1 mean).
    
    Returns a new DataFrame with {stat}_zscore columns added.
    """
    result = df.copy()
    
    for stat in stat_columns:
        if stat not in df.columns:
            continue
        
        z_col = f"{stat}_zscore"
        result[z_col] = np.nan
        
        for year in df[year_col].unique():
            mask = df[year_col] == year
            values = df.loc[mask, stat].dropna()
            
            if len(values) < 10:
                continue
            
            mean = values.mean()
            std = values.std()
            
            if std == 0:
                continue
            
            lower_is_better = stat in [
                "era", "whip", "walks_per_nine", "hits_per_nine",
                "ERA", "WHIP", "BB9", "H9"
            ]
            
            for idx in df.loc[mask].index:
                val = df.loc[idx, stat]
                if pd.isna(val):
                    continue
                z = (val - mean) / std
                if lower_is_better:
                    z = -z  # Flip so positive = better
                result.loc[idx, z_col] = z
    
    return result


# ============================================================
# ANALYSIS
# ============================================================

def label_final_four_teams(df, year_col="year", team_col="team"):
    """Add a binary column indicating if a team was in the CWS Final Four."""
    df = df.copy()
    df["is_final_four"] = 0
    
    for year, teams in CWS_FINAL_FOUR.items():
        for team in teams:
            mask = (df[year_col] == year)
            # Fuzzy match team names (NCAA names can vary)
            for idx in df.loc[mask].index:
                if team.lower() in str(df.loc[idx, team_col]).lower():
                    df.loc[idx, "is_final_four"] = 1
    
    return df


def compare_eras_percentile(df, stat_columns):
    """
    Compare average percentile ranks of Final Four teams 
    between recent and historical eras.
    
    Returns a DataFrame with one row per stat showing:
    - historical_avg_pctile
    - recent_avg_pctile
    - delta (recent - historical)
    - interpretation
    """
    results = []
    
    pctile_cols = [f"{s}_pctile" for s in stat_columns if f"{s}_pctile" in df.columns]
    
    ff = df[df["is_final_four"] == 1].copy()
    ff["era"] = ff["year"].apply(
        lambda y: "recent" if y in RECENT_YEARS else "historical"
    )
    
    for col in pctile_cols:
        stat_name = col.replace("_pctile", "")
        
        hist_vals = ff.loc[ff["era"] == "historical", col].dropna()
        recent_vals = ff.loc[ff["era"] == "recent", col].dropna()
        
        if len(hist_vals) < 3 or len(recent_vals) < 3:
            continue
        
        hist_mean = hist_vals.mean()
        recent_mean = recent_vals.mean()
        delta = recent_mean - hist_mean
        
        results.append({
            "stat": stat_name,
            "historical_avg_pctile": round(hist_mean, 1),
            "recent_avg_pctile": round(recent_mean, 1),
            "delta": round(delta, 1),
            "direction": "RISING" if delta > 5 else ("FALLING" if delta < -5 else "STABLE"),
        })
    
    return pd.DataFrame(results).sort_values("delta", ascending=False)


def compare_eras_zscore(df, stat_columns):
    """
    Compare z-scores of Final Four teams between eras using Welch's t-test.
    
    Returns a DataFrame with statistical test results for each stat.
    """
    results = []
    
    z_cols = [f"{s}_zscore" for s in stat_columns if f"{s}_zscore" in df.columns]
    
    ff = df[df["is_final_four"] == 1].copy()
    ff["era"] = ff["year"].apply(
        lambda y: "recent" if y in RECENT_YEARS else "historical"
    )
    
    for col in z_cols:
        stat_name = col.replace("_zscore", "")
        
        hist_vals = ff.loc[ff["era"] == "historical", col].dropna()
        recent_vals = ff.loc[ff["era"] == "recent", col].dropna()
        
        if len(hist_vals) < 3 or len(recent_vals) < 3:
            continue
        
        # Welch's t-test
        t_stat, p_value = scipy_stats.ttest_ind(recent_vals, hist_vals, equal_var=False)
        
        # Cohen's d effect size
        pooled_std = np.sqrt(
            (hist_vals.std()**2 + recent_vals.std()**2) / 2
        )
        cohens_d = (recent_vals.mean() - hist_vals.mean()) / pooled_std if pooled_std > 0 else 0
        
        results.append({
            "stat": stat_name,
            "historical_mean_z": round(hist_vals.mean(), 3),
            "recent_mean_z": round(recent_vals.mean(), 3),
            "delta_z": round(recent_vals.mean() - hist_vals.mean(), 3),
            "t_statistic": round(t_stat, 3),
            "p_value": round(p_value, 4),
            "cohens_d": round(cohens_d, 3),
            "significant_p05": p_value < 0.05,
            "significant_p10": p_value < 0.10,
            "effect_size": (
                "large" if abs(cohens_d) >= 0.8 else
                "medium" if abs(cohens_d) >= 0.5 else
                "small" if abs(cohens_d) >= 0.2 else
                "negligible"
            ),
        })
    
    return pd.DataFrame(results).sort_values("p_value")


def feature_importance_comparison(df, stat_columns):
    """
    Train Random Forest classifiers for each era to predict 
    CWS Final Four membership. Compare feature importances.
    
    NOTE: Small sample sizes make this exploratory, not definitive.
    """
    available_stats = [s for s in stat_columns if s in df.columns]
    
    results = {}
    
    for era_name, years in [("historical", HISTORICAL_YEARS), ("recent", RECENT_YEARS)]:
        era_df = df[df["year"].isin(years)].copy()
        
        # Drop rows with too many NaN stats
        era_df = era_df.dropna(subset=available_stats, thresh=len(available_stats) // 2)
        
        if len(era_df) < 20 or era_df["is_final_four"].sum() < 3:
            continue
        
        X = era_df[available_stats].fillna(era_df[available_stats].median())
        y = era_df["is_final_four"]
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train RF (with class_weight to handle imbalance)
        rf = RandomForestClassifier(
            n_estimators=500,
            max_depth=5,
            class_weight="balanced",
            random_state=42,
        )
        rf.fit(X_scaled, y)
        
        importances = pd.Series(rf.feature_importances_, index=available_stats)
        importances = importances.sort_values(ascending=False)
        
        results[era_name] = importances
    
    if len(results) == 2:
        comparison = pd.DataFrame({
            "historical_importance": results["historical"],
            "recent_importance": results["recent"],
        })
        comparison["delta"] = comparison["recent_importance"] - comparison["historical_importance"]
        comparison["pct_change"] = (
            comparison["delta"] / comparison["historical_importance"].replace(0, np.nan) * 100
        )
        return comparison.sort_values("delta", ascending=False)
    
    return pd.DataFrame()


# ============================================================
# MAIN
# ============================================================

def run_analysis(data_dir="data", output_dir="results"):
    """Run the complete analysis pipeline."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 1. Load data
    print("Loading data...")
    raw = load_all_team_stats(data_dir)
    df = build_team_stat_matrix(raw)
    
    # 2. Identify stat columns (numeric, non-metadata)
    meta_cols = {"year", "team", "team_name", "conference", "rank", 
                 "is_final_four", "era", "stat_name"}
    stat_columns = [
        c for c in df.columns 
        if c not in meta_cols 
        and df[c].dtype in [np.float64, np.int64, float, int]
        and not c.endswith("_pctile") 
        and not c.endswith("_zscore")
    ]
    
    print(f"Found {len(stat_columns)} stat columns: {stat_columns}")
    
    # 3. Normalize
    print("Computing percentile ranks...")
    df = compute_percentile_ranks(df, stat_columns)
    
    print("Computing z-scores...")
    df = compute_z_scores(df, stat_columns)
    
    # 4. Label Final Four teams
    print("Labeling CWS Final Four teams...")
    df = label_final_four_teams(df)
    
    ff_count = df["is_final_four"].sum()
    print(f"Matched {ff_count} Final Four team-years (expected ~48)")
    
    # 5. Run analyses
    print("\n" + "="*60)
    print("PERCENTILE COMPARISON")
    print("="*60)
    pctile_results = compare_eras_percentile(df, stat_columns)
    if not pctile_results.empty:
        print(pctile_results.to_string(index=False))
        pctile_results.to_csv(
            os.path.join(output_dir, "percentile_comparison.csv"), index=False
        )
    
    print("\n" + "="*60)
    print("Z-SCORE COMPARISON (Welch's t-test)")
    print("="*60)
    zscore_results = compare_eras_zscore(df, stat_columns)
    if not zscore_results.empty:
        print(zscore_results.to_string(index=False))
        zscore_results.to_csv(
            os.path.join(output_dir, "zscore_comparison.csv"), index=False
        )
    
    print("\n" + "="*60)
    print("FEATURE IMPORTANCE COMPARISON (Random Forest)")
    print("="*60)
    fi_results = feature_importance_comparison(df, stat_columns)
    if not fi_results.empty:
        print(fi_results.to_string())
        fi_results.to_csv(
            os.path.join(output_dir, "feature_importance.csv")
        )
    
    # 6. Save full dataset
    df.to_csv(os.path.join(output_dir, "full_dataset.csv"), index=False)
    print(f"\nFull dataset saved to {output_dir}/full_dataset.csv")
    
    # 7. Summary
    print("\n" + "="*60)
    print("SUMMARY: Stats with BIGGEST shifts (recent vs historical)")
    print("="*60)
    
    if not pctile_results.empty:
        rising = pctile_results[pctile_results["direction"] == "RISING"]
        falling = pctile_results[pctile_results["direction"] == "FALLING"]
        
        if not rising.empty:
            print("\nRISING importance (Final Four teams rank higher recently):")
            for _, row in rising.iterrows():
                print(f"  {row['stat']:30s}  {row['historical_avg_pctile']:5.1f} -> {row['recent_avg_pctile']:5.1f}  (+{row['delta']:.1f})")
        
        if not falling.empty:
            print("\nFALLING importance (Final Four teams rank lower recently):")
            for _, row in falling.iterrows():
                print(f"  {row['stat']:30s}  {row['historical_avg_pctile']:5.1f} -> {row['recent_avg_pctile']:5.1f}  ({row['delta']:.1f})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()
    
    run_analysis(args.data_dir, args.output_dir)
