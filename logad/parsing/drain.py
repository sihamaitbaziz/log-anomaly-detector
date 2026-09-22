from __future__ import annotations

import re
from dataclasses import dataclass, field


_DEFAULT_MASKS = [
    (re.compile(r"blk_-?\d+"), "<BLK>"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b"), "<IP>"),
    (re.compile(r"\b[0-9a-fA-F]{8,}\b"), "<HEX>"),
    (re.compile(r"(?<=[^A-Za-z0-9])-?\d+(?:\.\d+)?"), "<NUM>"),
    (re.compile(r"\b\d+\b"), "<NUM>"),
]


def mask_variables(message: str) -> str:
    out = message
    for pattern, token in _DEFAULT_MASKS:
        out = pattern.sub(token, out)
    return out


def tokenize(message: str) -> list[str]:
    return [tok for tok in message.strip().split() if tok]


def template_from_tokens(tokens: list[str]) -> str:
    return " ".join(tokens)


@dataclass
class LogCluster:
    cluster_id: int
    log_template_tokens: list[str]
    size: int = 0

    def similarity(self, tokens: list[str]) -> float:
        if not tokens or len(tokens) != len(self.log_template_tokens):
            return 0.0
        same = sum(a == b for a, b in zip(tokens, self.log_template_tokens))
        return same / len(tokens)

    def absorb(self, tokens: list[str]) -> None:
        self.log_template_tokens = [
            a if a == b else "<*>" for a, b in zip(self.log_template_tokens, tokens)
        ]
        self.size += 1


@dataclass
class _Node:
    children: dict = field(default_factory=dict)
    clusters: list[LogCluster] = field(default_factory=list)


class DrainParser:
    """Drain-style parse tree (He et al., ICWS 2017).

    Collapses parameterized log lines into event templates so that
    ``deleting block blk_A`` and ``deleting block blk_B`` become one event.
    """

    def __init__(
        self,
        depth: int = 4,
        similarity_threshold: float = 0.5,
        max_children: int = 100,
        max_clusters: int = 10_000,
        apply_masks: bool = True,
    ) -> None:
        if depth < 3:
            raise ValueError("Drain depth must be >= 3")
        self.depth = depth
        self.similarity_threshold = similarity_threshold
        self.max_children = max_children
        self.max_clusters = max_clusters
        self.apply_masks = apply_masks
        self.root = _Node()
        self.clusters: list[LogCluster] = []
        self._id_to_template: dict[int, str] = {}

    def add(self, message: str) -> int:
        tokens = tokenize(mask_variables(message) if self.apply_masks else message)
        if not tokens:
            tokens = ["<EMPTY>"]
        cluster = self._tree_search(tokens)
        if cluster is None:
            cluster = self._create_cluster(tokens)
        else:
            cluster.absorb(tokens)
        self._id_to_template[cluster.cluster_id] = template_from_tokens(
            cluster.log_template_tokens
        )
        return cluster.cluster_id

    def template_of(self, event_id: int) -> str:
        return self._id_to_template.get(event_id, "<UNKNOWN>")

    def templates(self) -> dict[int, str]:
        return dict(self._id_to_template)

    def _tree_search(self, tokens: list[str]) -> LogCluster | None:
        node = self.root.children.get(len(tokens))
        if node is None:
            return None
        current = node
        token_count = len(tokens)
        for depth in range(1, min(self.depth, token_count) ):
            token = tokens[depth - 1]
            if token not in current.children:
                token = "<*>"
                if token not in current.children:
                    return None
            current = current.children[token]
        return self._best_cluster(current.clusters, tokens)

    def _best_cluster(self, clusters: list[LogCluster], tokens: list[str]) -> LogCluster | None:
        best = None
        best_sim = -1.0
        for cluster in clusters:
            sim = cluster.similarity(tokens)
            if sim > best_sim:
                best, best_sim = cluster, sim
        if best is not None and best_sim >= self.similarity_threshold:
            return best
        return None

    def _create_cluster(self, tokens: list[str]) -> LogCluster:
        if len(self.clusters) >= self.max_clusters:
            return self.clusters[-1]

        cluster = LogCluster(
            cluster_id=len(self.clusters),
            log_template_tokens=list(tokens),
            size=1,
        )
        self.clusters.append(cluster)

        length = len(tokens)
        if length not in self.root.children:
            self.root.children[length] = _Node()
        current = self.root.children[length]
        token_count = len(tokens)
        for depth in range(1, min(self.depth, token_count)):
            token = tokens[depth - 1]
            if token not in current.children:
                if len(current.children) >= self.max_children:
                    token = "<*>"
                    if token not in current.children:
                        current.children[token] = _Node()
                else:
                    current.children[token] = _Node()
            current = current.children[token]
        current.clusters.append(cluster)
        return cluster
