from __future__ import annotations

import pandas as pd


def infer_time_segment(row: pd.Series, config: dict) -> str:
    if "time_segment" in row and pd.notna(row["time_segment"]):
        return str(row["time_segment"])

    segments = config.get("time_segments", [])
    if not segments:
        return "unknown"
    time_s = float(row.get("time_s", 0.0))
    index = min(int(time_s // (15 * 60)), len(segments) - 1)
    return segments[index].get("label", segments[index].get("name", "unknown"))


def scenario_bounds(ego: pd.DataFrame, config: dict) -> tuple[float, float]:
    start_y = float(ego["Local_Y_m"].iloc[0])
    road_config = config.get("road", {})
    if road_config.get("use_crop", True):
        length_m = float(road_config.get("crop_length_m", 500))
        return start_y, start_y + length_m

    length_m = float(road_config.get("full_segment_length_m", 640))
    return 0.0, length_m
