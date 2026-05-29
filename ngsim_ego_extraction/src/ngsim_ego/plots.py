from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _save_line_plot(path: Path, x, y, xlabel: str, ylabel: str, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, y, linewidth=1.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_ego_scenario(ego: pd.DataFrame, output_dir: str | Path) -> None:
    plots_dir = Path(output_dir)
    _save_line_plot(
        plots_dir / "ego_xy.png",
        ego["Local_X_m"],
        ego["Local_Y_m"],
        "Local X (m)",
        "Local Y (m)",
        "Ego Trajectory",
    )
    _save_line_plot(
        plots_dir / "ego_lane_over_time.png",
        ego["scenario_time_s"],
        ego["Lane_ID"],
        "Scenario time (s)",
        "Lane ID",
        "Ego Lane Over Time",
    )
    _save_line_plot(
        plots_dir / "ego_speed_over_time.png",
        ego["scenario_time_s"],
        ego["v_Vel_mps"],
        "Scenario time (s)",
        "Speed (m/s)",
        "Ego Speed Over Time",
    )
    _save_line_plot(
        plots_dir / "ego_acceleration_over_time.png",
        ego["scenario_time_s"],
        ego["v_Acc_mps2"],
        "Scenario time (s)",
        "Acceleration (m/s^2)",
        "Ego Acceleration Over Time",
    )


def plot_ego_maneuver_window(ego_maneuver: pd.DataFrame, output_dir: str | Path) -> None:
    if ego_maneuver.empty:
        return

    plots_dir = Path(output_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    x = ego_maneuver["maneuver_time_s"]

    fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    axes[0].plot(x, ego_maneuver["Local_X_m"], color="#2ca02c", linewidth=1.4)
    axes[0].set_ylabel("Local X (m)")

    ax_y = axes[0].twinx()
    longitudinal_progress = ego_maneuver["Local_Y_m"] - ego_maneuver["Local_Y_m"].iloc[0]
    ax_y.plot(x, longitudinal_progress, color="#9467bd", linewidth=1.1, alpha=0.65)
    ax_y.set_ylabel("Y progress (m)")

    axes[1].plot(x, ego_maneuver["v_Vel_mps"], color="#1f77b4", linewidth=1.4)
    axes[1].set_ylabel("Velocity (m/s)")

    axes[2].plot(x, ego_maneuver["v_Acc_mps2"], color="#d62728", linewidth=1.4)
    axes[2].set_ylabel("Acceleration (m/s^2)")
    axes[2].set_xlabel("Time from target lane change (s)")

    for ax in axes:
        ax.axvline(0, color="black", linestyle="--", linewidth=1.0, alpha=0.7)
        ax.grid(True, alpha=0.25)

    fig.suptitle("Ego Maneuver Window")
    fig.tight_layout()
    fig.savefig(plots_dir / "ego_maneuver_position_velocity_acceleration.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, ego_maneuver["Local_X_m"], color="#2ca02c", linewidth=1.6)
    ax.set_xlabel("Time from target lane change (s)")
    ax.set_ylabel("Local X (m)")
    ax.axvline(0, color="black", linestyle="--", linewidth=1.0, alpha=0.7)
    ax.grid(True, alpha=0.25)

    lane_ax = ax.twinx()
    lane_ax.step(x, ego_maneuver["Lane_ID"], where="post", color="#ff7f0e", linewidth=1.1, alpha=0.75)
    lane_ax.set_ylabel("Lane ID")

    fig.suptitle("Ego Lateral Position and Lane ID")
    fig.tight_layout()
    fig.savefig(plots_dir / "ego_maneuver_lateral_position_lane.png", dpi=160)
    plt.close(fig)
