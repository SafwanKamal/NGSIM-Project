from __future__ import annotations

from pathlib import Path
import re
import shutil
from typing import Any

import pandas as pd
import yaml

NGSIM_TRAJECTORY_COLUMNS = [
    "Vehicle_ID",
    "Frame_ID",
    "Total_Frames",
    "Global_Time",
    "Local_X",
    "Local_Y",
    "Global_X",
    "Global_Y",
    "v_Length",
    "v_Width",
    "v_Class",
    "v_Vel",
    "v_Acc",
    "Lane_ID",
    "Preceding",
    "Following",
    "Space_Headway",
    "Time_Headway",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: str | Path = "config/us101_config.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = project_root() / config_path
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_root() / candidate


def candidate_data_files(raw_data_dir: str | Path = "data/raw") -> list[Path]:
    raw_dir = resolve_project_path(raw_data_dir)
    if not raw_dir.exists():
        return []
    suffixes = {".csv", ".txt", ".dat"}
    files = sorted(
        path
        for path in raw_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffixes
        and "traject" in path.name.lower()
        and "dictionary" not in path.name.lower()
        and "us101_official" not in {part.lower() for part in path.relative_to(raw_dir).parts[:-1]}
    )

    # The official DOT archive contains CSV and TXT versions of the same trajectory
    # files. Prefer TXT because it matches the original NGSIM fixed-column export.
    by_segment: dict[str, Path] = {}
    for path in files:
        segment = time_segment_from_filename(path)
        current = by_segment.get(segment)
        if current is None or (current.suffix.lower() != ".txt" and path.suffix.lower() == ".txt"):
            by_segment[segment] = path
    return sorted(by_segment.values(), key=lambda path: path.name.lower())


def time_segment_from_filename(path: Path) -> str:
    name = path.stem.lower()
    match = re.search(r"(\d{4})\s*(?:am|pm)?[-_](\d{4})\s*(am|pm)?", name)
    if not match:
        return path.stem

    start, end, suffix = match.groups()
    suffix = suffix or "am"

    def format_time(value: str) -> str:
        hour = int(value[:2])
        minute = int(value[2:])
        display_hour = hour if 1 <= hour <= 12 else ((hour - 1) % 12) + 1
        return f"{display_hour}:{minute:02d} {suffix.upper()}"

    return f"{format_time(start)} - {format_time(end)}"


def find_trajectory_file(config: dict[str, Any]) -> Path:
    configured_path = resolve_project_path(config.get("input_file", "data/raw/us101_trajectories.csv"))
    if configured_path.exists():
        return configured_path

    data_files = candidate_data_files(config.get("raw_data_dir", "data/raw"))
    if len(data_files) == 1:
        return data_files[0]
    if len(data_files) > 1:
        ranked = sorted(
            data_files,
            key=lambda path: (
                "us101" not in path.name.lower() and "us-101" not in path.name.lower(),
                path.name.lower(),
            ),
        )
        return ranked[0]

    raise FileNotFoundError(
        f"Trajectory file not found: {configured_path}. Run scripts/00_download_dataset.py, "
        "put the raw NGSIM file under data/raw/, or update config/us101_config.yaml."
    )


def load_trajectory_file(path: str | Path) -> pd.DataFrame:
    input_path = resolve_project_path(path)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Trajectory file not found: {input_path}. Put the raw NGSIM file under data/raw/ "
            "or update config/us101_config.yaml."
        )

    suffix = input_path.suffix.lower()
    if suffix in {".txt", ".dat"}:
        data = pd.read_csv(input_path, sep=r"\s+", header=None, names=NGSIM_TRAJECTORY_COLUMNS)
    else:
        data = pd.read_csv(input_path)

    data["source_file"] = input_path.name
    data["time_segment"] = time_segment_from_filename(input_path)
    return data


def load_configured_trajectory_file(config: dict[str, Any]) -> pd.DataFrame:
    if config.get("load_all_raw_files", True):
        files = candidate_data_files(config.get("raw_data_dir", "data/raw"))
        if files:
            frames = []
            for index, file_path in enumerate(files):
                data = load_trajectory_file(file_path)
                data["Original_Vehicle_ID"] = data["Vehicle_ID"]
                data["source_index"] = index
                if len(files) > 1:
                    data["Vehicle_ID"] = data["Vehicle_ID"] + (index * 1_000_000)
                frames.append(data)
            return pd.concat(frames, ignore_index=True)

    return load_trajectory_file(find_trajectory_file(config))


def download_kaggle_dataset(config: dict[str, Any]) -> Path:
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError(
            "kagglehub could not be imported. Run `pip install -e .` first; if the latest "
            "KaggleHub package fails, install the pinned project dependency `kagglehub<1`."
        ) from exc

    dataset = config.get("kaggle", {}).get("dataset")
    if not dataset:
        raise ValueError("Missing kaggle.dataset in config/us101_config.yaml.")

    downloaded_path = Path(kagglehub.dataset_download(dataset))
    if config.get("kaggle", {}).get("copy_to_raw_dir", True):
        raw_dir = resolve_project_path(config.get("raw_data_dir", "data/raw"))
        raw_dir.mkdir(parents=True, exist_ok=True)
        for file_path in downloaded_path.rglob("*"):
            if file_path.is_file():
                target = raw_dir / file_path.name
                if not target.exists():
                    shutil.copy2(file_path, target)
    return downloaded_path
