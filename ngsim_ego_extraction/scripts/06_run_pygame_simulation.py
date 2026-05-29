from __future__ import annotations

import sys
from pathlib import Path

# Add src to python import search path
project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

try:
    from ngsim_visualizer.visualizer import ScenarioVisualizer
except ImportError as e:
    print(f"Error: Failed to import ScenarioVisualizer from ngsim_visualizer package: {e}")
    sys.exit(1)

def main():
    """Main execution point for launching the Pygame trajectory simulation."""
    scenarios_dir = project_root / "outputs" / "scenarios"
    
    if not scenarios_dir.exists() or not any(scenarios_dir.glob("scenario_*")):
        print(f"Error: No scenarios folder discovered in '{scenarios_dir}'.")
        print("Please run scenario extraction first:")
        print("  python scripts/02_extract_candidates.py")
        print("  python scripts/03_export_scenarios.py")
        sys.exit(1)
        
    print("==================================================================")
    print("          NGSIM US-101 Ego Scenario Pygame Visualizer             ")
    print("==================================================================")
    print("Controls:")
    print("  [Space]       Pause / Resume playback")
    print("  [<- / ->]     Rewind / Fast-forward 1.0 second")
    print("  [Up / Down]   Increase / Decrease playback speed rate")
    print("  [r]           Restart scenario from frame 0")
    print("  [[ / ]]       Switch to Previous / Next scenario folder")
    print("  [v]           Toggle View (Full Corridor vs Ego-Centered Zoom)")
    print("  [f]           Toggle Surrounding context (Compact vs Full pool)")
    print("  [t]           Toggle Ego past trail (-50m) on/off")
    print("  [p]           Toggle Ego future predicted path (+50m) on/off")
    print("  [1-9]         Jump to scenarios 1-9 directly")
    print("  [Esc / q]     Quit / Exit visualizer")
    print("==================================================================")
    
    # Run Pygame simulation visualizer
    visualizer = ScenarioVisualizer(scenarios_dir)
    visualizer.run()

if __name__ == "__main__":
    main()
