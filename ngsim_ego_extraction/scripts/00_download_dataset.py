from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ngsim_ego.load_data import candidate_data_files, download_kaggle_dataset, load_config


def main() -> None:
    config = load_config()
    kaggle_path = download_kaggle_dataset(config)
    print(f"Path to KaggleHub dataset files: {kaggle_path}")

    data_files = candidate_data_files(config.get("raw_data_dir", "data/raw"))
    if data_files:
        print("Trajectory-like files available under data/raw/:")
        for path in data_files:
            print(path)
    else:
        print("No CSV/TXT/DAT files were copied under data/raw/. Check the KaggleHub path above.")


if __name__ == "__main__":
    main()
