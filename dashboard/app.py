from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from logad.config import ARTIFACTS_DIR, FIGURES_DIR, REPORTS_DIR
from logad.parsing.bgl import parse_bgl_log
from logad.parsing.drain import DrainParser
from logad.sequences.bgl_windows import build_bgl_windows

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Log Anomaly Monitor",
    page_icon="◌",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
<style>

    /* ========================================================
       GLOBAL
       ======================================================== */

    .stApp {
        background-color: #f7f8fa;
        color: #263238;
    }

    .main .block-container {
        max-width: 1400px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }

    h1 {
        color: #263238 !important;
        font-weight: 650 !important;
        letter-spacing: -0.025em;
    }

    h2 {
        color: #34434f !important;
        font-weight: 600 !important;
        letter-spacing: -0.015em;
        margin-top: 1.6rem !important;
    }

    h3 {
        color: #465661 !important;
        font-weight: 600 !important;
    }

    p {
        color: #63727d;
    }

    hr {
        border: none;
        border-top: 1px solid #e3e7eb;
        margin: 2rem 0;
    }


    /* ========================================================
       SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e8ec;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 2rem;
    }


    /* ========================================================
       KPI CARDS
       ======================================================== */

    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e6ea;
        border-radius: 10px;
        padding: 17px 19px;
        min-height: 108px;
        box-shadow: 0 1px 2px rgba(30, 40, 50, 0.025);
    }

    .kpi-label {
        color: #78858f;
        font-size: 0.73rem;
        font-weight: 500;
        margin-bottom: 7px;
    }

    .kpi-value {
        color: #263238;
        font-size: 1.55rem;
        line-height: 1.1;
        font-weight: 650;
    }

    .kpi-description {
        color: #9aa3aa;
        font-size: 0.68rem;
        margin-top: 7px;
    }


    /* ========================================================
       ALERT ROWS
       ======================================================== */

    .alert-row {
        background: #ffffff;
        border: 1px solid #e5e8ec;
        border-radius: 8px;
        padding: 11px 14px;
        margin-bottom: 7px;
    }

    .alert-row:hover {
        border-color: #ccd4da;
    }

    .alert-id {
        color: #35444f;
        font-size: 0.88rem;
        font-weight: 600;
    }

    .alert-meta {
        color: #7c8891;
        font-size: 0.74rem;
        margin-top: 4px;
    }

    .anomaly-text {
        color: #a65050;
        font-weight: 600;
    }

    .normal-text {
        color: #69757d;
        font-weight: 500;
    }


    /* ========================================================
       SIDEBAR BRAND
       ======================================================== */

    .sidebar-brand {
        margin-bottom: 1.5rem;
    }

    .sidebar-title {
        color: #263238;
        font-size: 1.08rem;
        font-weight: 650;
    }

    .sidebar-subtitle {
        color: #89949c;
        font-size: 0.72rem;
        margin-top: 3px;
    }


    /* ========================================================
       SMALL LABELS
       ======================================================== */

    .eyebrow {
        color: #77858f;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }

    .muted {
        color: #849099;
        font-size: 0.75rem;
    }


    /* ========================================================
       STREAMLIT TABLE
       ======================================================== */

    div[data-testid="stDataFrame"] {
        border: 1px solid #e4e8eb;
        border-radius: 8px;
        overflow: hidden;
    }


    /* ========================================================
       BUTTONS
       ======================================================== */

    .stButton > button {
        border: 1px solid #d8dee3;
        border-radius: 7px;
        background: #ffffff;
        color: #465661;
    }

    .stButton > button:hover {
        border-color: #aeb8bf;
        color: #263238;
    }


    /* ========================================================
       FILE UPLOADER
       ======================================================== */

    [data-testid="stFileUploader"] {
        border-radius: 8px;
    }

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADING
# ============================================================


@st.cache_data
def load_metrics() -> pd.DataFrame | None:
    """Load experiment metrics."""

    path = REPORTS_DIR / "metrics.csv"

    if not path.exists():
        return None

    return pd.read_csv(path)


@st.cache_data
def load_flagged_windows() -> dict | None:
    """Load precomputed BGL flagged windows."""

    path = ARTIFACTS_DIR / "bgl_flagged.json"

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


metrics = load_metrics()
flagged_payload = load_flagged_windows()


# ============================================================
# SMALL UI HELPERS
# ============================================================


def metric_card(
    label: str,
    value: str,
    description: str,
) -> None:
    """Render a single KPI card."""

    html = textwrap.dedent(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-description">{description}</div>
        </div>
        """
    )
    st.markdown(html, unsafe_allow_html=True)


def alert_row(
    seq_id: str,
    score: float,
    n_events: int,
    label: str,
    is_anomaly: bool,
) -> None:
    """Render a compact alert row."""

    status_class = "anomaly-text" if is_anomaly else "normal-text"

    html = textwrap.dedent(
        f"""
        <div class="alert-row">
            <div class="alert-id">{seq_id}</div>
            <div class="alert-meta">
                Score: <b>{score:.4f}</b>
                &nbsp; · &nbsp;
                Events: <b>{n_events}</b>
                &nbsp; · &nbsp;
                Ground truth:
                <span class="{status_class}">{label}</span>
            </div>
        </div>
        """
    )
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        textwrap.dedent(
            """
            <div class="sidebar-brand">
                <div class="sidebar-title">Log Anomaly Monitor</div>
                <div class="sidebar-subtitle">Session & window-based detection</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    st.markdown("#### Navigation")

    page = st.radio(
        "Dashboard section",
        [
            "Overview",
            "Alert Triage",
            "Live Analysis",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown(
        textwrap.dedent(
            """
            <div class="muted">
                <b>Datasets</b><br>
                HDFS · BGL
                <br><br>
                <b>Parsing</b><br>
                Drain
                <br><br>
                <b>Detection</b><br>
                Isolation Forest · PCA
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


# ============================================================
# PAGE HEADER
# ============================================================

st.markdown(
    textwrap.dedent(
        """
        <div class="eyebrow">
            Machine Learning Monitoring
        </div>
        """
    ),
    unsafe_allow_html=True,
)

st.title("Log Anomaly Monitor")

st.markdown(
    """
    Investigate anomalous log sessions and time windows using
    event-template count vectors.
    """
)


# ============================================================
# OVERVIEW
# ============================================================

if page == "Overview":
    st.divider()

    st.subheader("Detection overview")

    # --------------------------------------------------------
    # GET HDFS PCA METRICS
    # --------------------------------------------------------

    kpi_auc = None
    kpi_recall = None
    kpi_fpr = None
    kpi_precision = None

    if metrics is not None:
        hdfs_pca = metrics[
            (metrics["dataset"] == "hdfs")
            & (metrics["model"] == "pca")
            & (metrics["slice"] == "recall≈0.80")
        ]

        if not hdfs_pca.empty:
            row = hdfs_pca.iloc[0]

            kpi_auc = float(row["roc_auc"])
            kpi_recall = float(row["recall"])
            kpi_fpr = float(row["fpr"])
            kpi_precision = float(row["precision"])

    # --------------------------------------------------------
    # KPI ROW
    # --------------------------------------------------------

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        metric_card(
            "HDFS ROC-AUC",
            (f"{kpi_auc:.4f}" if kpi_auc is not None else "—"),
            "PCA · block sessions",
        )

    with k2:
        metric_card(
            "Recall",
            (f"{kpi_recall:.1%}" if kpi_recall is not None else "—"),
            "Operating point ≈ 80%",
        )

    with k3:
        metric_card(
            "False Positive Rate",
            (f"{kpi_fpr:.2%}" if kpi_fpr is not None else "—"),
            "HDFS · PCA",
        )

    with k4:
        metric_card(
            "Precision",
            (f"{kpi_precision:.1%}" if kpi_precision is not None else "—"),
            "HDFS · PCA",
        )

    # --------------------------------------------------------
    # MODEL PERFORMANCE
    # --------------------------------------------------------

    st.divider()

    st.subheader("Model performance")

    st.caption(
        "Performance across datasets, grouping strategies and models "
        "at the operating point targeting approximately 80% recall."
    )

    if metrics is not None:
        show = metrics[metrics["slice"] == "recall≈0.80"][
            [
                "dataset",
                "grouping",
                "model",
                "precision",
                "recall",
                "fpr",
                "roc_auc",
                "alerts_per_million_lines",
            ]
        ].copy()

        # Format display values.

        show["precision"] = show["precision"].map(lambda x: f"{x:.1%}")
        show["recall"] = show["recall"].map(lambda x: f"{x:.1%}")
        show["fpr"] = show["fpr"].map(lambda x: f"{x:.2%}")
        show["roc_auc"] = show["roc_auc"].map(lambda x: f"{x:.4f}")
        show["alerts_per_million_lines"] = show[
            "alerts_per_million_lines"
        ].map(lambda x: f"{x:,.0f}")

        show.columns = [
            "Dataset",
            "Grouping",
            "Model",
            "Precision",
            "Recall",
            "FPR",
            "ROC-AUC",
            "Alerts / 1M",
        ]

        st.dataframe(
            show,
            hide_index=True,
            use_container_width=True,
        )

    else:
        st.warning(
            "metrics.csv was not found. Run the experiment pipeline first."
        )

    # --------------------------------------------------------
    # WINDOW SIZE ANALYSIS
    # --------------------------------------------------------

    st.divider()

    st.subheader("Window-size analysis")

    st.caption("Comparison of detection behaviour across BGL time windows.")

    fig = FIGURES_DIR / "window_size_tradeoff.png"

    if fig.exists():
        st.image(
            str(fig),
            caption="BGL window-size trade-off",
            use_container_width=True,
        )

    else:
        st.info("The window-size figure is not available.")

    # --------------------------------------------------------
    # RESULTS INTERPRETATION
    # --------------------------------------------------------

    st.divider()

    st.subheader("Results interpretation")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### HDFS")

        st.caption("Block-level session detection")

        st.write(
            """
            PCA reconstruction error provides strong separation
            between normal and anomalous HDFS sessions in the
            reported experiment.
            """
        )

    with col2:
        st.markdown("#### BGL")

        st.caption("Time-window detection")

        st.write(
            """
            BGL is more challenging for this feature representation.
            Results vary with the selected time-window size, showing
            the trade-off between detection sensitivity and alert
            volume.
            """
        )

    # --------------------------------------------------------
    # DETECTION PIPELINE
    # --------------------------------------------------------

    st.divider()

    st.subheader("Detection pipeline")

    st.caption(
        "Raw logs → Drain parsing → Event templates → "
        "Sessions / time windows → Count vectors → "
        "Isolation Forest / PCA → Anomaly score → Alert triage"
    )


# ============================================================
# ALERT TRIAGE
# ============================================================

elif page == "Alert Triage":
    st.divider()

    st.subheader("Alert triage")

    st.caption(
        "Review the highest-scoring BGL windows and inspect the "
        "underlying log lines."
    )

    if flagged_payload is None:
        st.warning(
            "No flagged-window artifact was found. "
            "Run the project pipeline to generate "
            "`artifacts/bgl_flagged.json`."
        )

    else:
        # ----------------------------------------------------
        # FILTER CONTROLS
        # ----------------------------------------------------

        filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1])

        available_windows = list(flagged_payload.keys())

        with filter_col1:
            selected_window = st.selectbox(
                "Window size",
                options=available_windows,
            )

        rows = flagged_payload.get(
            selected_window,
            [],
        )

        with filter_col2:
            status_filter = st.selectbox(
                "Ground truth",
                [
                    "All",
                    "Anomaly",
                    "Normal",
                ],
            )

        with filter_col3:
            maximum = max(
                5,
                min(25, len(rows)),
            )

            default_value = min(
                10,
                maximum,
            )

            max_alerts = st.slider(
                "Displayed windows",
                min_value=5,
                max_value=maximum,
                value=default_value,
            )

        # ----------------------------------------------------
        # FILTER DATA
        # ----------------------------------------------------

        filtered_rows = []

        for item in rows:
            is_anomaly = bool(
                item.get(
                    "y_true",
                    0,
                )
            )

            if status_filter == "Anomaly" and not is_anomaly:
                continue

            if status_filter == "Normal" and is_anomaly:
                continue

            filtered_rows.append(item)

        filtered_rows = filtered_rows[:max_alerts]

        # ----------------------------------------------------
        # TRIAGE SUMMARY
        # ----------------------------------------------------

        total = len(rows)

        anomaly_count = sum(
            bool(
                item.get(
                    "y_true",
                    0,
                )
            )
            for item in rows
        )

        normal_count = total - anomaly_count

        st.markdown("")

        s1, s2, s3 = st.columns(3)

        with s1:
            metric_card(
                "Flagged windows",
                f"{total}",
                "Highest-scoring windows",
            )

        with s2:
            metric_card(
                "Anomalous windows",
                f"{anomaly_count}",
                "Ground-truth anomaly label",
            )

        with s3:
            metric_card(
                "Normal windows",
                f"{normal_count}",
                "Potential false positives",
            )

        st.divider()

        st.caption(f"Showing {len(filtered_rows)} of {total} windows.")

        # ----------------------------------------------------
        # ALERT LIST
        # ----------------------------------------------------

        if not filtered_rows:
            st.info("No windows match the selected filter.")

        for item in filtered_rows:
            seq_id = str(
                item.get(
                    "seq_id",
                    "unknown",
                )
            )

            score = float(
                item.get(
                    "score",
                    0,
                )
            )

            n_events = int(
                item.get(
                    "n_events",
                    0,
                )
            )

            y_true = bool(
                item.get(
                    "y_true",
                    0,
                )
            )

            label = "Anomaly" if y_true else "Normal"

            alert_row(
                seq_id=seq_id,
                score=score,
                n_events=n_events,
                label=label,
                is_anomaly=y_true,
            )

            with st.expander(f"Inspect {seq_id}"):
                left, right = st.columns([1, 2])

                with left:
                    st.markdown("#### Alert details")

                    st.write(f"**Window:** {seq_id}")

                    st.write(f"**Anomaly score:** {score:.4f}")

                    st.write(f"**Events:** {n_events}")

                    st.write(f"**Ground truth:** {label}")

                    if y_true:
                        st.success("This window contains an anomaly label.")

                    else:
                        st.info(
                            "This window is labelled normal "
                            "and may represent a false positive."
                        )

                with right:
                    st.markdown("#### Raw log lines")

                    lines = item.get(
                        "lines",
                        [],
                    )

                    if lines:
                        for line in lines:
                            st.code(
                                line,
                                language="text",
                            )

                    else:
                        st.info("No raw lines are stored for this window.")


# ============================================================
# LIVE ANALYSIS
# ============================================================

elif page == "Live Analysis":
    st.divider()

    st.subheader("Live log analysis")

    st.caption(
        "Upload a BGL-style log file and inspect the resulting "
        "Drain templates and 60-second windows."
    )

    st.markdown(
        """
        **Processing pipeline**

        `Log lines` → `Drain templates` → `60-second windows`
        → `event counts` → `alert labels`
        """
    )

    uploaded = st.file_uploader(
        "Choose a BGL-style log file",
        type=[
            "log",
            "txt",
        ],
        help="Upload a BGL-style log file.",
    )

    if uploaded is not None:
        ARTIFACTS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = ARTIFACTS_DIR / "upload.log"

        path.write_bytes(uploaded.getvalue())

        with st.spinner(
            "Parsing log file and building " "60-second windows..."
        ):
            events, parser = parse_bgl_log(
                path,
                parser=DrainParser(),
                show_progress=False,
            )

            sequences = build_bgl_windows(
                events,
                window_sec=60,
            )

        st.success("Log processing completed.")

        # ----------------------------------------------------
        # UPLOAD METRICS
        # ----------------------------------------------------

        n_lines = len(events)

        n_templates = len(parser.templates())

        n_windows = len(sequences)

        n_alerts = int(sequences["y"].sum())

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            metric_card(
                "Log lines",
                f"{n_lines:,}",
                "Parsed events",
            )

        with c2:
            metric_card(
                "Templates",
                f"{n_templates:,}",
                "Drain event templates",
            )

        with c3:
            metric_card(
                "Windows",
                f"{n_windows:,}",
                "60-second windows",
            )

        with c4:
            metric_card(
                "Alert-labelled",
                f"{n_alerts:,}",
                "Windows containing alerts",
            )

        # ----------------------------------------------------
        # WINDOW PREVIEW
        # ----------------------------------------------------

        st.divider()

        st.subheader("Window preview")

        preview_columns = [
            "seq_id",
            "n_events",
            "n_alerts",
            "y",
            "t_start",
            "t_end",
        ]

        available_columns = [
            column for column in preview_columns if column in sequences.columns
        ]

        st.dataframe(
            sequences[available_columns].head(100),
            hide_index=True,
            use_container_width=True,
        )

        # ----------------------------------------------------
        # PARSED TEMPLATES
        # ----------------------------------------------------

        st.divider()

        st.subheader("Parsed event templates")

        templates = parser.templates()

        if templates:
            template_rows = []

            for template_id, template in templates.items():
                template_rows.append(
                    {
                        "Template ID": template_id,
                        "Template": str(template),
                    }
                )

            template_df = pd.DataFrame(template_rows)

            st.dataframe(
                template_df.head(100),
                hide_index=True,
                use_container_width=True,
            )

        else:
            st.info("No Drain templates were produced.")


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Log Anomaly Monitor · Drain parsing · "
    "Session/window-based anomaly detection"
)