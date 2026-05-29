# NGSIM Project

This repository contains the code and documentation for extracting simulator-ready lane-change scenarios from the official NGSIM US-101 vehicle trajectory dataset.

## Quick Navigation

- **Project Status and Decisions**: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- **Workflow and Run Instructions**: [ngsim_ego_extraction/README.md](ngsim_ego_extraction/README.md)
- **Main Configuration**: [ngsim_ego_extraction/config/us101_config.yaml](ngsim_ego_extraction/config/us101_config.yaml)
- **Example Plots**: [docs/assets/scenario_023_vehicle_2001164](docs/assets/scenario_023_vehicle_2001164)

## Generated Outputs

The full generated scenario outputs are not stored in GitHub because they are large generated datasets.

The final outputs are hosted in the following shared OneDrive folder:
[NGSIM Project Shared Outputs](https://texastechuniversity-my.sharepoint.com/:f:/g/personal/safkamal_ttu_edu/IgAMLRBHgXRQQqx9GqOyJK8vAWOFK251gDu3bDasSXuRrGU?e=lepLrl)

The shared folder contains:
```text
outputs/
PROJECT_STATUS.md
README.md
us101_config.yaml
US_101_metadata_with_disclaimer.pdf
```

The primary deliverables are under:
```text
outputs/scenarios/
```

Each scenario directory includes:
- `metadata.yaml`: Scenario metadata and filtering assumptions.
- `ego_trajectory.csv`: Ego vehicle trajectory over the selected road segment.
- `surrounding_vehicles.csv`: Surrounding vehicles formatted for simulation import.
- `surrounding_vehicles_full.csv`: Unfiltered surrounding vehicle context.
- `lane_changes.csv`: Target lane-change event index.
- `ego_maneuver_window.csv`: Ego trajectory cropped around the target lane change.
- `surrounding_maneuver_window.csv`: Surrounding vehicles during the target maneuver.
- `plots/`: Diagnostic and verification plots.

## Interactive Playback Simulation

An interactive simulation tool written in Pygame is provided to play back and visually QA any of the 30 scenario corridors in real-time.

To launch the playback visualizer, execute:
```bash
python scripts/06_run_pygame_simulation.py
```

### Key Features
- **HUD Dashboard**: Displays elapsed time, frame ID, speed (m/s and mph), active acceleration, and lane tracking.
- **Highway Layout**: Renders standard lane markings, vehicle geometries, and historical trajectory trails.
- **Camera View Modes**: Press `V` to toggle between **Full Segment view** (displays the entire 500m segment) and **Ego-Centered Tracking view** (scroll-tracks the Ego vehicle).

## Current Scenario Design

- **Dataset**: Official NGSIM US-101.
- **Time Coverage**: All three official 15-minute intervals.
- **Scenario Type**: Lane-change event corridors.
- **Current Exported Count**: 30 scenarios.
- **Road Segment Length**: Approximately 500 meters.
- **Maneuver Window**: 5 seconds before to 5 seconds after the target lane-change frame.
- **Local Leader-Free Constraint**:
  ```text
  Preceding == 0 OR Space_Headway_m > 50 m (checked across at least 80% of maneuver window frames)
  ```
