"""
Generate visualizations for CWS Final Four stats analysis.

Usage:
    python visualize_results.py [--results-dir results]
"""

import os
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)


def plot_percentile_comparison(results_dir, output_dir):
    """Bar chart comparing avg percentile ranks between eras."""
    filepath = os.path.join(results_dir, "percentile_comparison.csv")
    if not os.path.exists(filepath):
        print(f"Skipping percentile plot - {filepath} not found")
        return
    
    df = pd.read_csv(filepath)
    df = df.sort_values("delta", ascending=True)
    
    fig, ax = plt.subplots(figsize=(12, max(8, len(df) * 0.4)))
    
    y = range(len(df))
    width = 0.35
    
    bars1 = ax.barh(
        [i - width/2 for i in y], df["historical_avg_pctile"], width,
        label="2014-2023 (Historical)", color="#2196F3", alpha=0.8
    )
    bars2 = ax.barh(
        [i + width/2 for i in y], df["recent_avg_pctile"], width,
        label="2024-2025 (Recent)", color="#FF5722", alpha=0.8
    )
    
    ax.set_yticks(y)
    ax.set_yticklabels(df["stat"])
    ax.set_xlabel("Average National Percentile Rank of CWS Final Four Teams")
    ax.set_title("CWS Final Four: Average Percentile Rank by Stat\n(Higher = Better relative to D1)")
    ax.legend(loc="lower right")
    ax.axvline(x=50, color="gray", linestyle="--", alpha=0.5, label="D1 Median")
    ax.set_xlim(0, 100)
    
    plt.tight_layout()
    outpath = os.path.join(output_dir, "percentile_comparison.png")
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def plot_zscore_significance(results_dir, output_dir):
    """Volcano-style plot showing effect size vs p-value."""
    filepath = os.path.join(results_dir, "zscore_comparison.csv")
    if not os.path.exists(filepath):
        print(f"Skipping z-score plot - {filepath} not found")
        return
    
    df = pd.read_csv(filepath)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Color by significance
    colors = []
    for _, row in df.iterrows():
        if row["p_value"] < 0.05:
            colors.append("#FF1744" if row["cohens_d"] > 0 else "#2979FF")
        elif row["p_value"] < 0.10:
            colors.append("#FF8A80" if row["cohens_d"] > 0 else "#82B1FF")
        else:
            colors.append("#9E9E9E")
    
    scatter = ax.scatter(
        df["cohens_d"], 
        -np.log10(df["p_value"]),
        c=colors, s=100, alpha=0.8, edgecolors="black", linewidth=0.5
    )
    
    # Label points
    for _, row in df.iterrows():
        ax.annotate(
            row["stat"],
            (row["cohens_d"], -np.log10(row["p_value"])),
            fontsize=8, ha="center", va="bottom",
            xytext=(0, 5), textcoords="offset points"
        )
    
    # Significance lines
    ax.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5, label="p=0.05")
    ax.axhline(y=-np.log10(0.10), color="orange", linestyle="--", alpha=0.5, label="p=0.10")
    ax.axvline(x=0, color="gray", linestyle="-", alpha=0.3)
    
    ax.set_xlabel("Cohen's d (Effect Size)\n← Less important recently | More important recently →")
    ax.set_ylabel("-log10(p-value)\n↑ More statistically significant")
    ax.set_title("CWS Final Four Stats: Which Have Shifted?\n(2024-2025 vs 2014-2023)")
    ax.legend()
    
    # Add legend patches
    legend_elements = [
        mpatches.Patch(color="#FF1744", label="Significant RISE (p<0.05)"),
        mpatches.Patch(color="#2979FF", label="Significant FALL (p<0.05)"),
        mpatches.Patch(color="#9E9E9E", label="Not significant"),
    ]
    ax.legend(handles=legend_elements, loc="upper left")
    
    plt.tight_layout()
    outpath = os.path.join(output_dir, "zscore_volcano.png")
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def plot_feature_importance(results_dir, output_dir):
    """Side-by-side bar chart of Random Forest feature importances by era."""
    filepath = os.path.join(results_dir, "feature_importance.csv")
    if not os.path.exists(filepath):
        print(f"Skipping feature importance plot - {filepath} not found")
        return
    
    df = pd.read_csv(filepath, index_col=0)
    df = df.sort_values("delta", ascending=True)
    
    # Take top/bottom 15 stats
    if len(df) > 20:
        top = df.nlargest(10, "delta")
        bottom = df.nsmallest(10, "delta")
        df = pd.concat([bottom, top])
    
    fig, axes = plt.subplots(1, 2, figsize=(16, max(8, len(df) * 0.35)), sharey=True)
    
    y = range(len(df))
    
    axes[0].barh(y, df["historical_importance"], color="#2196F3", alpha=0.8)
    axes[0].set_title("Historical (2014-2023)")
    axes[0].set_xlabel("Feature Importance")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(df.index)
    axes[0].invert_xaxis()
    
    axes[1].barh(y, df["recent_importance"], color="#FF5722", alpha=0.8)
    axes[1].set_title("Recent (2024-2025)")
    axes[1].set_xlabel("Feature Importance")
    
    fig.suptitle("Random Forest Feature Importance for Predicting CWS Final Four",
                 fontsize=14, fontweight="bold")
    
    plt.tight_layout()
    outpath = os.path.join(output_dir, "feature_importance.png")
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def plot_era_heatmap(results_dir, output_dir):
    """Heatmap of all stats showing the delta between eras."""
    filepath = os.path.join(results_dir, "percentile_comparison.csv")
    if not os.path.exists(filepath):
        return
    
    df = pd.read_csv(filepath).sort_values("delta", ascending=False)
    
    fig, ax = plt.subplots(figsize=(8, max(6, len(df) * 0.35)))
    
    data = df[["stat", "delta"]].set_index("stat")
    
    sns.heatmap(
        data, annot=True, fmt=".1f", cmap="RdBu_r", center=0,
        ax=ax, cbar_kws={"label": "Percentile Shift (Recent - Historical)"},
        linewidths=0.5
    )
    
    ax.set_title("Percentile Shift: CWS Final Four Stats\n(Positive = Higher rank in 2024-25)")
    ax.set_ylabel("")
    
    plt.tight_layout()
    outpath = os.path.join(output_dir, "delta_heatmap.png")
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def generate_all_plots(results_dir="results", output_dir=None):
    """Generate all visualizations."""
    if output_dir is None:
        output_dir = results_dir
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    plot_percentile_comparison(results_dir, output_dir)
    plot_zscore_significance(results_dir, output_dir)
    plot_feature_importance(results_dir, output_dir)
    plot_era_heatmap(results_dir, output_dir)
    
    print("\nAll visualizations generated!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    
    generate_all_plots(args.results_dir, args.output_dir)
