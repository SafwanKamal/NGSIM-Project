# Raw Data

Place the raw NGSIM US-101 trajectory CSV or TXT file here, or run:

```bash
python scripts/00_download_dataset.py
```

The download script uses KaggleHub:

```python
kagglehub.dataset_download("nigelwilliams/ngsim-vehicle-trajectory-data-us-101")
```

The default config expects:

```text
data/raw/us101_trajectories.csv
```

Raw data should not be edited in place. Generated files belong under `outputs/` or `data/processed/`.
