from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ARTIFACTS_DIR = ROOT / "artifacts"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

HDFS_URL = "https://zenodo.org/records/3227177/files/HDFS_1.tar.gz"
BGL_URL = "https://zenodo.org/records/3227177/files/BGL.tar.gz"

# LogHub / Zenodo record 3227177 (LogPAI LogHub v1 dumps).
DATASET_CITATION = (
    "LogHub (Zenodo record 3227177), HDFS_1.tar.gz and BGL.tar.gz. "
    "HDFS_v1: 11,175,629 lines with block-level Normal/Anomaly labels. "
    "BGL: 4,747,963 lines; first token '-' = non-alert, otherwise alert."
)

BGL_WINDOWS_SEC = (30, 60, 300)


@dataclass(frozen=True)
class DrainConfig:
    depth: int = 4
    similarity_threshold: float = 0.5
    max_children: int = 100
    max_clusters: int = 10_000


@dataclass
class DetectorConfig:
    random_state: int = 42
    pca_variance: float = 0.90
    n_estimators: int = 200
    n_jobs: int = 1
    recall_targets: tuple[float, ...] = (0.50, 0.80, 0.90)
    fpr_targets: tuple[float, ...] = (0.001, 0.005, 0.01, 0.05)
    alert_budgets: tuple[int, ...] = (50, 100, 500, 1000)


@dataclass
class Paths:
    raw: Path = RAW_DIR
    processed: Path = PROCESSED_DIR
    artifacts: Path = ARTIFACTS_DIR
    reports: Path = REPORTS_DIR
    figures: Path = FIGURES_DIR
    extra: dict = field(default_factory=dict)

    def ensure(self) -> "Paths":
        for p in (self.raw, self.processed, self.artifacts, self.reports, self.figures):
            p.mkdir(parents=True, exist_ok=True)
        return self
