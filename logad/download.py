from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

from logad.config import BGL_URL, HDFS_URL, RAW_DIR


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"Already present: {dest}")
        return dest
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, dest)
    return dest


def _extract(archive: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(out_dir)


def find_file(root: Path, name: str) -> Path | None:
    matches = list(root.rglob(name))
    return matches[0] if matches else None


def download_loghub(dest: Path | None = None, datasets: tuple[str, ...] = ("hdfs", "bgl")) -> dict[str, Path]:
    dest = dest or RAW_DIR
    dest.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    if "hdfs" in datasets:
        archive = _download(HDFS_URL, dest / "HDFS_1.tar.gz")
        _extract(archive, dest / "hdfs")
        log = find_file(dest / "hdfs", "HDFS.log")
        labels = find_file(dest / "hdfs", "anomaly_label.csv")
        if log:
            found["hdfs_log"] = log
        if labels:
            found["hdfs_labels"] = labels
    if "bgl" in datasets:
        archive = _download(BGL_URL, dest / "BGL.tar.gz")
        _extract(archive, dest / "bgl")
        log = find_file(dest / "bgl", "BGL.log")
        if log:
            found["bgl_log"] = log
    return found
