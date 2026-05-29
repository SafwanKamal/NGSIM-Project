from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ngsim_ego.candidates import extract_ego_candidates, save_candidate_outputs
from ngsim_ego.load_data import load_config, load_configured_trajectory_file
from ngsim_ego.preprocess import preprocess_dataset


def main() -> None:
    config = load_config()
    raw = load_configured_trajectory_file(config)
    df = preprocess_dataset(raw, config)
    candidates = extract_ego_candidates(df, config)
    candidates_path, summary_path = save_candidate_outputs(candidates, config)
    print(f"Saved {len(candidates)} candidates to {candidates_path}")
    print(f"Saved candidate summary to {summary_path}")


if __name__ == "__main__":
    main()
