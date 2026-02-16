"""
Analyze CWS team stats across flexible comparison groups.

Runs all preset scenarios from cws_teams.py and outputs results.

Usage:
    python analyze_cws_stats.py                    # Run default scenario
    python analyze_cws_stats.py --scenario all     # Run all scenarios
    python analyze_cws_stats.py --scenario recent_3yr
    python analyze_cws_stats.py --debug            # Extra diagnostics
"""

import os
import sys
import json
import argparse
import logging
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from cws_teams import (
    CWS_DATA, SCENARIOS, get_comparison, find_team_in_data, STAT_CATEGORIES
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("results/analysis_log.txt", mode="w"),
    ]
)
logger = logging.getLogger(__name__)

RESULTS_DIR = "results"
DATA_DIR = "data"


# ============================================================
# DATA LOADING
# ============================================================

def load_data():
    """Load the master stats dataset."""
    master_file = os.path.join(DATA_DIR, "all_team_stats.csv")
    
    if not os.path.exists(master_file):
        logger.error(f"Master data file not found: {master_file}")
        logger.error("Run scrape_ncaa_stats.py first.")
        sys.exit(1)
    
    df = pd.read_csv(master_file)
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"Years: {sorted(df['year'].unique())}")
    logger.info(f"Sample teams: {df['team'].head(5).tolist()}")
    
    return df


def load_stat_metadata():
    """Load stat metadata (type, direction)."""
    meta_file = os.path.join(DATA_DIR, "stat_metadata.json")
    if os.path.exists(meta_file):
        with open(meta_file) as f:
            return json.load(f)
    
    # Fallback: reconstruct from STAT_CATEGORIES
    meta = {}
    for name, config in STAT_CATEGORIES.items():
        meta[name] = {
            "type": config["type"],
            "lower_is_better": config["lower_is_better"],
        }
    meta["iso"] = {"type": "batting", "lower_is_better": False}
    meta["ops"] = {"type": "batting", "lower_is_better": False}
    return meta


def get_stat_columns(df):
    """Identify stat columns (exclude metadata columns)."""
    meta_cols = {"year", "team", "is_target", "is_baseline", "group"}
    return [c for c in df.columns 
            if c not in meta_cols 
            and df[c].dtype in [np.float64, np.int64, float, int]
            and not c.endswith("_pctile")
            and not c.endswith("_zscore")]


# ============================================================
# NORMALIZATION
# ============================================================

def add_percentiles(df, stat_cols, stat_meta):
    """Add within-year percentile rank columns (0-100, higher = better)."""
    for stat in stat_cols:
        if stat not in df.columns:
            continue
        
        lower_better = stat_meta.get(stat, {}).get("lower_is_better", False)
        pctile_col = f"{stat}_pctile"
        df[pctile_col] = np.nan
        
        for year in df["year"].unique():
            mask = df["year"] == year
            vals = df.loc[mask, stat].dropna()
            if len(vals) < 10:
                continue
            
            for idx in df.loc[mask].index:
                v = df.loc[idx, stat]
                if pd.isna(v):
                    continue
                p = scipy_stats.percentileofscore(vals, v, kind="rank")
                df.loc[idx, pctile_col] = (100 - p) if lower_better else p
    
    return df


def add_zscores(df, stat_cols, stat_meta):
    """Add within-year z-score columns (positive = better)."""
    for stat in stat_cols:
        if stat not in df.columns:
            continue
        
        lower_better = stat_meta.get(stat, {}).get("lower_is_better", False)
        z_col = f"{stat}_zscore"
        df[z_col] = np.nan
        
        for year in df["year"].unique():
            mask = df["year"] == year
            vals = df.loc[mask, stat].dropna()
            if len(vals) < 10 or vals.std() == 0:
                continue
            
            mean, std = vals.mean(), vals.std()
            for idx in df.loc[mask].index:
                v = df.loc[idx, stat]
                if pd.isna(v):
                    continue
                z = (v - mean) / std
                df.loc[idx, z_col] = -z if lower_better else z
    
    return df


# ============================================================
# TEAM MATCHING
# ============================================================

def label_teams(df, comparison):
    """
    Label teams as target/baseline based on comparison config.
    Returns df with 'group' column ('target', 'baseline', or 'other').
    """
    df = df.copy()
    df["group"] = "other"
    
    available_teams_by_year = {}
    for year in df["year"].unique():
        available_teams_by_year[year] = df.loc[df["year"] == year, "team"].tolist()
    
    match_log = {"target": [], "baseline": [], "unmatched": []}
    
    for label, team_list in [("target", comparison["target"]), 
                              ("baseline", comparison["baseline"])]:
        for year, team_name in team_list:
            if year not in available_teams_by_year:
                match_log["unmatched"].append(f"{year} {team_name} (year not in data)")
                continue
            
            matched = find_team_in_data(team_name, available_teams_by_year[year])
            
            if matched:
                mask = (df["year"] == year) & (df["team"] == matched)
                df.loc[mask, "group"] = label
                match_log[label].append(f"{year} {team_name} -> {matched}")
            else:
                match_log["unmatched"].append(f"{year} {team_name}")
    
    # Log matching results
    logger.info(f"\nTeam matching results:")
    logger.info(f"  Target matched:   {len(match_log['target'])}")
    logger.info(f"  Baseline matched: {len(match_log['baseline'])}")
    logger.info(f"  Unmatched:        {len(match_log['unmatched'])}")
    
    if match_log["unmatched"]:
        logger.warning(f"  Unmatched teams: {match_log['unmatched']}")
    
    return df, match_log


# ============================================================
# ANALYSIS
# ============================================================

def percentile_comparison(df, stat_cols):
    """Compare avg percentile ranks between target and baseline groups."""
    results = []
    
    for stat in stat_cols:
        p_col = f"{stat}_pctile"
        if p_col not in df.columns:
            continue
        
        target = df.loc[df["group"] == "target", p_col].dropna()
        baseline = df.loc[df["group"] == "baseline", p_col].dropna()
        
        if len(target) < 2 or len(baseline) < 2:
            continue
        
        results.append({
            "stat": stat,
            "target_avg_pctile": round(target.mean(), 1),
            "target_n": len(target),
            "baseline_avg_pctile": round(baseline.mean(), 1),
            "baseline_n": len(baseline),
            "delta": round(target.mean() - baseline.mean(), 1),
        })
    
    out = pd.DataFrame(results).sort_values("delta", ascending=False)
    out["direction"] = out["delta"].apply(
        lambda d: "RISING" if d > 5 else ("FALLING" if d < -5 else "STABLE")
    )
    return out


def zscore_comparison(df, stat_cols):
    """Welch's t-test on z-scores between groups."""
    results = []
    
    for stat in stat_cols:
        z_col = f"{stat}_zscore"
        if z_col not in df.columns:
            continue
        
        target = df.loc[df["group"] == "target", z_col].dropna()
        baseline = df.loc[df["group"] == "baseline", z_col].dropna()
        
        if len(target) < 2 or len(baseline) < 2:
            continue
        
        t_stat, p_val = scipy_stats.ttest_ind(target, baseline, equal_var=False)
        
        pooled = np.sqrt((target.std()**2 + baseline.std()**2) / 2)
        d = (target.mean() - baseline.mean()) / pooled if pooled > 0 else 0
        
        results.append({
            "stat": stat,
            "target_mean_z": round(target.mean(), 3),
            "baseline_mean_z": round(baseline.mean(), 3),
            "delta_z": round(target.mean() - baseline.mean(), 3),
            "t_stat": round(t_stat, 3),
            "p_value": round(p_val, 4),
            "cohens_d": round(d, 3),
            "sig_05": p_val < 0.05,
            "sig_10": p_val < 0.10,
            "effect": (
                "large" if abs(d) >= 0.8 else
                "medium" if abs(d) >= 0.5 else
                "small" if abs(d) >= 0.2 else
                "negligible"
            ),
        })
    
    return pd.DataFrame(results).sort_values("p_value")


def feature_importance(df, stat_cols):
    """Random Forest feature importance for target vs all others."""
    available = [s for s in stat_cols if s in df.columns]
    if len(available) < 3:
        return pd.DataFrame()
    
    analysis_df = df[df["group"].isin(["target", "baseline", "other"])].copy()
    analysis_df["label"] = (analysis_df["group"] == "target").astype(int)
    analysis_df = analysis_df.dropna(subset=available, thresh=len(available) // 2)
    
    if analysis_df["label"].sum() < 3:
        logger.warning("Not enough target teams for RF analysis")
        return pd.DataFrame()
    
    X = analysis_df[available].fillna(analysis_df[available].median())
    y = analysis_df["label"]
    
    rf = RandomForestClassifier(
        n_estimators=500, max_depth=5,
        class_weight="balanced", random_state=42
    )
    rf.fit(StandardScaler().fit_transform(X), y)
    
    imp = pd.DataFrame({
        "stat": available,
        "importance": rf.feature_importances_,
    }).sort_values("importance", ascending=False)
    
    return imp


# ============================================================
# RUN SCENARIO
# ============================================================

def run_scenario(scenario_key, df, stat_cols, stat_meta, debug=False):
    """Run a complete analysis for one scenario."""
    scenario = SCENARIOS[scenario_key]
    logger.info(f"\n{'#'*60}")
    logger.info(f"SCENARIO: {scenario['name']}")
    logger.info(f"{'#'*60}")
    
    comparison = get_comparison(
        scenario["target_group"], scenario["target_years"],
        scenario["baseline_group"], scenario["baseline_years"],
    )
    
    logger.info(f"Target:   {len(comparison['target'])} team-seasons")
    logger.info(f"Baseline: {len(comparison['baseline'])} team-seasons")
    
    # Label teams
    labeled_df, match_log = label_teams(df, comparison)
    
    target_n = (labeled_df["group"] == "target").sum()
    baseline_n = (labeled_df["group"] == "baseline").sum()
    logger.info(f"Matched - Target: {target_n}, Baseline: {baseline_n}")
    
    if target_n < 2 or baseline_n < 2:
        logger.error("Not enough matched teams to analyze!")
        return
    
    # Output directory for this scenario
    scenario_dir = os.path.join(RESULTS_DIR, scenario_key)
    Path(scenario_dir).mkdir(parents=True, exist_ok=True)
    
    # Save match log
    with open(os.path.join(scenario_dir, "match_log.json"), "w") as f:
        json.dump(match_log, f, indent=2)
    
    # Percentile comparison
    pctile = percentile_comparison(labeled_df, stat_cols)
    if not pctile.empty:
        pctile.to_csv(os.path.join(scenario_dir, "percentile_comparison.csv"), index=False)
        logger.info(f"\nPercentile comparison:")
        logger.info(pctile.to_string(index=False))
    
    # Z-score comparison
    zscore = zscore_comparison(labeled_df, stat_cols)
    if not zscore.empty:
        zscore.to_csv(os.path.join(scenario_dir, "zscore_comparison.csv"), index=False)
        logger.info(f"\nZ-score comparison (Welch's t-test):")
        logger.info(zscore.to_string(index=False))
    
    # Feature importance
    fi = feature_importance(labeled_df, stat_cols)
    if not fi.empty:
        fi.to_csv(os.path.join(scenario_dir, "feature_importance.csv"), index=False)
        logger.info(f"\nTop features (RF importance):")
        logger.info(fi.head(10).to_string(index=False))
    
    # Summary
    logger.info(f"\nResults saved to {scenario_dir}/")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="all",
                        help="Scenario key or 'all' (default: all)")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = load_data()
    stat_meta = load_stat_metadata()
    stat_cols = get_stat_columns(df)
    
    logger.info(f"Stat columns: {stat_cols}")
    
    # Normalize
    logger.info("Computing percentile ranks...")
    df = add_percentiles(df, stat_cols, stat_meta)
    
    logger.info("Computing z-scores...")
    df = add_zscores(df, stat_cols, stat_meta)
    
    # Run scenarios
    if args.scenario == "all":
        for key in SCENARIOS:
            try:
                run_scenario(key, df, stat_cols, stat_meta, args.debug)
            except Exception as e:
                logger.error(f"Scenario {key} failed: {e}")
                if args.debug:
                    traceback.print_exc()
    else:
        if args.scenario not in SCENARIOS:
            logger.error(f"Unknown scenario: {args.scenario}")
            logger.error(f"Available: {list(SCENARIOS.keys())}")
            sys.exit(1)
        run_scenario(args.scenario, df, stat_cols, stat_meta, args.debug)


if __name__ == "__main__":
    main()
