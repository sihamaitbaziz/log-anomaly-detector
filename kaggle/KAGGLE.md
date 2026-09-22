# Kaggle: full HDFS + BGL run

Internet must be **on**. GPU is unused. Expected wall time: ~30–90 minutes for Drain parse of both dumps plus Isolation Forest / PCA, depending on CPU.

## 1. Notebook

New notebook → Python 3 → Accelerator: **None**.

Upload this repository as a Kaggle dataset  **or** clone:

```python
!git clone https://github.com/YOUR_USER/log-anomaly-detector.git /kaggle/working/repo
%cd /kaggle/working/repo
```

If you uploaded a dataset:

```python
import os, shutil
src = "/kaggle/input/log-anomaly-detector"  # your dataset slug
dst = "/kaggle/working/repo"
if not os.path.exists(dst):
    shutil.copytree(src, dst)
os.chdir(dst)
```

## 2. Install

```python
!pip install -r requirements.txt
```

## 3. Download LogHub (Zenodo 3227177)

```python
!python main.py download --datasets hdfs bgl
```

Equivalent raw wget if the helper is blocked:

```python
!mkdir -p /kaggle/working/repo/data/raw
!wget -O /kaggle/working/repo/data/raw/HDFS_1.tar.gz https://zenodo.org/records/3227177/files/HDFS_1.tar.gz
!wget -O /kaggle/working/repo/data/raw/BGL.tar.gz https://zenodo.org/records/3227177/files/BGL.tar.gz
!mkdir -p data/raw/hdfs data/raw/bgl
!tar -xzf data/raw/HDFS_1.tar.gz -C data/raw/hdfs
!tar -xzf data/raw/BGL.tar.gz -C data/raw/bgl
```

Confirm:

```python
!find data/raw -iname 'HDFS.log' -o -iname 'anomaly_label.csv' -o -iname 'BGL.log'
```

## 4. Smoke test (optional, ~5 min)

```python
!python main.py run --max-lines 150000 --windows 60 --trees 80
```

## 5. Full run (the resume numbers)

```python
!python main.py run --windows 30 60 300 --trees 200 --jobs -1
```

Outputs:

- `reports/metrics.csv` — FPR, recall, precision@budget, alerts per million lines
- `reports/window_tradeoff.csv` — 30 vs 60 vs 300 s
- `reports/figures/window_size_tradeoff.png` — README hero chart
- `artifacts/bgl_flagged.json` — dashboard


