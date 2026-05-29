from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ngsim_ego.candidates import extract_ego_candidates, save_candidate_outputs
from ngsim_ego.export import export_scenarios
from ngsim_ego.load_data import load_config, load_configured_trajectory_file, resolve_project_path
from ngsim_ego.preprocess import preprocess_dataset


def main() -> None:
    config = load_config()
    raw = load_configured_trajectory_file(config)
    df = preprocess_dataset(raw, config)

    candidates_path = resolve_project_path(config.get("export", {}).get("output_dir", "outputs")) / "candidates" / "ego_candidates.csv"
    if candidates_path.exists():
        candidates = pd.read_csv(candidates_path)
    else:
        candidates = extract_ego_candidates(df, config)
        save_candidate_outputs(candidates, config)

    paths = export_scenarios(df, candidates, config)
    print(f"Exported {len(paths)} scenarios")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
