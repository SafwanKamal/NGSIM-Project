from __future__ import annotations

from pathlib import Path

import pandas as pd

from .load_data import resolve_project_path
from .segment import infer_time_segment


CANDIDATE_COLUMNS = [
    "Vehicle_ID",
    "Original_Vehicle_ID",
    "source_file",
    "time_segment",
    "candidate_type",
    "lane_change_frame",
    "start_frame",
    "end_frame",
    "duration_seconds",
    "valid_fraction",
    "start_lane",
    "middle_lane_valid",
    "min_space_headway_m",
    "mean_space_headway_m",
    "has_lane_change",
    "num_lane_changes",
    "start_Local_X",
    "start_Local_Y",
    "end_Local_X",
    "end_Local_Y",
    "mean_speed_mps",
    "selection_reason",
]


def get_middle_lanes(df: pd.DataFrame, config: dict) -> list[int]:
    selection = config.get("candidate_selection", {})
    if not selection.get("auto_detect_middle_lanes", True):
        return [int(lane) for lane in selection.get("manual_middle_lanes", [])]

    all_lanes = sorted(int(lane) for lane in df["Lane_ID"].dropna().unique())
    if len(all_lanes) <= 2:
        return all_lanes
    return all_lanes[1:-1]


def count_lane_changes(vehicle_df: pd.DataFrame) -> int:
    lanes = vehicle_df["Lane_ID"].reset_index(drop=True)
    return int((lanes != lanes.shift(1)).iloc[1:].sum())


def lane_change_indexes(vehicle_df: pd.DataFrame) -> list[int]:
    lanes = vehicle_df["Lane_ID"].reset_index(drop=True)
    return lanes.index[(lanes != lanes.shift(1)) & lanes.shift(1).notna()].tolist()


def maneuver_window_mask(vehicle_df: pd.DataFrame, window_seconds: float) -> pd.Series:
    mask = pd.Series(False, index=vehicle_df.index)
    change_indexes = lane_change_indexes(vehicle_df)
    if not change_indexes:
        return mask

    times = vehicle_df["time_s"]
    for change_index in change_indexes:
        change_time = float(vehicle_df.loc[change_index, "time_s"])
        mask |= times.between(change_time - window_seconds, change_time + window_seconds, inclusive="both")
    return mask


def _build_candidate_row(
    vehicle_id: int,
    window_df: pd.DataFrame,
    config: dict,
    valid_fraction: float,
    middle_lane_valid: bool,
    selection_reason: str,
    candidate_type: str = "vehicle_window",
    lane_change_frame: int | None = None,
    leader_checked_frames: int = 0,
) -> dict:
    lane_changes = count_lane_changes(window_df)
    headway = window_df.get("Space_Headway_m", pd.Series(dtype="float64"))
    start = window_df.iloc[0]
    end = window_df.iloc[-1]
    return {
        "Vehicle_ID": int(vehicle_id),
        "Original_Vehicle_ID": int(start.get("Original_Vehicle_ID", vehicle_id)),
        "source_file": start.get("source_file", ""),
        "time_segment": infer_time_segment(start, config),
        "candidate_type": candidate_type,
        "lane_change_frame": lane_change_frame,
        "start_frame": int(start["Frame_ID"]),
        "end_frame": int(end["Frame_ID"]),
        "duration_seconds": round(float(end["time_s"] - start["time_s"]), 3),
        "valid_fraction": round(valid_fraction, 3),
        "start_lane": int(start["Lane_ID"]),
        "middle_lane_valid": middle_lane_valid,
        "min_space_headway_m": round(float(headway.min()), 3) if not headway.empty else None,
        "mean_space_headway_m": round(float(headway.mean()), 3) if not headway.empty else None,
        "has_lane_change": lane_changes > 0,
        "num_lane_changes": lane_changes,
        "start_Local_X": round(float(start["Local_X_m"]), 3),
        "start_Local_Y": round(float(start["Local_Y_m"]), 3),
        "end_Local_X": round(float(end["Local_X_m"]), 3),
        "end_Local_Y": round(float(end["Local_Y_m"]), 3),
        "mean_speed_mps": round(float(window_df["v_Vel_mps"].mean()), 3),
        "selection_reason": selection_reason,
        "leader_check_mode": config.get("candidate_selection", {}).get("leader_check_mode", "full_window"),
        "leader_checked_frames": int(leader_checked_frames),
    }


def _extract_lane_change_event_candidates(df: pd.DataFrame, config: dict, middle_lanes: list[int]) -> list[dict]:
    selection = config.get("candidate_selection", {})
    road = config.get("road", {})
    leader_threshold_m = float(selection.get("local_leader_free_distance_m", 75))
    lane_change_window_s = float(selection.get("lane_change_window_seconds", 5))
    required_fraction = float(selection.get("require_no_close_leader_fraction", 1.0))
    required_middle_fraction = float(selection.get("require_middle_lane_fraction", 1.0))
    min_duration_s = float(selection.get("min_duration_seconds", 10))
    crop_length_m = float(road.get("crop_length_m", 500))
    min_window_distance_fraction = float(selection.get("min_window_distance_fraction", 0.9))
    middle_set = set(middle_lanes)

    candidates = []
    for vehicle_id, vehicle_df in df.groupby("Vehicle_ID"):
        vehicle_df = vehicle_df.sort_values("Frame_ID").reset_index(drop=True)
        y_values = vehicle_df["Local_Y_m"].to_numpy()
        middle_mask = vehicle_df["Lane_ID"].isin(middle_lanes).to_numpy()
        no_preceding = (
            vehicle_df["Preceding"].fillna(0).eq(0)
            if "Preceding" in vehicle_df.columns
            else pd.Series(True, index=vehicle_df.index)
        )
        far_preceding = (
            vehicle_df["Space_Headway_m"].gt(leader_threshold_m)
            if "Space_Headway_m" in vehicle_df.columns
            else pd.Series(False, index=vehicle_df.index)
        )
        leader_ok = (no_preceding | far_preceding).to_numpy()
        lanes = vehicle_df["Lane_ID"].reset_index(drop=True)

        for change_index in lane_change_indexes(vehicle_df):
            from_lane = int(lanes.iloc[change_index - 1])
            to_lane = int(lanes.iloc[change_index])
            if from_lane not in middle_set or to_lane not in middle_set:
                continue

            change_time = float(vehicle_df.at[change_index, "time_s"])
            maneuver_mask = vehicle_df["time_s"].between(
                change_time - lane_change_window_s,
                change_time + lane_change_window_s,
                inclusive="both",
            ).to_numpy()
            leader_checked_frames = int(maneuver_mask.sum())
            if leader_checked_frames == 0:
                continue
            valid_fraction = float(leader_ok[maneuver_mask].mean())
            if valid_fraction < required_fraction:
                continue

            best_window = None
            for start_index in range(change_index + 1):
                if y_values[start_index] + crop_length_m < y_values[change_index]:
                    continue
                end_index = int(y_values.searchsorted(y_values[start_index] + crop_length_m, side="right") - 1)
                if end_index < change_index or end_index <= start_index:
                    continue
                distance_m = float(y_values[end_index] - y_values[start_index])
                duration_s = float(vehicle_df.at[end_index, "time_s"] - vehicle_df.at[start_index, "time_s"])
                if duration_s < min_duration_s:
                    continue
                if road.get("use_crop", True) and distance_m < crop_length_m * min_window_distance_fraction:
                    continue
                middle_fraction = float(middle_mask[start_index : end_index + 1].mean())
                if middle_fraction < required_middle_fraction:
                    continue

                center_distance = abs(((start_index + end_index) / 2) - change_index)
                score = (distance_m, duration_s, -center_distance)
                if best_window is None or score > best_window["score"]:
                    best_window = {"start_index": start_index, "end_index": end_index, "score": score}

            if best_window is None:
                continue

            window_df = vehicle_df.iloc[best_window["start_index"] : best_window["end_index"] + 1].copy().reset_index(drop=True)
            candidates.append(
                _build_candidate_row(
                    int(vehicle_id),
                    window_df,
                    config,
                    valid_fraction,
                    True,
                    "500 m window around target lane-change event; target maneuver window is locally leader-free",
                    "lane_change_event",
                    int(vehicle_df.at[change_index, "Frame_ID"]),
                    leader_checked_frames,
                )
            )
    return candidates


def extract_ego_candidates(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    middle_lanes = get_middle_lanes(df, config)
    selection = config.get("candidate_selection", {})
    road = config.get("road", {})
    min_duration_s = float(selection.get("min_duration_seconds", 10))
    leader_threshold_m = float(selection.get("local_leader_free_distance_m", 75))
    leader_check_mode = selection.get("leader_check_mode", "full_window")
    lane_change_window_s = float(selection.get("lane_change_window_seconds", 5))
    required_fraction = float(selection.get("require_no_close_leader_fraction", 0.8))
    required_middle_fraction = float(selection.get("require_middle_lane_fraction", 0.8))
    min_window_distance_fraction = float(selection.get("min_window_distance_fraction", 0.9))
    max_candidates = int(selection.get("max_candidates_to_export", 6))
    crop_length_m = float(road.get("crop_length_m", 500))

    if selection.get("prefer_lane_change_events", False):
        event_candidates = _extract_lane_change_event_candidates(df, config, middle_lanes)
        if event_candidates:
            result = pd.DataFrame(event_candidates)
            result = result.drop_duplicates(subset=["Vehicle_ID", "start_frame", "end_frame"])
            result = result.sort_values(
                ["duration_seconds", "mean_space_headway_m", "num_lane_changes"],
                ascending=[False, False, True],
                na_position="last",
            )
            
            # Balance candidates evenly across all middle lanes to prevent left/right lane bias
            selected_candidates = []
            candidates_per_lane = max(1, max_candidates // len(middle_lanes))
            lane_counts = {lane: 0 for lane in middle_lanes}
            
            # First pass: collect up to quota per lane
            for _, row in result.iterrows():
                slane = int(row["start_lane"])
                if slane in lane_counts and lane_counts[slane] < candidates_per_lane:
                    selected_candidates.append(row)
                    lane_counts[slane] += 1
            
            # Second pass: fill up the remaining spots with best overall candidates
            used_keys = set((r["Vehicle_ID"], r["start_frame"]) for r in selected_candidates)
            for _, row in result.iterrows():
                if len(selected_candidates) >= max_candidates:
                    break
                key = (row["Vehicle_ID"], row["start_frame"])
                if key not in used_keys:
                    selected_candidates.append(row)
                    used_keys.add(key)
            
            balanced_result = pd.DataFrame(selected_candidates)
            balanced_result = balanced_result.sort_values(
                ["duration_seconds", "mean_space_headway_m", "num_lane_changes"],
                ascending=[False, False, True],
                na_position="last",
            ).reset_index(drop=True)
            return balanced_result

    candidates = []
    for vehicle_id, vehicle_df in df.groupby("Vehicle_ID"):
        vehicle_df = vehicle_df.sort_values("Frame_ID").reset_index(drop=True)
        middle_lane_mask = vehicle_df["Lane_ID"].isin(middle_lanes)
        no_preceding_mask = (
            vehicle_df["Preceding"].fillna(0).eq(0)
            if "Preceding" in vehicle_df.columns
            else pd.Series(True, index=vehicle_df.index)
        )
        if "Space_Headway_m" in vehicle_df.columns:
            far_preceding_mask = vehicle_df["Space_Headway_m"] > leader_threshold_m
        else:
            far_preceding_mask = pd.Series(False, index=vehicle_df.index)

        locally_leader_free_mask = no_preceding_mask | far_preceding_mask
        start_mask = middle_lane_mask
        if not bool(start_mask.any()):
            continue

        y_values = vehicle_df["Local_Y_m"].to_numpy()
        lane_ok = middle_lane_mask.to_numpy()
        leader_ok = locally_leader_free_mask.to_numpy()
        maneuver_mask = maneuver_window_mask(vehicle_df, lane_change_window_s).to_numpy()
        lane_bad_cumsum = (~lane_ok).cumsum()
        if leader_check_mode == "maneuver_windows":
            leader_check_mask = maneuver_mask
        else:
            leader_check_mask = pd.Series(True, index=vehicle_df.index).to_numpy()
        leader_bad_cumsum = (leader_check_mask & ~leader_ok).cumsum()
        leader_check_cumsum = leader_check_mask.cumsum()

        best_window = None
        for start_index in start_mask[start_mask].index:
            start_y = y_values[start_index]
            end_y = start_y + crop_length_m if road.get("use_crop", True) else float(road.get("full_segment_length_m", 640))
            end_index = int(y_values.searchsorted(end_y, side="right") - 1)
            if end_index <= start_index:
                continue

            duration_s = float(vehicle_df.at[end_index, "time_s"] - vehicle_df.at[start_index, "time_s"])
            distance_m = float(vehicle_df.at[end_index, "Local_Y_m"] - vehicle_df.at[start_index, "Local_Y_m"])
            if duration_s < min_duration_s:
                continue
            if road.get("use_crop", True) and distance_m < crop_length_m * min_window_distance_fraction:
                continue

            window_len = end_index - start_index + 1
            lane_bad = int(lane_bad_cumsum[end_index] - (lane_bad_cumsum[start_index - 1] if start_index else 0))
            leader_bad = int(leader_bad_cumsum[end_index] - (leader_bad_cumsum[start_index - 1] if start_index else 0))
            leader_checked = int(leader_check_cumsum[end_index] - (leader_check_cumsum[start_index - 1] if start_index else 0))
            middle_fraction = 1.0 - lane_bad / window_len
            valid_fraction = 1.0 if leader_checked == 0 else 1.0 - leader_bad / leader_checked
            if middle_fraction < required_middle_fraction or valid_fraction < required_fraction:
                continue

            if best_window is None or duration_s > best_window["duration_seconds"]:
                best_window = {
                    "start_index": start_index,
                    "end_index": end_index,
                    "duration_seconds": duration_s,
                    "distance_m": distance_m,
                    "middle_fraction": middle_fraction,
                    "valid_fraction": valid_fraction,
                    "leader_checked_frames": leader_checked,
                }

        if best_window is None:
            continue

        start_index = best_window["start_index"]
        end_index = best_window["end_index"]
        window_df = vehicle_df.iloc[start_index : end_index + 1].copy()
        lane_changes = count_lane_changes(window_df)
        window_maneuver_mask = maneuver_window_mask(window_df.reset_index(drop=True), lane_change_window_s)
        headway = window_df.get("Space_Headway_m", pd.Series(dtype="float64"))
        middle_lane_valid = bool(best_window["middle_fraction"] >= required_middle_fraction)
        start = window_df.iloc[0]
        end = window_df.iloc[-1]

        candidates.append(
            {
                "Vehicle_ID": int(vehicle_id),
                "Original_Vehicle_ID": int(start.get("Original_Vehicle_ID", vehicle_id)),
                "source_file": start.get("source_file", ""),
                "time_segment": infer_time_segment(start, config),
                "start_frame": int(start["Frame_ID"]),
                "end_frame": int(end["Frame_ID"]),
                "duration_seconds": round(best_window["duration_seconds"], 3),
                "valid_fraction": round(best_window["valid_fraction"], 3),
                "start_lane": int(start["Lane_ID"]),
                "middle_lane_valid": middle_lane_valid,
                "min_space_headway_m": round(float(headway.min()), 3) if not headway.empty else None,
                "mean_space_headway_m": round(float(headway.mean()), 3) if not headway.empty else None,
                "has_lane_change": lane_changes > 0,
                "num_lane_changes": lane_changes,
                "start_Local_X": round(float(start["Local_X_m"]), 3),
                "start_Local_Y": round(float(start["Local_Y_m"]), 3),
                "end_Local_X": round(float(end["Local_X_m"]), 3),
                "end_Local_Y": round(float(end["Local_Y_m"]), 3),
                "mean_speed_mps": round(float(window_df["v_Vel_mps"].mean()), 3),
                "selection_reason": (
                    "500 m window in middle lanes; locally leader-free checked during lane-change maneuver windows"
                    if leader_check_mode == "maneuver_windows"
                    else "500 m window in middle lanes and locally leader-free for required fraction"
                ),
                "leader_check_mode": leader_check_mode,
                "leader_checked_frames": int(window_maneuver_mask.sum()) if leader_check_mode == "maneuver_windows" else len(window_df),
            }
        )

    if not candidates:
        return pd.DataFrame(columns=CANDIDATE_COLUMNS)

    result = pd.DataFrame(candidates)
    if selection.get("leader_check_mode", "full_window") == "maneuver_windows":
        result = result.sort_values(
            ["has_lane_change", "duration_seconds", "mean_space_headway_m", "num_lane_changes"],
            ascending=[False, False, False, True],
            na_position="last",
        )
    else:
        result = result.sort_values(
            ["duration_seconds", "mean_space_headway_m", "num_lane_changes"],
            ascending=[False, False, True],
            na_position="last",
        )
        
    # Balance candidates evenly across all middle lanes to prevent left/right lane bias
    selected_candidates = []
    candidates_per_lane = max(1, max_candidates // len(middle_lanes))
    lane_counts = {lane: 0 for lane in middle_lanes}
    
    # First pass: collect up to quota per lane
    for _, row in result.iterrows():
        slane = int(row["start_lane"])
        if slane in lane_counts and lane_counts[slane] < candidates_per_lane:
            selected_candidates.append(row)
            lane_counts[slane] += 1
            
    # Second pass: fill up remaining spots with best overall candidates
    used_keys = set((r["Vehicle_ID"], r["start_frame"]) for r in selected_candidates)
    for _, row in result.iterrows():
        if len(selected_candidates) >= max_candidates:
            break
        key = (row["Vehicle_ID"], row["start_frame"])
        if key not in used_keys:
            selected_candidates.append(row)
            used_keys.add(key)
            
    balanced_result = pd.DataFrame(selected_candidates)
    if selection.get("leader_check_mode", "full_window") == "maneuver_windows":
        balanced_result = balanced_result.sort_values(
            ["has_lane_change", "duration_seconds", "mean_space_headway_m", "num_lane_changes"],
            ascending=[False, False, False, True],
            na_position="last",
        ).reset_index(drop=True)
    else:
        balanced_result = balanced_result.sort_values(
            ["duration_seconds", "mean_space_headway_m", "num_lane_changes"],
            ascending=[False, False, True],
            na_position="last",
        ).reset_index(drop=True)
    return balanced_result


def save_candidate_outputs(candidates: pd.DataFrame, config: dict) -> tuple[Path, Path]:
    output_dir = resolve_project_path(config.get("export", {}).get("output_dir", "outputs")) / "candidates"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = output_dir / "ego_candidates.csv"
    summary_path = output_dir / "ego_candidate_summary.csv"
    candidates.to_csv(candidates_path, index=False)
    candidates.describe(include="all").to_csv(summary_path)
    return candidates_path, summary_path
