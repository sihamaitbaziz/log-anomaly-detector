import numpy as np

from logad.evaluation.metrics import point_from_predictions, precision_at_k, roc_auc


def test_fpr_is_fp_over_negatives() -> None:
    y = np.array([0, 0, 0, 0, 1, 1])
    y_hat = np.array([1, 0, 0, 0, 1, 0])
    op = point_from_predictions(y, y_hat, threshold=0.5, n_log_lines=1000)
    assert op.fp == 1
    assert op.tn == 3
    assert abs(op.fpr - 0.25) < 1e-9
    assert abs(op.alerts_per_million_lines - 2000) < 1e-6


def test_precision_at_k_and_auc() -> None:
    y = np.array([1, 0, 1, 0])
    scores = np.array([0.9, 0.8, 0.1, 0.0])
    op = precision_at_k(y, scores, k=2, n_log_lines=100)
    assert op.precision == 0.5
    assert roc_auc(y, scores) > 0.5
