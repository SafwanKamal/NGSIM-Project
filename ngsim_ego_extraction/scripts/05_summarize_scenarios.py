from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ngsim_ego.load_data import load_config, resolve_project_path


def _read_metadata(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _lane_summary(ego: pd.DataFrame) -> str:
    lanes = [int(lane) for lane in ego["Lane_ID"].dropna().unique()]
    return ", ".join(str(lane) for lane in sorted(lanes))


def _maneuver_mask(ego: pd.DataFrame, window_seconds: float, lane_change_frame: int | None = None) -> pd.Series:
    mask = pd.Series(False, index=ego.index)
    if lane_change_frame is not None and "Frame_ID" in ego.columns:
        target = ego[ego["Frame_ID"].eq(lane_change_frame)]
        if not target.empty:
            change_time = float(target["scenario_time_s"].iloc[0])
            return ego["scenario_time_s"].between(change_time - window_seconds, change_time + window_seconds, inclusive="both")

    lanes = ego["Lane_ID"].reset_index(drop=True)
    changes = lanes.index[(lanes != lanes.shift(1)) & lanes.shift(1).notna()].tolist()
    if not changes:
        return mask
    times = ego["scenario_time_s"].reset_index(drop=True)
    for change_index in changes:
        change_time = float(times.iloc[change_index])
        mask |= times.between(change_time - window_seconds, change_time + window_seconds, inclusive="both")
    mask.index = ego.index
    return mask


def _leader_free_summary(
    ego: pd.DataFrame,
    threshold_m: float,
    mode: str,
    window_seconds: float,
    lane_change_frame: int | None = None,
) -> tuple[float, str]:
    no_preceding = ego["Preceding"].fillna(0).eq(0) if "Preceding" in ego.columns else pd.Series(False, index=ego.index)
    far_preceding = ego["Space_Headway_m"].gt(threshold_m) if "Space_Headway_m" in ego.columns else pd.Series(False, index=ego.index)
    leader_free = no_preceding | far_preceding

    if mode == "maneuver_windows":
        checked = _maneuver_mask(ego, window_seconds, lane_change_frame)
        if int(checked.sum()) == 0:
            return 1.0, "no lane-change maneuver window"
        fraction = float(leader_free[checked].mean())
        label = "target maneuver-window" if lane_change_frame is not None else "maneuver-window"
        return fraction, f"{fraction:.1%} of {label} frames are locally leader-free"

    fraction = float(leader_free.mean()) if len(ego) else 0.0
    return fraction, f"{fraction:.1%} of ego frames are locally leader-free"


def build_summary(config: dict) -> str:
    output_dir = resolve_project_path(config.get("export", {}).get("output_dir", "outputs"))
    scenarios_root = output_dir / "scenarios"
    scenario_dirs = sorted(path for path in scenarios_root.glob("scenario_*") if path.is_dir())
    threshold_m = float(config.get("candidate_selection", {}).get("local_leader_free_distance_m", 75))
    mode = config.get("candidate_selection", {}).get("leader_check_mode", "full_window")
    window_seconds = float(config.get("candidate_selection", {}).get("lane_change_window_seconds", 5))

    lines = [
        "# NGSIM US-101 Scenario Summary",
        "",
        f"Scenario folder: `{scenarios_root}`",
        f"Scenario count: {len(scenario_dirs)}",
        "",
        "| Scenario | Ego vehicle | Time interval | Road length (m) | Duration (s) | Lanes | Lane changes | Type | Locally leader-free | Compact surrounding | Full surrounding |",
        "|---|---:|---|---:|---:|---|---:|---|---|---:|---:|",
    ]

    for scenario_dir in scenario_dirs:
        metadata = _read_metadata(scenario_dir / "metadata.yaml")
        ego = pd.read_csv(scenario_dir / "ego_trajectory.csv")
        lane_changes = pd.read_csv(scenario_dir / "lane_changes.csv")
        surrounding = pd.read_csv(scenario_dir / "surrounding_vehicles.csv")
        full_path = scenario_dir / "surrounding_vehicles_full.csv"
        surrounding_full = pd.read_csv(full_path) if full_path.exists() else surrounding
        lane_change_frame = metadata.get("lane_change_frame")
        leader_fraction, leader_text = _leader_free_summary(ego, threshold_m, mode, window_seconds, lane_change_frame)
        lines.append(
            "| {scenario} | {vehicle_id} | {time_segment} | {road_length:.1f} | {duration:.1f} | {lanes} | {lane_changes} | {candidate_type} | {leader_text} | {surrounding_count} | {surrounding_full_count} |".format(
                scenario=scenario_dir.name,
                vehicle_id=int(metadata.get("vehicle_id", ego["Vehicle_ID"].iloc[0])),
                time_segment=metadata.get("time_segment", "unknown"),
                road_length=float(metadata.get("road_length_m", 0.0)),
                duration=float(metadata.get("duration_seconds", ego["scenario_time_s"].max())),
                lanes=_lane_summary(ego),
                lane_changes=len(lane_changes),
                candidate_type=metadata.get("candidate_type", ""),
                leader_text=leader_text,
                surrounding_count=int(surrounding["Vehicle_ID"].nunique()) if not surrounding.empty else 0,
                surrounding_full_count=int(surrounding_full["Vehicle_ID"].nunique()) if not surrounding_full.empty else 0,
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `Locally leader-free` means the ego has no close preceding vehicle in its local influence region; it does not mean the whole road ahead is empty.",
            "- Plots for each scenario are stored in that scenario's `plots/` folder.",
            "- Review the plots before using a scenario for simulator comparison.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    config = load_config()
    output_dir = resolve_project_path(config.get("export", {}).get("output_dir", "outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_summary(config)
    report_path = output_dir / "scenario_summary.md"
    report_path.write_text(report, encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    main()
