from logad.parsing.bgl import parse_bgl_log
from logad.pipeline import run_pipeline
from logad.sequences.bgl_windows import build_bgl_windows
from logad.synthetic import write_synthetic_bgl, write_synthetic_hdfs


def test_bgl_window_labels_change_with_size(tmp_path) -> None:
    log_path = write_synthetic_bgl(tmp_path, n_lines=800, seed=4)
    events, _ = parse_bgl_log(log_path, show_progress=False)
    small = build_bgl_windows(events, 30)
    large = build_bgl_windows(events, 300)
    assert len(small) > len(large)
    # Larger windows absorb alerts, so anomaly *rate* typically rises.
    assert large["y"].mean() >= small["y"].mean()


def test_demo_pipeline_writes_metrics(tmp_path) -> None:
    hdfs_log, hdfs_labels = write_synthetic_hdfs(tmp_path / "h", n_blocks=120, seed=5)
    bgl_log = write_synthetic_bgl(tmp_path / "b", n_lines=1200, seed=6)
    table = run_pipeline(
        hdfs_log=hdfs_log,
        hdfs_labels=hdfs_labels,
        bgl_log=bgl_log,
        windows=(30, 60, 300),
        max_lines=None,
    )
    assert {"hdfs", "bgl"} <= set(table["dataset"])
    assert "recall≈0.80" in set(table["slice"])
    assert (table["fpr"] >= 0).all()
