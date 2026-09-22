from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


HDFS_TEMPLATES = [
    "Receiving block <BLK> src: <IP> dest: <IP>",
    "PacketResponder <NUM> for block <BLK> terminating",
    "Received block <BLK> of size <NUM> from <IP>",
    "Deleting block <BLK> file /user/root/rand/_temporary",
    "Verification succeeded for <BLK>",
    "writeBlock <BLK> received exception",
    "Unexpected error trying to delete block <BLK>",
]

BGL_TEMPLATES = [
    "instruction cache parity error corrected",
    "data storage interrupt",
    "generating core.<NUM>",
    "ciod: Error creating node map from file",
    "total of <NUM> ddr error(s) detected and corrected",
    "kernel panic",
    "external input interrupt",
]


def write_synthetic_hdfs(out_dir: Path, n_blocks: int = 800, seed: int = 0) -> tuple[Path, Path]:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "HDFS.log"
    label_path = out_dir / "anomaly_label.csv"

    lines: list[str] = []
    labels: list[tuple[str, str]] = []
    line_clock = 203518
    n_anom = max(40, n_blocks // 20)

    for i in range(n_blocks):
        blk = f"blk_{-1600000000000000000 + i}"
        is_anom = i < n_anom
        labels.append((blk, "Anomaly" if is_anom else "Normal"))
        n_events = int(rng.integers(6, 14))
        if is_anom:
            n_events += int(rng.integers(8, 25))
        for _ in range(n_events):
            if is_anom and rng.random() < 0.35:
                tmpl = HDFS_TEMPLATES[rng.choice([5, 6])]
            else:
                tmpl = HDFS_TEMPLATES[int(rng.integers(0, 5))]
            content = tmpl.replace("<BLK>", blk).replace("<IP>", "10.250.19.102:50010").replace(
                "<NUM>", str(int(rng.integers(1, 9)))
            )
            pid = int(rng.integers(100, 999))
            lines.append(
                f"081109 {line_clock:06d} {pid} INFO dfs.DataNode$DataXceiver: {content}"
            )
            line_clock += 1

    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pd.DataFrame(labels, columns=["BlockId", "Label"]).to_csv(label_path, index=False)
    return log_path, label_path


def write_synthetic_bgl(out_dir: Path, n_lines: int = 4000, seed: int = 1) -> Path:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "BGL.log"
    t0 = 1_117_838_570
    rows: list[str] = []
    alert_windows = {12, 13, 40, 41, 90, 110, 125}

    for i in range(n_lines):
        ts = t0 + i * 2  # ~2 seconds per line, dense enough for 30/60/300s windows
        window = (ts - t0) // 60
        is_alert = window in alert_windows and rng.random() < 0.55
        decoy = window in {20, 55, 70, 100} and rng.random() < 0.4
        if is_alert:
            label = rng.choice(["KERNDTLB", "KERNSTOR", "APPFATAL"])
            # Many BGL alerts share templates with healthy lines — counts, not keywords.
            if rng.random() < 0.55:
                content = BGL_TEMPLATES[int(rng.integers(0, 5))]
            else:
                content = rng.choice(BGL_TEMPLATES[5:7])
        elif decoy:
            label = "-"
            content = rng.choice(BGL_TEMPLATES[4:7])
        else:
            label = "-"
            content = BGL_TEMPLATES[int(rng.integers(0, 5))]
        content = content.replace("<NUM>", str(int(rng.integers(1, 20))))
        node = "R02-M1-N0-C:J12-U11"
        date = "2005.06.03"
        timestr = "2005-06-03-15.42.50.363779"
        rows.append(
            f"{label} {ts} {date} {node} {timestr} {node} RAS KERNEL INFO {content}"
        )
    log_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return log_path
