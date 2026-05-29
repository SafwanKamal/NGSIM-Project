# NGSIM Ego Vehicle Extraction

Python workflow for extracting simulator-ready ego-vehicle scenarios from the NGSIM US-101 trajectory dataset.

## Shared Outputs

The full generated outputs are shared outside GitHub:

[NGSIM Project Shared Outputs](https://texastechuniversity-my.sharepoint.com/:f:/g/personal/safkamal_ttu_edu/IgAMLRBHgXRQQqx9GqOyJK8vAWOFK251gDu3bDasSXuRrGU?e=lepLrl)

Use that folder for the final `outputs/` directory, including all exported scenario CSVs, metadata, and plots.

## Quick Start

1. Download the Kaggle dataset:

```bash
python scripts/00_download_dataset.py
```

This uses:

```python
kagglehub.dataset_download("nigelwilliams/ngsim-vehicle-trajectory-data-us-101")
```

The downloaded CSV/TXT/DAT files are copied into `data/raw/`.

For the full official US-101 trajectory package with all three 15-minute periods, use:

```bash
python scripts/00_download_official_us101.py
```

Alternatively, manually put the raw US-101 trajectory file at:

```text
data/raw/us101_trajectories.csv
```

By default, the loader reads all trajectory-like files in `data/raw/`, not just one time segment. The current Kaggle package downloaded here contains one trajectory file, `trajectories-0750am-0805am.txt`; adding the other US-101 segment files to `data/raw/` will include them automatically.

The default config uses lanes `[2, 3, 4, 5, 6, 7]` as middle/freeway lanes for the downloaded 8-lane file and prefers lane-change-event candidates. For lane-change candidates, `Preceding == 0 OR Space_Headway_m > local_leader_free_distance_m` is checked only inside the configured maneuver window around the lane change.

2. Install the package in editable mode:

```bash
pip install -e .
```

3. Inspect the raw dataset:

```bash
python scripts/01_inspect_dataset.py
```

4. Extract candidate ego vehicles:

```bash
python scripts/02_extract_candidates.py
```

5. Export simulator-ready scenarios:

```bash
python scripts/03_export_scenarios.py
```

6. Regenerate plots for exported scenarios:

```bash
python scripts/04_plot_scenarios.py
```

7. Generate a scenario summary report:

```bash
python scripts/05_summarize_scenarios.py
```

Generated files are written under `outputs/`.

Each scenario exports both surrounding-vehicle context files:

- `surrounding_vehicles_full.csv`: all vehicles in the broad local context window.
- `surrounding_vehicles.csv`: compact simulator-ready context, using the closest ahead and behind vehicles per nearby lane, with minimum-frame filtering.

Lane-change scenarios also include maneuver-window context:

- `lane_changes.csv`: compact lane-change event index.
- `ego_maneuver_window.csv`: ego trajectory from 5 seconds before to 5 seconds after the target lane-change frame.
- `surrounding_maneuver_window.csv`: compact surrounding vehicles over the same maneuver window.
