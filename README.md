# Log Anomaly Detector

### Session-Based & Window-Based Log Anomaly Detection on HDFS and BGL

An end-to-end machine learning project for detecting anomalous system log behavior using **Drain log parsing**, **event-template representations**, **Isolation Forest**, and **PCA reconstruction error**.

The project focuses on an important question in log monitoring:

> **How does the way we group log events into sessions or time windows affect anomaly detection performance?**

Instead of treating every log line independently, the system transforms raw logs into structured sessions or time windows and evaluates their anomaly scores using operational metrics such as **ROC-AUC, precision, recall, false-positive rate, and alert volume**.

---

## 📌 Overview

Modern systems can generate millions of log lines, making manual inspection impractical.

This project implements a complete anomaly detection pipeline:

```text
Raw Logs
    ↓
Drain Log Parsing
    ↓
Event Templates
    ↓
HDFS Sessions / BGL Time Windows
    ↓
Event-Template Count Vectors
    ↓
Isolation Forest + PCA
    ↓
Anomaly Scores
    ↓
Operational Evaluation
    ↓
Streamlit Monitoring Dashboard


🎯 Objectives

The project has four main objectives:

Parse large-scale system logs into reusable event templates.
Transform raw log lines into meaningful sessions or time windows.
Compare classical unsupervised anomaly detection approaches.
Study how the definition of a sequence/window affects detection quality and alert volume.

A key idea of the project is that the unit being classified matters.

For HDFS, the natural unit is a block session.

For BGL, the project evaluates several time-window definitions:

30 seconds
60 seconds
300 seconds
📊 Datasets

The experiments use the LogHub HDFS and BGL datasets.

HDFS

The HDFS dataset contains approximately:

11,175,629 log lines

HDFS logs are grouped by Block ID, producing block-level sessions.

The dataset provides Normal/Anomaly labels at the block level.

BGL

The BGL dataset contains approximately:

4,747,963 log lines

BGL logs are grouped into fixed time windows:

30 seconds
60 seconds
300 seconds

The BGL alert indicator is derived from the dataset's alert field.

Dataset Sources
LogHub: https://github.com/logpai/loghub
Zenodo: https://zenodo.org/records/3227177

The raw datasets are not included in this repository because of their size.

They are downloaded locally when running the real experiments.

🧠 Methodology
1. Drain Log Parsing

Raw system logs contain both stable event information and variable values such as:

IDs
numbers
IP addresses
timestamps
dynamic parameters

A Drain-style parser identifies recurring patterns and converts raw messages into event templates.

For example:

Original log:

Block blk_12345 moved from node 192.168.1.20

can be represented as:

Block <*> moved from node <*>

This reduces the raw log vocabulary into a structured set of event types.

2. Session and Window Construction
HDFS

HDFS logs are grouped by Block ID:

Log Lines
    ↓
Block ID
    ↓
HDFS Session

Each block session becomes one observation for anomaly detection.

BGL

BGL logs do not use the same block-based session structure.

Instead, logs are grouped according to their timestamps:

BGL Logs
    ↓
Timestamp
    ↓
30s / 60s / 300s Windows

The different window sizes are evaluated to understand how temporal grouping affects anomaly detection.

3. Feature Engineering

Each session/window is represented using an event-template count vector.

For example:

Template A → 12 occurrences
Template B →  4 occurrences
Template C →  0 occurrences
Template D →  8 occurrences
...

The vector represents the behavioral profile of the session/window.

This representation is intentionally simple and interpretable.

🤖 Anomaly Detection Models

The project evaluates two unsupervised anomaly detection approaches.

Isolation Forest

Isolation Forest identifies observations that are easier to isolate from the rest of the dataset.

It is used as an unsupervised baseline for identifying unusual combinations of event-template frequencies.

The model does not require anomaly labels as direct training targets.

PCA Reconstruction Error

PCA learns a lower-dimensional representation of the event-template vectors.

The reconstruction error is used as an anomaly score.

Original Vector
      ↓
     PCA
      ↓
Compressed Representation
      ↓
Reconstruction
      ↓
Reconstruction Error
      ↓
Anomaly Score

A higher reconstruction error indicates a stronger deviation from the learned structure.

📈 Evaluation Strategy

The project intentionally does not use accuracy as the main headline metric.

Log anomaly datasets can be highly imbalanced, so accuracy can hide important operational behaviour.

Instead, the project evaluates:

ROC-AUC
Precision
Recall
False Positive Rate (FPR)
Alerts per million lines
Performance under alert budgets
Performance at approximately 80% recall

The approximately 80% recall operating point is used to expose the trade-off between detecting anomalies and generating false alerts.

🏆 Results

The results below come from the full real LogHub experiment using the complete HDFS and BGL datasets.

HDFS Results

At an operating point targeting approximately 80% recall:

Model	ROC-AUC	Precision	Recall	FPR	Alerts / 1M lines
Isolation Forest	0.9607	44.54%	80.91%	3.04%	2,736.61
PCA	0.9895	93.72%	80.10%	0.16%	1,287.62

The HDFS experiment shows strong separation using PCA reconstruction error with block-level sessions.

BGL Results

BGL is more challenging for the current event-template count representation.

PCA — Window Size Comparison
Window Size	ROC-AUC	Precision	Recall	FPR
30 seconds	0.8276	15.97%	79.72%	23.34%
60 seconds	0.8371	15.58%	80.00%	22.24%
300 seconds	0.8433	16.54%	80.16%	24.35%
Isolation Forest — Window Size Comparison
Window Size	ROC-AUC
30 seconds	0.5235
60 seconds	0.6171
300 seconds	0.7646

The BGL results show that the current count-vector representation has difficulty controlling false positives when operating around 80% recall.

This limitation is explicitly reported rather than hidden behind a single accuracy value.

🔎 Key Findings
HDFS

The HDFS experiment benefits from a natural session definition based on Block ID.

At the selected operating point, PCA achieves:

ROC-AUC : 0.9895
Precision: 93.72%
Recall  : 80.10%
FPR     : 0.16%

This demonstrates that the combination of block-level sessions and PCA reconstruction error can provide strong anomaly separation on HDFS.

BGL

BGL is more difficult because the logs are grouped into fixed time windows rather than naturally defined sessions.

Changing the window size affects:

anomaly score distributions
alert volume
false-positive behaviour
ROC-AUC

Therefore, sequence/window construction is an important part of the anomaly detection problem.

🖥️ Streamlit Dashboard

The project includes an interactive Streamlit monitoring interface called:

Log Anomaly Monitor

The dashboard is designed around three main workflows.

1. Overview

The Overview page provides:

HDFS performance metrics
model comparison
BGL window-size analysis
interpretation of HDFS and BGL results
detection pipeline
2. Alert Triage

The Alert Triage page allows the user to:

select a BGL window size
filter anomaly/normal windows
inspect high-scoring windows
view anomaly scores
inspect the raw log lines associated with a window

The goal is to move from:

Anomaly Score

to:

Anomaly Score
      ↓
Flagged Window
      ↓
Raw Log Lines
      ↓
Human Inspection
3. Live Analysis

The Live Analysis page allows a user to upload a BGL-style .log or .txt file.

The application then:

Uploaded Log
     ↓
Drain Parsing
     ↓
Event Templates
     ↓
60-Second Windows
     ↓
Window Statistics

The interface displays:

number of parsed events
number of discovered templates
number of generated windows
alert statistics
window-level information
parsed templates

Run the dashboard with:

python main.py dashboard

📸 Dashboard Screenshots
Overview



📁 Project Structure
log-anomaly-detector/
│
├── main.py
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
│
├── logad/
│   ├── config.py
│   ├── download.py
│   ├── pipeline.py
│   ├── synthetic.py
│   │
│   ├── parsing/
│   │   ├── drain.py
│   │   ├── hdfs.py
│   │   └── bgl.py
│   │
│   ├── sequences/
│   │   ├── hdfs_sessions.py
│   │   └── bgl_windows.py
│   │
│   ├── features/
│   │   └── count_vector.py
│   │
│   ├── models/
│   │   └── detectors.py
│   │
│   ├── evaluation/
│   │   ├── metrics.py
│   │   └── window_study.py
│   │
│   └── viz/
│       └── plots.py
│
├── dashboard/
│   └── app.py
│
├── tests/
│   ├── test_bgl_windows.py
│   ├── test_hdfs.py
│   └── test_metrics.py
│
├── reports/
│   ├── metrics.csv
│   ├── figures/
│   │   ├── window_size_tradeoff.png
│   │   ├── alert_volume.png
│   │   └── fpr_at_80_recall.png
│   │
│   └── screenshots/
│       ├── overview.png
│       ├── alert-triage.png
│       └── live-analysis.png
│
├── kaggle/
│   ├── KAGGLE.md
│   └── kaggle_notebook.ipynb
│
└── data/
    └── README.md

Large datasets, generated artifacts, caches, and virtual environments are intentionally excluded from version control.

⚙️ Installation
Windows

Create a virtual environment:

python -m venv .venv

Activate it:

.venv\Scripts\activate

Install the dependencies:

pip install -r requirements.txt
macOS / Linux
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
🧪 Run Tests

Run the test suite with:

python -m pytest -q
🚀 Quick Demo

A lightweight synthetic demo is available to verify that the pipeline works without downloading the complete datasets:

python main.py demo

The demo is intended for testing the pipeline only.

Synthetic demo metrics should not be presented as the real benchmark results.

📥 Download the Real Datasets

Download the HDFS and BGL datasets with:

python main.py download --datasets hdfs bgl

The raw datasets are stored locally and excluded from Git using .gitignore.

▶️ Run the Real Experiment

Run the complete BGL window-size experiment:

python main.py run --windows 30 60 300

For a smaller smoke test:

python main.py run --max-lines 200000 --windows 60

The generated evaluation results are written to:

reports/metrics.csv

Generated figures are written to:

reports/figures/
☁️ Kaggle

The full experiment was executed on Kaggle because the complete HDFS and BGL datasets contain millions of log lines.

Recommended workflow:

Kaggle Notebook
      ↓
Install requirements
      ↓
Download LogHub datasets
      ↓
Run full experiment
      ↓
Save metrics and figures

The repository contains the Kaggle workflow under:

kaggle/

Kaggle is recommended for the full experiment when local hardware, RAM, storage, or execution time is limited.

🔬 Reproducibility

The main configuration is centralized in:

logad/config.py

Important settings include:

Random seed       : 42
PCA variance      : 0.90
Isolation Forest  : 200 estimators
BGL windows       : 30 / 60 / 300 seconds

This makes the experiments easier to reproduce and modify.

📊 Generated Reports

The project stores the main evaluation results in:

reports/metrics.csv

Visualizations are stored in:

reports/figures/

The main visualizations include:

Window Size Trade-off
reports/figures/window_size_tradeoff.png
Alert Volume
reports/figures/alert_volume.png
False Positive Rate
reports/figures/fpr_at_80_recall.png

These files summarize the completed real-data experiment.

⚠️ Limitations
1. Event order is not explicitly modeled

The current feature representation uses event-template counts.

Therefore, sequences such as:

A → B → C

and:

C → B → A

can produce similar count representations.

The current system therefore does not explicitly model event ordering.

2. BGL false positives

The BGL results show a relatively high false-positive rate at the approximately 80% recall operating point.

This indicates that the current count-vector representation is not sufficient for highly precise BGL anomaly detection.

3. Classical unsupervised models

The current implementation focuses on:

Isolation Forest
PCA reconstruction error

More advanced sequence models could potentially capture temporal dependencies that these approaches miss.

🔮 Future Work

Possible improvements include:

Sequence-Aware Detection

Implement:

DeepLog-style next-event prediction
sequence embeddings
lightweight Transformer models
Temporal Features

Add:

inter-arrival times
burst statistics
event frequency changes
temporal entropy
Streaming Processing

Implement streaming Drain/Drain3 processing for continuously arriving logs.

Explainability

Add explanations showing which event templates contributed most to an anomaly score.

Additional Datasets

Evaluate the pipeline on additional system-log datasets to study generalization.

🧰 Technologies
Python
Pandas
NumPy
Scikit-learn
Matplotlib
Streamlit
Pytest
Drain-style log parsing
PCA
Isolation Forest
Kaggle



The large raw datasets are downloaded when needed.



👩‍💻 Author

Siham Aitbaziz

AI & Data Science


📄 License

This project code is released under the MIT License.

The HDFS and BGL datasets are not included in this repository and remain subject to their respective source and distribution terms.