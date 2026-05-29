from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ngsim_ego.load_data import load_config, resolve_project_path
from ngsim_ego.plots import plot_ego_scenario


def main() -> None:
    config = load_config()
    scenarios_root = resolve_project_path(config.get("export", {}).get("output_dir", "outputs")) / "scenarios"
    scenario_dirs = sorted(path for path in scenarios_root.glob("scenario_*") if path.is_dir())
    for scenario_dir in scenario_dirs:
        ego_path = scenario_dir / "ego_trajectory.csv"
        if not ego_path.exists():
            continue
        ego = pd.read_csv(ego_path)
        plot_ego_scenario(ego, scenario_dir / "plots")
        print(f"Updated plots for {scenario_dir}")
    if not scenario_dirs:
        print(f"No scenarios found under {scenarios_root}")


if __name__ == "__main__":
    main()

