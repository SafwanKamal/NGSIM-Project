from __future__ import annotations

from pathlib import Path
import shutil

import pandas as pd
import yaml

from .candidates import get_middle_lanes
from .load_data import resolve_project_path
from .plots import plot_ego_maneuver_window, plot_ego_scenario
from .segment import infer_time_segment
from .surrounding import compact_surrounding_vehicles, extract_surrounding_vehicles
from .tracking import create_ego_scenario


EGO_EXPORT_COLUMNS = [
    "Vehicle_ID",
    "Frame_ID",
    "scenario_time_s",
    "time_s",
    "Local_X_m",
    "Local_Y_m",
    "v_Vel_mps",
    "v_Acc_mps2",
    "Lane_ID",
    "Preceding",
    "Following",
    "Space_Headway_m",
    "Time_Headway",
]


MANEUVER_EXPORT_COLUMNS = [
    "Vehicle_ID",
    "Frame_ID",
    "scenario_time_s",
    "maneuver_time_s",
    "time_s",
    "Local_X_m",
    "Local_Y_m",
    "v_Vel_mps",
    "v_Acc_mps2",
    "Lane_ID",
    "from_lane",
    "to_lane",
    "is_lane_change_frame",
    "Preceding",
    "Following",
    "Space_Headway_m",
    "Time_Headway",
]


def _available_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column in df.columns]


def _target_lane_change_window(
    ego: pd.DataFrame,
    surrounding: pd.DataFrame,
    candidate: pd.Series,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lane_change_frame = candidate.get("lane_change_frame", None)
    if pd.isna(lane_change_frame):
        return pd.DataFrame(columns=ego.columns), pd.DataFrame(columns=surrounding.columns)

    target = ego[ego["Frame_ID"].eq(int(lane_change_frame))]
    if target.empty:
        return pd.DataFrame(columns=ego.columns), pd.DataFrame(columns=surrounding.columns)

    window_s = float(config.get("candidate_selection", {}).get("lane_change_window_seconds", 5))
    change_time = float(target["scenario_time_s"].iloc[0])
    from_lane = None
    to_lane = int(target["Lane_ID"].iloc[0])
    target_index = int(target.index[0])
    previous = ego[ego.index < target_index]
    if not previous.empty:
        from_lane = int(previous["Lane_ID"].iloc[-1])

    start_t = change_time - window_s
    end_t = change_time + window_s
    ego_window = ego[ego["scenario_time_s"].between(start_t, end_t, inclusive="both")].copy()
    ego_window["maneuver_time_s"] = ego_window["scenario_time_s"] - change_time
    ego_window["from_lane"] = from_lane
    ego_window["to_lane"] = to_lane
    ego_window["is_lane_change_frame"] = ego_window["Frame_ID"].eq(int(lane_change_frame))

    surrounding_window = surrounding[surrounding["scenario_time_s"].between(start_t, end_t, inclusive="both")].copy()
    if not surrounding_window.empty:
        surrounding_window["maneuver_time_s"] = surrounding_window["scenario_time_s"] - change_time
        surrounding_window["from_lane"] = from_lane
        surrounding_window["to_lane"] = to_lane
        surrounding_window["is_lane_change_frame"] = surrounding_window["Frame_ID"].eq(int(lane_change_frame))

    return ego_window, surrounding_window


def export_scenario(df: pd.DataFrame, candidate: pd.Series, config: dict, scenario_number: int) -> Path:
    vehicle_id = int(candidate["Vehicle_ID"])
    scenario = create_ego_scenario(
        df,
        vehicle_id,
        config,
        int(candidate["start_frame"]) if "start_frame" in candidate else None,
        int(candidate["end_frame"]) if "end_frame" in candidate else None,
    )
    ego = scenario["ego"]
    lane_changes = scenario["lane_changes"]
    surrounding_full = extract_surrounding_vehicles(df, ego, config)
    surrounding = compact_surrounding_vehicles(surrounding_full, ego, config)
    ego_maneuver, surrounding_maneuver = _target_lane_change_window(ego, surrounding, candidate, config)

    output_root = resolve_project_path(config.get("export", {}).get("output_dir", "outputs")) / "scenarios"
    scenario_dir = output_root / f"scenario_{scenario_number:03d}_vehicle_{vehicle_id}"
    plots_dir = scenario_dir / "plots"
    scenario_dir.mkdir(parents=True, exist_ok=True)

    ego[_available_columns(ego, EGO_EXPORT_COLUMNS)].to_csv(scenario_dir / "ego_trajectory.csv", index=False)
    surrounding_full[_available_columns(surrounding_full, EGO_EXPORT_COLUMNS)].to_csv(
        scenario_dir / "surrounding_vehicles_full.csv", index=False
    )
    surrounding[_available_columns(surrounding, EGO_EXPORT_COLUMNS)].to_csv(scenario_dir / "surrounding_vehicles.csv", index=False)
    ego_maneuver[_available_columns(ego_maneuver, MANEUVER_EXPORT_COLUMNS)].to_csv(
        scenario_dir / "ego_maneuver_window.csv", index=False
    )
    surrounding_maneuver[_available_columns(surrounding_maneuver, MANEUVER_EXPORT_COLUMNS)].to_csv(
        scenario_dir / "surrounding_maneuver_window.csv", index=False
    )
    lane_changes.to_csv(scenario_dir / "lane_changes.csv", index=False)

    middle_lanes = get_middle_lanes(df, config)
    metadata = {
        "dataset": config.get("dataset_name", "NGSIM US-101"),
        "vehicle_id": vehicle_id,
        "original_vehicle_id": int(candidate.get("Original_Vehicle_ID", vehicle_id)),
        "source_file": candidate.get("source_file", ""),
        "candidate_type": candidate.get("candidate_type", ""),
        "lane_change_frame": None if pd.isna(candidate.get("lane_change_frame", None)) else int(candidate.get("lane_change_frame")),
        "time_segment": infer_time_segment(ego.iloc[0], config),
        "road_length_m": round(float(scenario["road_length_m"]), 3),
        "sampling_interval_s": 0.1,
        "start_frame": int(ego["Frame_ID"].iloc[0]),
        "end_frame": int(ego["Frame_ID"].iloc[-1]),
        "duration_seconds": round(float(ego["scenario_time_s"].max()), 3),
        "start_lane": int(ego["Lane_ID"].iloc[0]),
        "middle_lanes": middle_lanes,
        "local_leader_free_distance_m": config.get("candidate_selection", {}).get("local_leader_free_distance_m", 75),
        "leader_check_mode": candidate.get("leader_check_mode", config.get("candidate_selection", {}).get("leader_check_mode", "full_window")),
        "leader_checked_frames": int(candidate.get("leader_checked_frames", 0)),
        "maneuver_window_seconds_before": config.get("candidate_selection", {}).get("lane_change_window_seconds", 5),
        "maneuver_window_seconds_after": config.get("candidate_selection", {}).get("lane_change_window_seconds", 5),
        "ego_maneuver_window_rows": int(len(ego_maneuver)),
        "surrounding_maneuver_window_rows": int(len(surrounding_maneuver)),
        "candidate_rule": "middle lane and locally leader-free during most of the analysis window",
        "num_surrounding_vehicles": int(surrounding["Vehicle_ID"].nunique()) if not surrounding.empty else 0,
        "num_surrounding_rows": int(len(surrounding)),
        "num_surrounding_vehicles_full": int(surrounding_full["Vehicle_ID"].nunique()) if not surrounding_full.empty else 0,
        "num_surrounding_rows_full": int(len(surrounding_full)),
        "surrounding_export": {
            "full_file": "surrounding_vehicles_full.csv",
            "compact_file": "surrounding_vehicles.csv",
            "compact_behind_distance_m": config.get("surrounding_vehicles", {}).get("compact_behind_distance_m"),
            "compact_ahead_distance_m": config.get("surrounding_vehicles", {}).get("compact_ahead_distance_m"),
            "compact_min_frames": config.get("surrounding_vehicles", {}).get("compact_min_frames"),
            "compact_rule": "closest ahead and closest behind per lane at each ego frame",
        },
        "notes": "Use for simulator comparison. Tracking ends when ego exits selected segment.",
    }
    with (scenario_dir / "metadata.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(metadata, handle, sort_keys=False)

    if config.get("export", {}).get("save_plots", True):
        plot_ego_scenario(ego, plots_dir)
        plot_ego_maneuver_window(ego_maneuver, plots_dir)
        (plots_dir / "local_scene_frames").mkdir(parents=True, exist_ok=True)

    return scenario_dir


def export_scenarios(df: pd.DataFrame, candidates: pd.DataFrame, config: dict) -> list[Path]:
    output_root = resolve_project_path(config.get("export", {}).get("output_dir", "outputs")) / "scenarios"
    if config.get("export", {}).get("clean_scenarios_dir", True) and output_root.exists():
        for scenario_dir in output_root.glob("scenario_*"):
            if scenario_dir.is_dir():
                shutil.rmtree(scenario_dir)

    paths = []
    for index, candidate in candidates.reset_index(drop=True).iterrows():
        paths.append(export_scenario(df, candidate, config, index + 1))
    return paths
