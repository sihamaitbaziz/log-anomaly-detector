from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from logad.parsing.drain import DrainParser

BLOCK_RE = re.compile(r"(blk_-?\d+)")
HDFS_LINE_RE = re.compile(
    r"^(?P<date>\d{6})\s+(?P<time>\d{6})\s+(?P<pid>\d+)\s+"
    r"(?P<level>\S+)\s+(?P<component>\S+):\s+(?P<content>.*)$"
)


@dataclass
class ParsedLine:
    line_no: int
    content: str
    event_id: int
    block_ids: list[str]
    raw: str


def iter_hdfs_lines(path: Path) -> Iterator[tuple[int, str, str]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, start=1):
            raw = raw.rstrip("\n")
            if not raw:
                continue
            match = HDFS_LINE_RE.match(raw)
            content = match.group("content") if match else raw
            yield line_no, raw, content


def parse_hdfs_log(
    log_path: Path,
    parser: DrainParser | None = None,
    max_lines: int | None = None,
    show_progress: bool = True,
) -> tuple[pd.DataFrame, DrainParser]:
    """Parse HDFS lines and explode each mentioned block id into a session event."""
    parser = parser or DrainParser()
    rows: list[dict] = []
    iterator = iter_hdfs_lines(log_path)
    if show_progress:
        iterator = tqdm(iterator, desc="Parse HDFS", unit="line")

    for line_no, raw, content in iterator:
        if max_lines is not None and line_no > max_lines:
            break
        event_id = parser.add(content)
        block_ids = BLOCK_RE.findall(raw)
        if not block_ids:
            continue
        for block_id in dict.fromkeys(block_ids):
            rows.append(
                {
                    "line_no": line_no,
                    "block_id": block_id,
                    "event_id": event_id,
                    "content": content,
                }
            )
    events = pd.DataFrame(rows)
    return events, parser


def load_hdfs_labels(label_path: Path) -> pd.DataFrame:
    labels = pd.read_csv(label_path)
    labels.columns = [c.strip() for c in labels.columns]
    if "BlockId" in labels.columns:
        labels = labels.rename(columns={"BlockId": "block_id", "Label": "label"})
    labels["y"] = (labels["label"].astype(str).str.lower() != "normal").astype(int)
    return labels[["block_id", "y", "label"]]
