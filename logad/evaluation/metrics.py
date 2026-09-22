from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass
class OperatingPoint:
    threshold: float
    precision: float
    recall: float
    fpr: float
    f1: float
    tp: int
    fp: int
    tn: int
    fn: int
    n_alerts: int
    alerts_per_million_lines: float


def _confusion(y_true: np.ndarray, y_hat: np.ndarray) -> tuple[int, int, int, int]:
    tp = int(np.sum((y_true == 1) & (y_hat == 1)))
    fp = int(np.sum((y_true == 0) & (y_hat == 1)))
    tn = int(np.sum((y_true == 0) & (y_hat == 0)))
    fn = int(np.sum((y_true == 1) & (y_hat == 0)))
    return tp, fp, tn, fn


def point_from_predictions(
    y_true: np.ndarray,
    y_hat: np.ndarray,
    threshold: float,
    n_log_lines: int,
) -> OperatingPoint:
    tp, fp, tn, fn = _confusion(y_true, y_hat)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    n_alerts = tp + fp
    per_m = (n_alerts / n_log_lines * 1_000_000) if n_log_lines else float("nan")
    return OperatingPoint(
        threshold=float(threshold),
        precision=precision,
        recall=recall,
        fpr=fpr,
        f1=f1,
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        n_alerts=n_alerts,
        alerts_per_million_lines=per_m,
    )


def _thresholds(scores: np.ndarray, max_points: int = 400) -> np.ndarray:
    uniq = np.unique(scores)
    uniq = np.sort(uniq)[::-1]
    if len(uniq) > max_points:
        idx = np.linspace(0, len(uniq) - 1, max_points).astype(int)
        uniq = uniq[idx]
    return uniq


def sweep_threshold(
    y_true: np.ndarray, scores: np.ndarray, n_log_lines: int
) -> list[OperatingPoint]:
    points = []
    for thr in _thresholds(scores):
        y_hat = (scores >= thr).astype(int)
        points.append(point_from_predictions(y_true, y_hat, thr, n_log_lines))
    return points


def closest_recall(points: list[OperatingPoint], target: float) -> OperatingPoint:
    return min(points, key=lambda p: (abs(p.recall - target), p.fpr))


def closest_fpr(points: list[OperatingPoint], target: float) -> OperatingPoint:
    return min(points, key=lambda p: (abs(p.fpr - target), -p.recall))


def precision_at_k(
    y_true: np.ndarray, scores: np.ndarray, k: int, n_log_lines: int
) -> OperatingPoint:
    k = max(1, min(int(k), len(scores)))
    order = np.argsort(-scores)[:k]
    y_hat = np.zeros_like(y_true)
    y_hat[order] = 1
    # threshold is the k-th score
    thr = scores[order[-1]]
    return point_from_predictions(y_true, y_hat, thr, n_log_lines)


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    pos = scores[y_true == 1]
    neg = scores[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    # Mann–Whitney / Wilcoxon
    # P(score_pos > score_neg) + 0.5 P(eq)
    pos = pos.astype(np.float64)
    neg = neg.astype(np.float64)
    n_gt = 0.0
    for p in pos:
        n_gt += np.sum(p > neg) + 0.5 * np.sum(p == neg)
    return float(n_gt / (len(pos) * len(neg)))


def summarize_run(
    *,
    dataset: str,
    grouping: str,
    model: str,
    y_true: np.ndarray,
    scores: np.ndarray,
    n_log_lines: int,
    n_templates: int,
    n_sequences: int,
    anomaly_rate: float,
    recall_targets: tuple[float, ...] = (0.5, 0.8, 0.9),
    fpr_targets: tuple[float, ...] = (0.001, 0.005, 0.01, 0.05),
    alert_budgets: tuple[int, ...] = (50, 100, 500, 1000),
) -> dict:
    points = sweep_threshold(y_true, scores, n_log_lines)
    auc = roc_auc(y_true, scores)
    rows: list[dict] = []
    base = {
        "dataset": dataset,
        "grouping": grouping,
        "model": model,
        "n_log_lines": n_log_lines,
        "n_templates": n_templates,
        "n_sequences": n_sequences,
        "anomaly_rate": anomaly_rate,
        "roc_auc": auc,
    }
    for target in recall_targets:
        op = closest_recall(points, target)
        row = {**base, "slice": f"recall≈{target:.2f}", **asdict(op)}
        rows.append(row)
    for target in fpr_targets:
        op = closest_fpr(points, target)
        row = {**base, "slice": f"fpr≈{target:.3f}", **asdict(op)}
        rows.append(row)
    for k in alert_budgets:
        if k > len(y_true):
            continue
        op = precision_at_k(y_true, scores, k, n_log_lines)
        row = {**base, "slice": f"budget={k}", **asdict(op)}
        rows.append(row)

    # Human-handleable default: FPR that yields <= 200 alerts on this split
    cheap = [p for p in points if p.n_alerts <= 200]
    if cheap:
        op = max(cheap, key=lambda p: p.recall)
        rows.append({**base, "slice": "max_recall@≤200_alerts", **asdict(op)})

    return {
        "table": pd.DataFrame(rows),
        "curve": pd.DataFrame([asdict(p) | base for p in points]),
        "auc": auc,
    }
