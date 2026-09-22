from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from logad.config import BGL_WINDOWS_SEC, DetectorConfig, Paths
from logad.evaluation.metrics import summarize_run
from logad.evaluation.window_study import window_tradeoff_table
from logad.features.count_vector import log1p_tf, sequences_to_count_matrix
from logad.models.detectors import IsolationForestDetector, PCADetector
from logad.parsing.bgl import parse_bgl_log
from logad.parsing.drain import DrainParser
from logad.parsing.hdfs import load_hdfs_labels, parse_hdfs_log
from logad.sequences.bgl_windows import build_bgl_windows
from logad.sequences.hdfs_sessions import build_hdfs_sessions
from logad.viz.plots import plot_alert_volume, plot_fpr_at_recall, plot_window_tradeoff


def _save_templates(parser: DrainParser, path: Path) -> None:
    rows = [{"event_id": k, "template": v} for k, v in parser.templates().items()]
    pd.DataFrame(rows).to_csv(path, index=False)


def _split_matrix(matrix, y, seq_ids, chronological: bool, seed: int):
    n = matrix.shape[0]
    if chronological:
        cut = int(n * 0.7)
        return (
            matrix[:cut],
            matrix[cut:],
            y[:cut],
            y[cut:],
            seq_ids[:cut],
            seq_ids[cut:],
        )
    idx = np.arange(n)
    counts = np.bincount(y.astype(int))
    can_stratify = len(counts) > 1 and counts.min() >= 2
    train_idx, test_idx = train_test_split(
        idx, test_size=0.3, random_state=seed, stratify=y if can_stratify else None
    )
    return (
        matrix[train_idx],
        matrix[test_idx],
        y[train_idx],
        y[test_idx],
        seq_ids[train_idx],
        seq_ids[test_idx],
    )


def evaluate_sequences(
    sequences: pd.DataFrame,
    *,
    dataset: str,
    grouping: str,
    n_log_lines: int,
    n_templates: int,
    cfg: DetectorConfig,
    chronological: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    matrix, y, seq_ids = sequences_to_count_matrix(sequences, n_events=n_templates)
    matrix = log1p_tf(matrix)
    x_train, x_test, y_train, y_test, id_train, id_test = _split_matrix(
        matrix, y, seq_ids, chronological=chronological, seed=cfg.random_state
    )
    # Unsupervised fit: labels unused during training.
    detectors = [
        IsolationForestDetector(
            n_estimators=cfg.n_estimators,
            random_state=cfg.random_state,
            n_jobs=cfg.n_jobs,
        ),
        PCADetector(variance=cfg.pca_variance, random_state=cfg.random_state),
    ]
    tables = []
    curves = []
    score_payload = {}
    for det in detectors:
        det.fit(x_train)
        scores = det.score(x_test)
        summary = summarize_run(
            dataset=dataset,
            grouping=grouping,
            model=det.name,
            y_true=y_test,
            scores=scores,
            n_log_lines=int(n_log_lines * 0.3),
            n_templates=n_templates,
            n_sequences=len(y_test),
            anomaly_rate=float(y_test.mean()),
            recall_targets=cfg.recall_targets,
            fpr_targets=cfg.fpr_targets,
            alert_budgets=cfg.alert_budgets,
        )
        tables.append(summary["table"])
        curves.append(summary["curve"])
        score_payload[det.name] = {
            "seq_id": id_test.tolist(),
            "y": y_test.tolist(),
            "score": scores.tolist(),
        }
    return pd.concat(tables, ignore_index=True), pd.concat(curves, ignore_index=True), score_payload


def _flagged_windows(
    sequences: pd.DataFrame,
    scores_by_model: dict,
    events: pd.DataFrame,
    window_sec: int,
    top_k: int = 25,
) -> list[dict]:
    if "isolation_forest" not in scores_by_model:
        return []
    payload = scores_by_model["isolation_forest"]
    frame = pd.DataFrame(payload)
    frame = frame.sort_values("score", ascending=False).head(top_k)
    seq_map = sequences.set_index("seq_id")
    ts0 = int(events["timestamp"].min())
    events = events.copy()
    events["window_id"] = ((events["timestamp"] - ts0) // window_sec).astype(int)
    flagged = []
    for row in frame.itertuples():
        if row.seq_id not in seq_map.index:
            continue
        seq = seq_map.loc[row.seq_id]
        window_id = int(seq["window_id"])
        lines = (
            events.loc[events["window_id"] == window_id, "content"]
            .head(40)
            .tolist()
        )
        flagged.append(
            {
                "seq_id": row.seq_id,
                "score": float(row.score),
                "y_true": int(row.y),
                "n_events": int(seq["n_events"]),
                "lines": lines,
            }
        )
    return flagged


def run_hdfs(
    log_path: Path,
    label_path: Path,
    *,
    max_lines: int | None,
    cfg: DetectorConfig,
    paths: Paths,
) -> dict:
    events, parser = parse_hdfs_log(log_path, max_lines=max_lines)
    labels = load_hdfs_labels(label_path)
    sequences = build_hdfs_sessions(events, labels)
    n_templates = len(parser.templates())
    table, curve, scores = evaluate_sequences(
        sequences,
        dataset="hdfs",
        grouping="block_session",
        n_log_lines=int(events["line_no"].nunique()),
        n_templates=n_templates,
        cfg=cfg,
        chronological=False,
    )
    _save_templates(parser, paths.processed / "hdfs_templates.csv")
    sequences.drop(columns=["event_ids"], errors="ignore").to_csv(
        paths.processed / "hdfs_sessions_meta.csv", index=False
    )
    joblib.dump(scores, paths.artifacts / "hdfs_scores.joblib")
    return {"table": table, "curve": curve, "n_templates": n_templates, "n_seq": len(sequences)}


def run_bgl(
    log_path: Path,
    *,
    windows: tuple[int, ...] = BGL_WINDOWS_SEC,
    max_lines: int | None,
    cfg: DetectorConfig,
    paths: Paths,
) -> dict:
    events, parser = parse_bgl_log(log_path, max_lines=max_lines)
    n_templates = len(parser.templates())
    _save_templates(parser, paths.processed / "bgl_templates.csv")
    tables, curves = [], []
    dashboard = {}
    for window in windows:
        sequences = build_bgl_windows(events, window_sec=window)
        table, curve, scores = evaluate_sequences(
            sequences,
            dataset="bgl",
            grouping=f"window_{window}s",
            n_log_lines=len(events),
            n_templates=n_templates,
            cfg=cfg,
            chronological=True,
        )
        tables.append(table)
        curves.append(curve)
        dashboard[str(window)] = _flagged_windows(
            sequences, scores, events, window_sec=window
        )
        sequences.drop(columns=["event_ids", "contents", "line_nos"], errors="ignore").to_csv(
            paths.processed / f"bgl_windows_{window}s.csv", index=False
        )
    (paths.artifacts / "bgl_flagged.json").write_text(
        json.dumps(dashboard, indent=2), encoding="utf-8"
    )
    return {
        "table": pd.concat(tables, ignore_index=True),
        "curve": pd.concat(curves, ignore_index=True),
        "n_templates": n_templates,
    }


def write_reports(table: pd.DataFrame, curve: pd.DataFrame, paths: Paths) -> dict[str, Path]:
    paths.ensure()
    metrics_path = paths.reports / "metrics.csv"
    curve_path = paths.reports / "curves.csv"
    table.to_csv(metrics_path, index=False)
    curve.to_csv(curve_path, index=False)
    trade = window_tradeoff_table(table)
    trade_path = paths.reports / "window_tradeoff.csv"
    trade.to_csv(trade_path, index=False)

    figs = {}
    bgl_curve = curve[curve["dataset"] == "bgl"]
    if len(bgl_curve):
        figs["window"] = plot_window_tradeoff(
            bgl_curve, paths.figures / "window_size_tradeoff.png"
        )
    figs["alerts"] = plot_alert_volume(table, paths.figures / "alert_volume.png")
    figs["fpr"] = plot_fpr_at_recall(table, paths.figures / "fpr_at_80_recall.png")
    return {"metrics": metrics_path, "curves": curve_path, "tradeoff": trade_path, **figs}


def run_pipeline(
    *,
    hdfs_log: Path | None,
    hdfs_labels: Path | None,
    bgl_log: Path | None,
    windows: tuple[int, ...] = BGL_WINDOWS_SEC,
    max_lines: int | None = None,
    cfg: DetectorConfig | None = None,
) -> pd.DataFrame:
    cfg = cfg or DetectorConfig()
    paths = Paths().ensure()
    frames = []
    curves = []
    if hdfs_log and hdfs_labels and hdfs_log.exists():
        result = run_hdfs(hdfs_log, hdfs_labels, max_lines=max_lines, cfg=cfg, paths=paths)
        frames.append(result["table"])
        curves.append(result["curve"])
    if bgl_log and bgl_log.exists():
        result = run_bgl(
            bgl_log, windows=windows, max_lines=max_lines, cfg=cfg, paths=paths
        )
        frames.append(result["table"])
        curves.append(result["curve"])
    if not frames:
        raise FileNotFoundError("No dataset paths found. Run demo or download LogHub files.")
    table = pd.concat(frames, ignore_index=True)
    curve = pd.concat(curves, ignore_index=True)
    write_reports(table, curve, paths)
    return table
