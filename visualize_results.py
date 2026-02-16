"""
Generate visualizations for all analyzed scenarios.

Usage:
    python visualize_results.py
"""

import os
import sys
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for CI
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

from cws_teams import SCENARIOS

sns.set_theme(style="whitegrid", font_scale=1.1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = "results"


def plot_percentile(scenario_dir, scenario_name):
    """Horizontal bar chart: avg percentile by stat, target vs baseline."""
    fp = os.path.join(scenario_dir, "percentile_comparison.csv")
    if not os.path.exists(fp):
        return
    
    df = pd.read_csv(fp).sort_values("delta", ascending=True)
    if df.empty:
        return
    
    fig, ax = plt.subplots(figsize=(12, max(6, len(df) * 0.45)))
    y = range(len(df))
    w = 0.35
    
    ax.barh([i - w/2 for i in y], df["baseline_avg_pctile"], w,
            label="Baseline", color="#2196F3", alpha=0.8)
    ax.barh([i + w/2 for i in y], df["target_avg_pctile"], w,
            label="Target", color="#FF5722", alpha=0.8)
    
    ax.set_yticks(y)
    ax.set_yticklabels(df["stat"], fontsize=9)
    ax.set_xlabel("Avg National Percentile (higher = better)")
    ax.set_title(f"Percentile Comparison\n{scenario_name}", fontsize=12)
    ax.legend(loc="lower right")
    ax.axvline(x=50, color="gray", linestyle="--", alpha=0.4)
    ax.set_xlim(0, 100)
    
    plt.tight_layout()
    plt.savefig(os.path.join(scenario_dir, "percentile_chart.png"), dpi=150)
    plt.close()


def plot_volcano(scenario_dir, scenario_name):
    """Volcano plot: effect size vs significance."""
    fp = os.path.join(scenario_dir, "zscore_comparison.csv")
    if not os.path.exists(fp):
        return
    
    df = pd.read_csv(fp)
    if df.empty:
        return
    
    fig, ax = plt.subplots(figsize=(11, 8))
    
    colors = []
    for _, r in df.iterrows():
        if r["p_value"] < 0.05:
            colors.append("#FF1744" if r["cohens_d"] > 0 else "#2979FF")
        elif r["p_value"] < 0.10:
            colors.append("#FF8A80" if r["cohens_d"] > 0 else "#82B1FF")
        else:
            colors.append("#9E9E9E")
    
    ax.scatter(df["cohens_d"], -np.log10(df["p_value"].clip(lower=1e-10)),
               c=colors, s=100, alpha=0.8, edgecolors="black", linewidth=0.5)
    
    for _, r in df.iterrows():
        ax.annotate(r["stat"], (r["cohens_d"], -np.log10(max(r["p_value"], 1e-10))),
                     fontsize=7, ha="center", va="bottom", xytext=(0, 5),
                     textcoords="offset points")
    
    ax.axhline(-np.log10(0.05), color="red", linestyle="--", alpha=0.4, label="p=0.05")
    ax.axhline(-np.log10(0.10), color="orange", linestyle="--", alpha=0.4, label="p=0.10")
    ax.axvline(0, color="gray", linestyle="-", alpha=0.3)
    
    ax.set_xlabel("Cohen's d\n← Lower in target | Higher in target →")
    ax.set_ylabel("-log10(p-value)")
    ax.set_title(f"Statistical Significance of Stat Shifts\n{scenario_name}", fontsize=12)
    
    legend = [
        mpatches.Patch(color="#FF1744", label="Sig. rise (p<0.05)"),
        mpatches.Patch(color="#2979FF", label="Sig. fall (p<0.05)"),
        mpatches.Patch(color="#9E9E9E", label="Not significant"),
    ]
    ax.legend(handles=legend, loc="upper left")
    
    plt.tight_layout()
    plt.savefig(os.path.join(scenario_dir, "volcano_chart.png"), dpi=150)
    plt.close()


def plot_heatmap(scenario_dir, scenario_name):
    """Delta heatmap."""
    fp = os.path.join(scenario_dir, "percentile_comparison.csv")
    if not os.path.exists(fp):
        return
    
    df = pd.read_csv(fp).sort_values("delta", ascending=False)
    if df.empty:
        return
    
    fig, ax = plt.subplots(figsize=(6, max(5, len(df) * 0.35)))
    data = df.set_index("stat")[["delta"]]
    
    sns.heatmap(data, annot=True, fmt=".1f", cmap="RdBu_r", center=0,
                ax=ax, linewidths=0.5,
                cbar_kws={"label": "Percentile Shift"})
    ax.set_title(f"Percentile Shift\n{scenario_name}", fontsize=11)
    ax.set_ylabel("")
    
    plt.tight_layout()
    plt.savefig(os.path.join(scenario_dir, "heatmap.png"), dpi=150)
    plt.close()


def main():
    for key, scenario in SCENARIOS.items():
        scenario_dir = os.path.join(RESULTS_DIR, key)
        if not os.path.isdir(scenario_dir):
            logger.info(f"Skipping {key} (no results directory)")
            continue
        
        logger.info(f"Generating plots for: {key}")
        
        try:
            plot_percentile(scenario_dir, scenario["name"])
            plot_volcano(scenario_dir, scenario["name"])
            plot_heatmap(scenario_dir, scenario["name"])
            logger.info(f"  Done: {scenario_dir}/")
        except Exception as e:
            logger.error(f"  Failed: {e}")
    
    logger.info("\nAll visualizations complete.")


if __name__ == "__main__":
    main()
