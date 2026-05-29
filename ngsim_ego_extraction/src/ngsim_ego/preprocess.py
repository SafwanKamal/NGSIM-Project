from __future__ import annotations

import re

import pandas as pd

from .units import acceleration_factor, position_factor, speed_factor


CANONICAL_COLUMNS = {
    "vehicle_id": "Vehicle_ID",
    "vehicleid": "Vehicle_ID",
    "frame_id": "Frame_ID",
    "frameid": "Frame_ID",
    "global_time": "Global_Time",
    "globaltime": "Global_Time",
    "local_x": "Local_X",
    "localx": "Local_X",
    "local_y": "Local_Y",
    "localy": "Local_Y",
    "global_x": "Global_X",
    "globalx": "Global_X",
    "global_y": "Global_Y",
    "globaly": "Global_Y",
    "v_length": "v_Length",
    "vlength": "v_Length",
    "v_width": "v_Width",
    "vwidth": "v_Width",
    "v_class": "v_Class",
    "vclass": "v_Class",
    "v_vel": "v_Vel",
    "vvel": "v_Vel",
    "v_acc": "v_Acc",
    "vacc": "v_Acc",
    "lane_id": "Lane_ID",
    "laneid": "Lane_ID",
    "preceding": "Preceding",
    "following": "Following",
    "space_headway": "Space_Headway",
    "spaceheadway": "Space_Headway",
    "time_headway": "Time_Headway",
    "timeheadway": "Time_Headway",
}

REQUIRED_COLUMNS = ["Vehicle_ID", "Frame_ID", "Local_X", "Local_Y", "v_Vel", "v_Acc", "Lane_ID"]


def _column_key(name: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", str(name).strip()).strip("_")
    return cleaned.lower()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for column in df.columns:
        canonical = CANONICAL_COLUMNS.get(_column_key(column))
        if canonical:
            rename_map[column] = canonical
    return df.rename(columns=rename_map)


def preprocess_dataset(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    data = normalize_columns(df).copy()
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required NGSIM columns after normalization: {missing}")

    for column in set(REQUIRED_COLUMNS + ["Global_Time", "Preceding", "Following", "Space_Headway", "Time_Headway"]):
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=REQUIRED_COLUMNS)
    data = data.sort_values(["Vehicle_ID", "Frame_ID"]).reset_index(drop=True)

    units_config = config.get("units", {})
    pos_factor = position_factor(units_config)
    vel_factor = speed_factor(units_config)
    acc_factor = acceleration_factor(units_config)

    data["Local_X_m"] = data["Local_X"] * pos_factor
    data["Local_Y_m"] = data["Local_Y"] * pos_factor
    data["v_Vel_mps"] = data["v_Vel"] * vel_factor
    data["v_Acc_mps2"] = data["v_Acc"] * acc_factor

    if "Space_Headway" in data.columns:
        data["Space_Headway_m"] = data["Space_Headway"] * pos_factor

    if "Global_Time" in data.columns and data["Global_Time"].notna().any():
        min_time = data["Global_Time"].min()
        data["time_s"] = (data["Global_Time"] - min_time) / 1000.0
    else:
        min_frame = data["Frame_ID"].min()
        data["time_s"] = (data["Frame_ID"] - min_frame) * 0.1

    return data

