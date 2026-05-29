from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ngsim_ego.load_data import candidate_data_files, load_config, load_configured_trajectory_file, resolve_project_path
from ngsim_ego.preprocess import normalize_columns


def main() -> None:
    config = load_config()
    input_files = candidate_data_files(config.get("raw_data_dir", "data/raw"))
    df = normalize_columns(load_configured_trajectory_file(config))
    output_dir = resolve_project_path(config.get("export", {}).get("output_dir", "outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        f"Input files: {[str(path) for path in input_files]}",
        f"Columns: {list(df.columns)}",
        f"Rows: {len(df):,}",
        f"Vehicles: {df['Vehicle_ID'].nunique():,}" if "Vehicle_ID" in df.columns else "Vehicles: Vehicle_ID column not found",
        f"Lane IDs: {sorted(df['Lane_ID'].dropna().unique().tolist())}" if "Lane_ID" in df.columns else "Lane IDs: Lane_ID column not found",
        f"Frame_ID min/max: {df['Frame_ID'].min()} / {df['Frame_ID'].max()}" if "Frame_ID" in df.columns else "Frame_ID min/max: Frame_ID column not found",
        f"Global_Time min/max: {df['Global_Time'].min()} / {df['Global_Time'].max()}" if "Global_Time" in df.columns else "Global_Time min/max: Global_Time column not found",
        f"Local_X range: {df['Local_X'].min()} / {df['Local_X'].max()}" if "Local_X" in df.columns else "Local_X range: Local_X column not found",
        f"Local_Y range: {df['Local_Y'].min()} / {df['Local_Y'].max()}" if "Local_Y" in df.columns else "Local_Y range: Local_Y column not found",
    ]

    report = "\n".join(lines)
    print(report)
    (output_dir / "dataset_inspection.txt").write_text(report + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
