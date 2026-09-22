from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", context="talk")


def plot_window_tradeoff(curve: pd.DataFrame, out: Path) -> Path:
    """Hero chart: recall vs false-positive rate by window size."""
    fig, ax = plt.subplots(figsize=(10, 6))
    data = curve.copy()
    data["window"] = data["grouping"]
    sns.lineplot(
        data=data,
        x="fpr",
        y="recall",
        hue="window",
        style="model",
        ax=ax,
        linewidth=2.4,
    )
    ax.set_xlim(0, 0.08)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("Recall (anomalous windows caught)")
    ax.set_title("Window size moves the SOC tradeoff more than the model")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out


def plot_alert_volume(table: pd.DataFrame, out: Path) -> Path:
    subset = table[table["slice"] == "recall≈0.80"].copy()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.barplot(
        data=subset,
        x="grouping",
        y="alerts_per_million_lines",
        hue="model",
        ax=ax,
    )
    ax.set_xlabel("Grouping")
    ax.set_ylabel("Alerts per million log lines @ ~80% recall")
    ax.set_title("Alert volume a human would actually see")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out


def plot_fpr_at_recall(table: pd.DataFrame, out: Path) -> Path:
    subset = table[table["slice"] == "recall≈0.80"].copy()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.barplot(data=subset, x="grouping", y="fpr", hue="model", ax=ax)
    ax.set_ylabel("False positive rate @ ~80% recall")
    ax.set_xlabel("Grouping")
    ax.set_title("False positives dominate usefulness, not accuracy")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out
