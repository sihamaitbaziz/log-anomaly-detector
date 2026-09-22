from pathlib import Path

from logad.parsing.drain import DrainParser
from logad.parsing.hdfs import load_hdfs_labels, parse_hdfs_log
from logad.sequences.hdfs_sessions import build_hdfs_sessions
from logad.synthetic import write_synthetic_hdfs


def test_drain_collapses_block_ids(tmp_path: Path) -> None:
    parser = DrainParser()
    a = parser.add("deleting block blk_-1608999687919862906")
    b = parser.add("deleting block blk_7503483334202473044")
    assert a == b
    assert "<*>" in parser.template_of(a) or "<BLK>" in parser.template_of(a)


def test_hdfs_sessions_and_labels(tmp_path: Path) -> None:
    log_path, label_path = write_synthetic_hdfs(tmp_path, n_blocks=40, seed=3)
    events, parser = parse_hdfs_log(log_path, show_progress=False)
    labels = load_hdfs_labels(label_path)
    sessions = build_hdfs_sessions(events, labels)
    assert len(parser.templates()) >= 3
    assert sessions["y"].sum() > 0
    assert sessions["seq_id"].nunique() == 40
