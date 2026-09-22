from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from scipy import sparse


def sequences_to_count_matrix(
    sequences: pd.DataFrame, n_events: int | None = None
) -> tuple[sparse.csr_matrix, np.ndarray, np.ndarray]:
    """Bag-of-templates: each sequence becomes a count vector over event ids."""
    if n_events is None:
        n_events = int(max((max(ids) if ids else 0) for ids in sequences["event_ids"])) + 1

    indptr = [0]
    indices: list[int] = []
    data: list[int] = []
    for event_ids in sequences["event_ids"]:
        counts = Counter(int(e) for e in event_ids)
        for event_id, count in sorted(counts.items()):
            if 0 <= event_id < n_events:
                indices.append(event_id)
                data.append(count)
        indptr.append(len(indices))

    matrix = sparse.csr_matrix(
        (data, indices, indptr), shape=(len(sequences), n_events), dtype=np.float32
    )
    y = sequences["y"].to_numpy(dtype=int)
    seq_ids = sequences["seq_id"].to_numpy()
    return matrix, y, seq_ids


def log1p_tf(matrix: sparse.spmatrix) -> sparse.csr_matrix:
    matrix = matrix.tocsr(copy=True)
    matrix.data = np.log1p(matrix.data)
    return matrix
