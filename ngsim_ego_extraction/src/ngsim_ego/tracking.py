from __future__ import annotations

import pandas as pd

from .segment import scenario_bounds


def detect_lane_changes(ego: pd.DataFrame) -> pd.DataFrame:
    lanes = ego["Lane_ID"].reset_index(drop=True)
    changes = ego.reset_index(drop=True).loc[(lanes != lanes.shift(1)) & lanes.shift(1).notna()].copy()
    if changes.empty:
        return pd.DataFrame(
            columns=["Vehicle_ID", "Frame_ID", "time_seconds", "from_lane", "to_lane", "Local_X", "Local_Y", "v_Vel", "v_Acc"]
        )
    changes["from_lane"] = lanes.shift(1).loc[changes.index].astype(int).values
    changes["to_lane"] = changes["Lane_ID"].astype(int)
    changes["time_seconds"] = changes["scenario_time_s"]
    return changes[["Vehicle_ID", "Frame_ID", "time_seconds", "from_lane", "to_lane", "Local_X_m", "Local_Y_m", "v_Vel_mps", "v_Acc_mps2"]].rename(
        columns={"Local_X_m": "Local_X", "Local_Y_m": "Local_Y", "v_Vel_mps": "v_Vel", "v_Acc_mps2": "v_Acc"}
    )


def create_ego_scenario(
    df: pd.DataFrame,
    vehicle_id: int,
    config: dict,
    start_frame: int | None = None,
    end_frame: int | None = None,
) -> dict:
    ego = df[df["Vehicle_ID"].eq(vehicle_id)].sort_values("Frame_ID").copy()
    if ego.empty:
        raise ValueError(f"Vehicle_ID {vehicle_id} not found in preprocessed dataset.")

    if start_frame is not None and end_frame is not None:
        ego = ego[(ego["Frame_ID"] >= start_frame) & (ego["Frame_ID"] <= end_frame)].copy()
        start_y = float(ego["Local_Y_m"].iloc[0])
        end_y = float(ego["Local_Y_m"].iloc[-1])
    else:
        start_y, end_y = scenario_bounds(ego, config)
        ego = ego[(ego["Local_Y_m"] >= start_y) & (ego["Local_Y_m"] <= end_y)].copy()
    if ego.empty:
        raise ValueError(f"Vehicle_ID {vehicle_id} has no rows inside selected road bounds.")

    scenario_start_time = float(ego["time_s"].iloc[0])
    ego["scenario_time_s"] = ego["time_s"] - scenario_start_time
    lane_changes = detect_lane_changes(ego)

    return {
        "vehicle_id": int(vehicle_id),
        "ego": ego,
        "lane_changes": lane_changes,
        "segment_start_y_m": start_y,
        "segment_end_y_m": end_y,
        "road_length_m": end_y - start_y,
    }
