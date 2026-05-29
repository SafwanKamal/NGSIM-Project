from __future__ import annotations

import pandas as pd


def _scenario_time(df: pd.DataFrame, ego: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    scenario_start_time = float(ego["time_s"].iloc[0])
    result["scenario_time_s"] = result["time_s"] - scenario_start_time
    return result


def extract_surrounding_vehicles(df: pd.DataFrame, ego: pd.DataFrame, config: dict) -> pd.DataFrame:
    settings = config.get("surrounding_vehicles", {})
    behind_m = float(settings.get("behind_distance_m", 50))
    ahead_m = float(settings.get("ahead_distance_m", 100))
    lane_radius = int(settings.get("lane_radius", 1))

    selected_indexes = []
    if "source_index" in df.columns and "source_index" in ego.columns:
        source_value = ego["source_index"].iloc[0]
        df = df[df["source_index"].eq(source_value)]

    frame_groups = {frame: frame_df for frame, frame_df in df.groupby("Frame_ID")}
    for _, ego_row in ego.iterrows():
        frame_df = frame_groups.get(ego_row["Frame_ID"])
        if frame_df is None:
            continue

        lane_delta = (frame_df["Lane_ID"] - ego_row["Lane_ID"]).abs()
        y_delta = frame_df["Local_Y_m"] - ego_row["Local_Y_m"]
        mask = (
            frame_df["Vehicle_ID"].ne(ego_row["Vehicle_ID"])
            & lane_delta.le(lane_radius)
            & y_delta.ge(-behind_m)
            & y_delta.le(ahead_m)
        )
        selected_indexes.extend(frame_df.index[mask].tolist())

    if not selected_indexes:
        return pd.DataFrame(columns=df.columns)

    surrounding = df.loc[sorted(set(selected_indexes))].copy()
    surrounding = _scenario_time(surrounding, ego)
    return surrounding.sort_values(["Frame_ID", "Vehicle_ID"]).reset_index(drop=True)


def compact_surrounding_vehicles(full_surrounding: pd.DataFrame, ego: pd.DataFrame, config: dict) -> pd.DataFrame:
    if full_surrounding.empty:
        return full_surrounding.copy()

    settings = config.get("surrounding_vehicles", {})
    behind_m = float(settings.get("compact_behind_distance_m", settings.get("behind_distance_m", 50)))
    ahead_m = float(settings.get("compact_ahead_distance_m", settings.get("ahead_distance_m", 100)))
    min_frames = int(settings.get("compact_min_frames", 1))

    ego_by_frame = ego.set_index("Frame_ID")
    selected_indexes = []
    for frame_id, frame_df in full_surrounding.groupby("Frame_ID"):
        if frame_id not in ego_by_frame.index:
            continue

        ego_row = ego_by_frame.loc[frame_id]
        if isinstance(ego_row, pd.DataFrame):
            ego_row = ego_row.iloc[0]

        frame_df = frame_df.copy()
        frame_df["relative_y_m"] = frame_df["Local_Y_m"] - float(ego_row["Local_Y_m"])
        frame_df = frame_df[(frame_df["relative_y_m"] >= -behind_m) & (frame_df["relative_y_m"] <= ahead_m)]
        if frame_df.empty:
            continue

        for lane_id, lane_df in frame_df.groupby("Lane_ID"):
            ahead = lane_df[lane_df["relative_y_m"] >= 0].sort_values("relative_y_m").head(1)
            behind = lane_df[lane_df["relative_y_m"] < 0].sort_values("relative_y_m", ascending=False).head(1)
            selected_indexes.extend(ahead.index.tolist())
            selected_indexes.extend(behind.index.tolist())

    if not selected_indexes:
        return pd.DataFrame(columns=full_surrounding.columns)

    compact = full_surrounding.loc[sorted(set(selected_indexes))].copy()
    if min_frames > 1 and not compact.empty:
        counts = compact.groupby("Vehicle_ID")["Frame_ID"].transform("count")
        compact = compact[counts >= min_frames].copy()

    return compact.sort_values(["Frame_ID", "Vehicle_ID"]).reset_index(drop=True)
