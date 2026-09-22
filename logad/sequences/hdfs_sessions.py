from __future__ import annotations

import pandas as pd


def build_hdfs_sessions(
    events: pd.DataFrame, labels: pd.DataFrame | None = None
) -> pd.DataFrame:
    """One row per block id: event-id sequence + optional ground-truth label."""
    grouped = (
        events.sort_values(["block_id", "line_no"])
        .groupby("block_id", sort=False)
        .agg(
            event_ids=("event_id", list),
            n_events=("event_id", "size"),
            n_lines=("line_no", "nunique"),
        )
        .reset_index()
        .rename(columns={"block_id": "seq_id"})
    )
    grouped["dataset"] = "hdfs"
    grouped["window_sec"] = pd.NA
    if labels is not None:
        merged = grouped.merge(
            labels.rename(columns={"block_id": "seq_id"}), on="seq_id", how="left"
        )
        merged["y"] = merged["y"].fillna(0).astype(int)
        return merged
    grouped["y"] = 0
    grouped["label"] = "Unknown"
    return grouped
