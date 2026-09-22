from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from logad.parsing.drain import DrainParser


def iter_bgl_lines(path: Path) -> Iterator[tuple[int, str, dict]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, start=1):
            raw = raw.rstrip("\n")
            if not raw:
                continue
            parts = raw.split(None, 9)
            if len(parts) < 10:
                label, timestamp, content = "-", 0, raw
            else:
                label = parts[0]
                try:
                    timestamp = int(parts[1])
                except ValueError:
                    timestamp = 0
                content = parts[9]
            yield line_no, raw, {
                "label": label,
                "timestamp": timestamp,
                "content": content,
                "is_alert": int(label != "-"),
            }


def parse_bgl_log(
    log_path: Path,
    parser: DrainParser | None = None,
    max_lines: int | None = None,
    show_progress: bool = True,
) -> tuple[pd.DataFrame, DrainParser]:
    parser = parser or DrainParser()
    rows: list[dict] = []
    iterator = iter_bgl_lines(log_path)
    if show_progress:
        iterator = tqdm(iterator, desc="Parse BGL", unit="line")

    for line_no, raw, fields in iterator:
        if max_lines is not None and line_no > max_lines:
            break
        event_id = parser.add(fields["content"])
        rows.append(
            {
                "line_no": line_no,
                "timestamp": fields["timestamp"],
                "event_id": event_id,
                "is_alert": fields["is_alert"],
                "alert_type": fields["label"],
                "content": fields["content"],
            }
        )
    return pd.DataFrame(rows), parser
