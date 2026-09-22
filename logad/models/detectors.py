from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def _to_dense(x: sparse.spmatrix | np.ndarray) -> np.ndarray:
    if sparse.issparse(x):
        return x.toarray()
    return np.asarray(x)


@dataclass
class ScoredDetector:
    name: str

    def fit(self, x_train: sparse.spmatrix | np.ndarray) -> "ScoredDetector":
        raise NotImplementedError

    def score(self, x: sparse.spmatrix | np.ndarray) -> np.ndarray:
        """Higher score = more anomalous."""
        raise NotImplementedError


class IsolationForestDetector(ScoredDetector):
    def __init__(self, n_estimators: int = 200, random_state: int = 42, n_jobs: int = -1):
        super().__init__(name="isolation_forest")
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination="auto",
            random_state=random_state,
            n_jobs=n_jobs,
        )

    def fit(self, x_train: sparse.spmatrix | np.ndarray) -> "IsolationForestDetector":
        self.model.fit(_to_dense(x_train))
        return self

    def score(self, x: sparse.spmatrix | np.ndarray) -> np.ndarray:
        return -self.model.decision_function(_to_dense(x))


class PCADetector(ScoredDetector):
    """PCA / TruncatedSVD reconstruction error on count vectors."""

    def __init__(self, variance: float = 0.90, random_state: int = 42):
        super().__init__(name="pca")
        self.variance = variance
        self.random_state = random_state
        self.scaler = StandardScaler(with_mean=True, with_std=True)
        self.svd: TruncatedSVD | None = None
        self.n_components: int = 1

    def fit(self, x_train: sparse.spmatrix | np.ndarray) -> "PCADetector":
        dense = _to_dense(x_train)
        scaled = self.scaler.fit_transform(dense)
        max_comp = max(1, min(scaled.shape[0] - 1, scaled.shape[1] - 1, 64))
        probe = TruncatedSVD(n_components=max_comp, random_state=self.random_state)
        probe.fit(scaled)
        cum = np.cumsum(probe.explained_variance_ratio_)
        self.n_components = int(max(1, int(np.searchsorted(cum, self.variance) + 1)))
        self.n_components = min(self.n_components, max_comp)
        self.svd = TruncatedSVD(
            n_components=self.n_components, random_state=self.random_state
        )
        self.svd.fit(scaled)
        return self

    def score(self, x: sparse.spmatrix | np.ndarray) -> np.ndarray:
        if self.svd is None:
            raise RuntimeError("PCADetector must be fit before scoring")
        scaled = self.scaler.transform(_to_dense(x))
        projected = self.svd.transform(scaled)
        reconstructed = self.svd.inverse_transform(projected)
        return np.mean((scaled - reconstructed) ** 2, axis=1)
