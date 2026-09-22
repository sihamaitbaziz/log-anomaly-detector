from __future__ import annotations

import pandas as pd


def build_bgl_windows(
    events: pd.DataFrame, window_sec: int, store_lines: bool = False
) -> pd.DataFrame:
    """Fixed-width time windows. A window is anomalous if any line is an alert."""
    if window_sec <= 0:
        raise ValueError("window_sec must be positive")
    frame = events.copy()
    ts0 = int(frame["timestamp"].min())
    frame["window_id"] = ((frame["timestamp"] - ts0) // window_sec).astype(int)
    aggregations = {
        "event_ids": ("event_id", list),
        "n_events": ("event_id", "size"),
        "n_lines": ("line_no", "nunique"),
        "n_alerts": ("is_alert", "sum"),
        "t_start": ("timestamp", "min"),
        "t_end": ("timestamp", "max"),
    }
    if store_lines:
        aggregations["contents"] = ("content", list)
        aggregations["line_nos"] = ("line_no", list)
    grouped = (
        frame.sort_values(["window_id", "line_no"])
        .groupby("window_id", sort=True)
        .agg(**aggregations)
        .reset_index()
    )
    grouped["seq_id"] = grouped["window_id"].map(lambda i: f"w{window_sec}_{i}")
    grouped["y"] = (grouped["n_alerts"] > 0).astype(int)
    grouped["dataset"] = "bgl"
    grouped["window_sec"] = window_sec
    return grouped
