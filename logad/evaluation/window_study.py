from __future__ import annotations

import pandas as pd


def window_tradeoff_table(metrics_table: pd.DataFrame) -> pd.DataFrame:
    """Keep the SOC-relevant slices for the BGL window-size comparison."""
    keep = metrics_table[
        metrics_table["slice"].isin(["recall≈0.80", "fpr≈0.010", "budget=100"])
        | metrics_table["slice"].str.contains("200_alerts", na=False)
    ].copy()
    return keep.sort_values(["dataset", "model", "grouping", "slice"])
