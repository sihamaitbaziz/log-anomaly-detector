
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from logad.config import BGL_WINDOWS_SEC, DetectorConfig, Paths, DATASET_CITATION  
from logad.download import download_loghub, find_file  
from logad.pipeline import run_pipeline  
from logad.synthetic import write_synthetic_bgl, write_synthetic_hdfs  


def cmd_demo(args: argparse.Namespace) -> None:
    raw = Paths().ensure().raw / "demo"
    hdfs_log, hdfs_labels = write_synthetic_hdfs(raw / "hdfs", n_blocks=args.demo_blocks)
    bgl_log = write_synthetic_bgl(raw / "bgl", n_lines=args.demo_lines)
    table = run_pipeline(
        hdfs_log=hdfs_log,
        hdfs_labels=hdfs_labels,
        bgl_log=bgl_log,
        windows=tuple(args.windows),
        max_lines=None,
        cfg=DetectorConfig(n_estimators=args.trees, n_jobs=1),
    )
    print("\n=== metrics (synthetic demo — replace with LogHub numbers for the resume) ===")
    cols = [
        "dataset",
        "grouping",
        "model",
        "slice",
        "precision",
        "recall",
        "fpr",
        "n_alerts",
        "alerts_per_million_lines",
        "roc_auc",
    ]
    view = table[table["slice"].isin(["recall≈0.80", "fpr≈0.010", "budget=100"])]
    print(view[cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"\nWrote reports/metrics.csv and reports/figures/")
    print("Launch the triage UI with:  python main.py dashboard")


def cmd_download(args: argparse.Namespace) -> None:
    found = download_loghub(datasets=tuple(args.datasets))
    for key, path in found.items():
        print(f"{key}: {path}")
    if not found:
        print("Download finished but files were not found. Inspect data/raw/")


def cmd_run(args: argparse.Namespace) -> None:
    raw = Paths().ensure().raw
    hdfs_log = Path(args.hdfs_log) if args.hdfs_log else find_file(raw, "HDFS.log")
    hdfs_labels = (
        Path(args.hdfs_labels) if args.hdfs_labels else find_file(raw, "anomaly_label.csv")
    )
    bgl_log = Path(args.bgl_log) if args.bgl_log else find_file(raw, "BGL.log")
    table = run_pipeline(
        hdfs_log=hdfs_log,
        hdfs_labels=hdfs_labels,
        bgl_log=bgl_log,
        windows=tuple(args.windows),
        max_lines=args.max_lines,
        cfg=DetectorConfig(n_estimators=args.trees, n_jobs=args.jobs),
    )
    print("\n=== LogHub run ===")
    print(DATASET_CITATION)
    cols = [
        "dataset",
        "grouping",
        "model",
        "slice",
        "precision",
        "recall",
        "fpr",
        "n_alerts",
        "alerts_per_million_lines",
        "roc_auc",
    ]
    view = table[table["slice"].isin(["recall≈0.80", "fpr≈0.010", "max_recall@≤200_alerts"])]
    print(view[cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nFull table: reports/metrics.csv")


def cmd_dashboard(_: argparse.Namespace) -> None:
    app = ROOT / "dashboard" / "app.py"
    subprocess.check_call([sys.executable, "-m", "streamlit", "run", str(app)])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Session-based log anomaly detector")
    sub = parser.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="Synthetic HDFS + BGL, end-to-end in minutes")
    demo.add_argument("--windows", nargs="+", type=int, default=list(BGL_WINDOWS_SEC))
    demo.add_argument("--demo-blocks", type=int, default=800)
    demo.add_argument("--demo-lines", type=int, default=4000)
    demo.add_argument("--trees", type=int, default=120)
    demo.set_defaults(func=cmd_demo)

    dl = sub.add_parser("download", help="Fetch LogHub HDFS_1 and BGL from Zenodo")
    dl.add_argument("--datasets", nargs="+", default=["hdfs", "bgl"], choices=["hdfs", "bgl"])
    dl.set_defaults(func=cmd_download)

    run = sub.add_parser("run", help="Train/evaluate on local LogHub files")
    run.add_argument("--hdfs-log", type=str, default=None)
    run.add_argument("--hdfs-labels", type=str, default=None)
    run.add_argument("--bgl-log", type=str, default=None)
    run.add_argument("--windows", nargs="+", type=int, default=list(BGL_WINDOWS_SEC))
    run.add_argument("--max-lines", type=int, default=None, help="Optional cap for smoke tests")
    run.add_argument("--trees", type=int, default=200)
    run.add_argument("--jobs", type=int, default=1)
    run.set_defaults(func=cmd_run)

    dash = sub.add_parser("dashboard", help="SOC-style triage UI")
    dash.set_defaults(func=cmd_dashboard)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
