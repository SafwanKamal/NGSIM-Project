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

8. Play back the scenarios in the interactive Pygame simulation visualizer:

```bash
python scripts/06_run_pygame_simulation.py
```

Generated files are written under `outputs/`.

Each scenario exports both surrounding-vehicle context files:

- `surrounding_vehicles_full.csv`: all vehicles in the broad local context window.
- `surrounding_vehicles.csv`: compact simulator-ready context, using the closest ahead and behind vehicles per nearby lane, with minimum-frame filtering.

Lane-change scenarios also include maneuver-window context:

- `lane_changes.csv`: compact lane-change event index.
- `ego_maneuver_window.csv`: ego trajectory from 5 seconds before to 5 seconds after the target lane-change frame.
- `surrounding_maneuver_window.csv`: compact surrounding vehicles over the same maneuver window.

---

## Trajectory Simulation Playback (Pygame)

An interactive, high-fidelity vector simulator is implemented in Python using **Pygame** to visually play back all 30 scenario corridors in real-time.

### Running the Visualizer
From the `ngsim_ego_extraction/` project root directory, execute:
```bash
python scripts/06_run_pygame_simulation.py
```

### Necessary Folder Structure & Files

The visualizer auto-discovers and maps scenarios using the following layout and components:

```text
ngsim_ego_extraction/
  ├── scripts/
  │     └── 06_run_pygame_simulation.py  # Simulation launcher runner
  │
  ├── src/
  │     └── ngsim_visualizer/            # Visualizer package directory
  │             ├── __init__.py          # Package initialization
  │             └── visualizer.py        # Core Pygame rendering engine loop
  │
  └── outputs/
        └── scenarios/
              └── scenario_XXX_vehicle_YYYY/  # Scenario directories (e.g. 001 to 030)
                    ├── metadata.yaml        # Segment, Ego ID, active bounds metadata
                    ├── ego_trajectory.csv   # Ego (X_m, Y_m) position/speed arrays
                    └── surrounding_vehicles.csv  # Compact surrounding traffic coordinates
```

* **`metadata.yaml`**: Contains `vehicle_id` (used to track/draw EGO in bright orange), `time_segment` label, and crop bounds.
* **`ego_trajectory.csv`**: Contains chronological coordinates (`Local_X_m`, `Local_Y_m`), speeds, and accelerations.
* **`surrounding_vehicles.csv`**: Compact coordinate timelines of nearby traffic. *Note: Pressing `F` dynamically loads `surrounding_vehicles_full.csv` for the broader local context pool.*

### Key Controls Layout
* **`Space`**: Pause / Resume playback.
* **`<-` / `->` (Left/Right Arrows)**: Seek backward / forward 1.0 second (10 frames).
* **`Up` / `Down` (Up/Down Arrows)**: Adjust playback speed rate (`0.25x`, `0.5x`, `1.0x`, `2.0x`, `5.0x`).
* **`[` / `]`** (or **`PageUp / PageDn`**): Switch between scenario folders (e.g. previous/next).
* **`1-9`**: Jump directly to scenarios 1 through 9.
* **`V`**: Toggle camera tracking views:
  * **Ego-Centered Tracking View**: Scroll-centers on EGO with neon vector labels (auto-scrolling).
  * **Full Road View**: Displays the entire 500m cropped segment in a single static frame.
* **`F`**: Toggle traffic density context (Compact simulator-ready vs. Full broad surroundings).
* **`T`**: Toggle Ego past trail (-50m trail) on/off.
* **`P`**: Toggle Ego future predicted path (+50m forecast) on/off.
* **`Esc` or `Q`**: Close / Exit the visualizer.

