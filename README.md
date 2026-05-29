# NGSIM Project

This repository contains the code and documentation for extracting simulator-ready lane-change scenarios from the official NGSIM US-101 vehicle trajectory dataset.

## Quick Navigation

- Project decisions and progress:
  - [PROJECT_STATUS.md](PROJECT_STATUS.md)

- Python workflow and run instructions:
  - [ngsim_ego_extraction/README.md](ngsim_ego_extraction/README.md)

- Main configuration:
  - [ngsim_ego_extraction/config/us101_config.yaml](ngsim_ego_extraction/config/us101_config.yaml)

- Example plots used in the status report:
  - [docs/assets/scenario_023_vehicle_2001164](docs/assets/scenario_023_vehicle_2001164)

## Generated Outputs

The full generated scenario outputs are not stored in GitHub because they are generated artifacts and include many CSV/PNG files.

Use the shared OneDrive folder for final outputs:

[NGSIM Project Shared Outputs](https://texastechuniversity-my.sharepoint.com/:f:/g/personal/safkamal_ttu_edu/IgAMLRBHgXRQQqx9GqOyJK8vAWOFK251gDu3bDasSXuRrGU?e=lepLrl)

The shared folder should contain:

```text
outputs/
PROJECT_STATUS.md
README.md
us101_config.yaml
US_101_metadata_with_disclaimer.pdf
```

The most important generated folder is:

```text
outputs/scenarios/
```

Each scenario folder includes:

- `metadata.yaml`: scenario metadata and filtering assumptions.
- `ego_trajectory.csv`: ego trajectory over the selected road window.
- `surrounding_vehicles.csv`: compact simulator-ready surrounding vehicles.
- `surrounding_vehicles_full.csv`: broader local traffic context.
- `lane_changes.csv`: lane-change event index.
- `ego_maneuver_window.csv`: ego data around the target lane change.
- `surrounding_maneuver_window.csv`: compact surrounding traffic during the maneuver.
- `plots/`: visual QA plots.

## 🎬 NEW: Interactive Playback Simulation

You can now play back and visually QA any of the 30 scenario corridors in real-time using a premium, high-fidelity vector simulator written in **Pygame**!

To start the interactive playback visualizer:
```bash
python scripts/06_run_pygame_simulation.py
```

* **Interactive HUD Dashboard**: Displays elapsed time, frame ID, speed (m/s & mph), active acceleration, and lane tracking.
* **Vector Highway & Trajectory Tails**: Draws standard lane markings with glowing vehicle vectors and neon historical trajectory trails.
* **Dual Camera Views**: Press `V` to toggle between a **Full Segment view** (fits the entire 500m segment) and an **Ego-Centered Tracking view** (scroll-tracks with Ego).

## Current Scenario Design

- Dataset: official NGSIM US-101.
- Time coverage: all three official 15-minute US-101 segments.
- Scenario type: target lane-change event scenarios.
- Current exported count: `30` scenarios.
- Road window: approximately `500 m`.
- Maneuver window: `5 seconds before` to `5 seconds after` the target lane-change frame.
- Local leader-free rule during the target maneuver:

```text
Preceding == 0 OR Space_Headway_m > 75 m
```

