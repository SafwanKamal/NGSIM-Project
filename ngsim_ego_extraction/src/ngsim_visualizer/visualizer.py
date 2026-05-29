from __future__ import annotations

import colorsys
import math
import os
from pathlib import Path
import random
import sys
import pandas as pd
import pygame
import yaml

# Initialize Pygame font
pygame.font.init()
FONT_TITLE = pygame.font.SysFont("Outfit", 26, bold=True) or pygame.font.SysFont("Arial", 26, bold=True)
FONT_HUD = pygame.font.SysFont("Consolas", 15) or pygame.font.SysFont("Courier New", 15)
FONT_HELP = pygame.font.SysFont("Arial", 12)
FONT_LABEL = pygame.font.SysFont("Arial", 11, bold=True)

# Standard dimensions and HSL neon palettes
COLOR_BG = (22, 24, 28)          # Extremely deep modern dark
COLOR_ROAD = (35, 37, 44)        # Dark grey road
COLOR_LANE_LINE = (90, 95, 110)   # Clean subtle lane divider
COLOR_EGO = (255, 100, 0)        # Blazing neon orange
COLOR_EGO_GLOW = (255, 150, 0)
COLOR_TEXT = (240, 244, 250)     # Pure premium off-white
COLOR_HUD_BG = (15, 17, 20, 215) # Smooth glassmorphic backdrop
COLOR_ACCENT = (0, 210, 255)     # Cyberpunk cyan
COLOR_GLOW_BLUE = (0, 160, 255)  # Road border glow
COLOR_TAIL_LIGHT_DIM = (120, 0, 0)
COLOR_TAIL_LIGHT_BRIGHT = (255, 10, 10)

def get_vehicle_color(vehicle_id: int) -> tuple[int, int, int]:
    """Generates a stable, premium neon/pastel color for each vehicle ID."""
    state = random.getstate()
    random.seed(int(vehicle_id))
    h = random.randint(0, 360) / 360.0
    s = 0.85  # High saturation
    l = 0.58  # Bright neon
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    random.setstate(state)
    return int(r * 255), int(g * 255), int(b * 255)

class ScenarioVisualizer:
    def __init__(self, scenarios_dir: Path):
        self.scenarios_dir = scenarios_dir
        self.scenario_paths = self._discover_scenarios()
        self.scenario_index = 0
        
        # Screen dimensions
        self.screen_width = 1280
        self.screen_height = 720
        
        # State variables
        self.running = True
        self.paused = False
        self.frame_index = 0
        self.playback_speed = 1.0  # multiplier: 0.25x, 0.5x, 1x, 2x, 5x
        self.fps = 60
        self.ticks = 0.0  # Time tracker for pulsing HUD animation
        
        # Rendering view settings
        self.view_mode = "ego_centered" 
        self.show_full_surrounding = True 
        self.show_tails = True
        self.show_future_paths = True  # Toggleable predicted future path
        
        # Vehicle dimensions (meters)
        self.vehicle_length = 4.6
        self.vehicle_width = 1.95
        
        # Load first scenario
        self.metadata = {}
        self.ego_df = pd.DataFrame()
        self.surrounding_df = pd.DataFrame()
        self.frames = []
        self.lane_changes = pd.DataFrame()
        
        self.load_scenario(self.scenario_index)

    def _discover_scenarios(self) -> list[Path]:
        """Scans the scenarios directory and returns sorted scenario paths."""
        if not self.scenarios_dir.exists():
            print(f"Scenarios directory not found at: {self.scenarios_dir}")
            return []
        
        paths = sorted([p for p in self.scenarios_dir.glob("scenario_*") if p.is_dir()])
        return paths

    def load_scenario(self, index: int):
        """Loads all CSV/YAML files for the selected scenario."""
        if not self.scenario_paths:
            return
        
        self.scenario_index = index % len(self.scenario_paths)
        path = self.scenario_paths[self.scenario_index]
        print(f"Loading Scenario [{self.scenario_index + 1}/{len(self.scenario_paths)}]: {path.name}")
        
        # Load metadata
        meta_file = path / "metadata.yaml"
        if meta_file.exists():
            with meta_file.open("r", encoding="utf-8") as f:
                self.metadata = yaml.safe_load(f)
        else:
            self.metadata = {"vehicle_id": 0, "road_length_m": 500}
            
        # Load EGO trajectory
        ego_file = path / "ego_trajectory.csv"
        if ego_file.exists():
            self.ego_df = pd.read_csv(ego_file).sort_values("Frame_ID").reset_index(drop=True)
            self.frames = sorted(self.ego_df["Frame_ID"].unique().tolist())
        else:
            self.ego_df = pd.DataFrame()
            self.frames = []
            
        # Load surrounding vehicles
        surrounding_file = path / ("surrounding_vehicles_full.csv" if self.show_full_surrounding else "surrounding_vehicles.csv")
        if surrounding_file.exists():
            self.surrounding_df = pd.read_csv(surrounding_file)
        else:
            self.surrounding_df = pd.DataFrame()
            
        # Load lane changes
        lc_file = path / "lane_changes.csv"
        if lc_file.exists():
            self.lane_changes = pd.read_csv(lc_file)
        else:
            self.lane_changes = pd.DataFrame()
            
        # Reset playback state
        self.frame_index = 0
        
        # Pre-group databases by Frame_ID for high-speed retrieval
        self.ego_by_frame = {frame: df for frame, df in self.ego_df.groupby("Frame_ID")}
        self.surr_by_frame = {frame: df for frame, df in self.surrounding_df.groupby("Frame_ID")} if not self.surrounding_df.empty else {}
        
        # Pre-index databases by Vehicle_ID for high-speed dynamic spatial slices
        self.ego_by_vehicle = {vid: df.sort_values("Frame_ID").reset_index(drop=True) for vid, df in self.ego_df.groupby("Vehicle_ID")} if not self.ego_df.empty else {}
        self.surr_by_vehicle = {vid: df.sort_values("Frame_ID").reset_index(drop=True) for vid, df in self.surrounding_df.groupby("Vehicle_ID")} if not self.surrounding_df.empty else {}

    def toggle_surrounding_mode(self):
        """Switches between compact simulator-ready and full broad surrounding vehicle views."""
        self.show_full_surrounding = not self.show_full_surrounding
        self.load_scenario(self.scenario_index)

    def render_road(self, screen: pygame.Surface, min_y: float, max_y: float, ego_y: float):
        """Draws the highway corridor framed with neon glowing boundaries."""
        lane_width_m = 3.6576
        num_lanes = 8
        road_width_m = num_lanes * lane_width_m
        
        road_center_screen_y = self.screen_height // 2 + 40
        
        if self.view_mode == "ego_centered":
            scale_zoom = 9.5  # pixels per meter
            offset_x = 350.0 - ego_y * scale_zoom
            scale_x = scale_zoom
            scale_y = scale_zoom
        else:
            left_margin = 60
            right_margin = 60
            road_render_width = self.screen_width - (left_margin + right_margin)
            scale_x = road_render_width / (max_y - min_y)
            offset_x = left_margin - min_y * scale_x
            scale_y = 6.8  
            
        offset_y = road_center_screen_y - (road_width_m / 2) * scale_y
        
        screen_start_x = min_y * scale_x + offset_x
        screen_end_x = max_y * scale_x + offset_x
        
        # Asphalt base
        road_rect = pygame.Rect(
            screen_start_x,
            offset_y,
            screen_end_x - screen_start_x,
            road_width_m * scale_y
        )
        pygame.draw.rect(screen, COLOR_ROAD, road_rect)
        
        # Neon Border glows for the highway
        glow_width = 3
        pygame.draw.line(screen, COLOR_GLOW_BLUE, (screen_start_x, offset_y), (screen_end_x, offset_y), glow_width)
        pygame.draw.line(screen, COLOR_GLOW_BLUE, (screen_start_x, offset_y + road_width_m * scale_y), (screen_end_x, offset_y + road_width_m * scale_y), glow_width)
        
        # Lane markings
        for i in range(num_lanes + 1):
            lane_boundary_m = i * lane_width_m
            screen_y = offset_y + lane_boundary_m * scale_y
            
            if i == 0 or i == num_lanes:
                pygame.draw.line(screen, COLOR_TEXT, (screen_start_x, screen_y), (screen_end_x, screen_y), 2)
            else:
                # Dashed lanes
                dash_len = 12
                gap_len = 16
                x = screen_start_x
                while x < screen_end_x:
                    end_dash = min(x + dash_len, screen_end_x)
                    pygame.draw.line(screen, COLOR_LANE_LINE, (x, screen_y), (end_dash, screen_y), 1)
                    x += dash_len + gap_len
                    
            # Lane labels
            if i < num_lanes:
                lane_num_center_y = offset_y + (i + 0.5) * lane_width_m * scale_y
                lbl = FONT_HELP.render(f"L{i+1}", True, (110, 115, 130))
                screen.blit(lbl, (screen_start_x - 30, lane_num_center_y - lbl.get_height() // 2))
                screen.blit(lbl, (screen_end_x + 10, lane_num_center_y - lbl.get_height() // 2))
                
        return scale_x, scale_y, offset_x, offset_y

    def render_tails(self, screen: pygame.Surface, scale_x: float, scale_y: float, offset_x: float, offset_y: float, curr_frame: int):
        """Draws a clean, subtle solid neon past trail (-50m) exclusively for the Ego vehicle."""
        ego_id = int(self.metadata.get("vehicle_id", 0))
        ego_row = self.ego_by_frame.get(curr_frame)
        if ego_row is not None and not ego_row.empty:
            row = ego_row.iloc[0]
            current_y = float(row["Local_Y_m"])
            v_hist = self.ego_by_vehicle.get(ego_id)
            if v_hist is not None and not v_hist.empty:
                past_df = v_hist[(v_hist["Frame_ID"] <= curr_frame) & (v_hist["Local_Y_m"] >= current_y - 50.0)]
                if len(past_df) >= 2:
                    self._draw_past_trail_ribbon(screen, past_df, scale_x, scale_y, offset_x, offset_y, COLOR_EGO)

    def _draw_past_trail_ribbon(self, screen: pygame.Surface, past_df: pd.DataFrame, 
                                scale_x: float, scale_y: float, offset_x: float, offset_y: float, 
                                color: tuple[int, int, int]):
        """Draws the Ego past trail as a crisp, subtle solid line with a very soft neon glow."""
        pts = []
        for _, r in past_df.iterrows():
            sx = float(r["Local_Y_m"]) * scale_x + offset_x
            sy = offset_y + float(r["Local_X_m"]) * scale_y
            pts.append((sx, sy))
            
        for idx in range(len(pts) - 1):
            p1 = pts[idx]
            p2 = pts[idx + 1]
            pct = (idx + 1) / len(pts)
            
            # Subtle, crisp solid line: core width 3 pixels
            width = max(1, int(pct * 3.0))
            
            # Faint, understated neon backglow (width 5 pixels, very soft 20% opacity)
            glow_color = (
                int(COLOR_BG[0] + (COLOR_EGO_GLOW[0] - COLOR_BG[0]) * pct * 0.2),
                int(COLOR_BG[1] + (COLOR_EGO_GLOW[1] - COLOR_BG[1]) * pct * 0.2),
                int(COLOR_BG[2] + (COLOR_EGO_GLOW[2] - COLOR_BG[2]) * pct * 0.2)
            )
            pygame.draw.line(screen, glow_color, p1, p2, width + 2)
            
            # Solid core line
            fade_color = (
                int(COLOR_BG[0] + (COLOR_EGO[0] - COLOR_BG[0]) * pct),
                int(COLOR_BG[1] + (COLOR_EGO[1] - COLOR_BG[1]) * pct),
                int(COLOR_BG[2] + (COLOR_EGO[2] - COLOR_BG[2]) * pct)
            )
            pygame.draw.line(screen, fade_color, p1, p2, width)

    def render_future_paths(self, screen: pygame.Surface, scale_x: float, scale_y: float, offset_x: float, offset_y: float, curr_frame: int):
        """Draws a crisp, subtle solid neon prediction path (+50m) exclusively for the Ego vehicle."""
        ego_id = int(self.metadata.get("vehicle_id", 0))
        ego_row = self.ego_by_frame.get(curr_frame)
        if ego_row is not None and not ego_row.empty:
            row = ego_row.iloc[0]
            current_y = float(row["Local_Y_m"])
            ego_hist = self.ego_by_vehicle.get(ego_id)
            if ego_hist is not None and not ego_hist.empty:
                future_df = ego_hist[(ego_hist["Frame_ID"] > curr_frame) & (ego_hist["Local_Y_m"] <= current_y + 50.0)]
                if len(future_df) >= 2:
                    self._draw_future_path_ribbon(screen, future_df, scale_x, scale_y, offset_x, offset_y, COLOR_EGO)

    def _draw_future_path_ribbon(self, screen: pygame.Surface, future_df: pd.DataFrame, 
                                 scale_x: float, scale_y: float, offset_x: float, offset_y: float, 
                                 color: tuple[int, int, int]):
        """Draws the Ego predicted path as a crisp, solid line with a very subtle prediction fade."""
        pts = []
        for _, r in future_df.iterrows():
            sx = float(r["Local_Y_m"]) * scale_x + offset_x
            sy = offset_y + float(r["Local_X_m"]) * scale_y
            pts.append((sx, sy))
            
        # Crisp solid prediction vector: width 2 pixels
        line_width = 2
        
        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]
            pct = 1.0 - (i / len(pts))
            
            # Subtle Prediction color blending
            core_color = (
                int(COLOR_BG[0] + (COLOR_EGO[0] - COLOR_BG[0]) * pct * 0.8),
                int(COLOR_BG[1] + (COLOR_EGO[1] - COLOR_BG[1]) * pct * 0.8),
                int(COLOR_BG[2] + (COLOR_EGO[2] - COLOR_BG[2]) * pct * 0.8)
            )
            
            # Very faint glowing backing (width 4 pixels, very soft)
            glow_color = (
                int(COLOR_BG[0] + (COLOR_EGO_GLOW[0] - COLOR_BG[0]) * pct * 0.25),
                int(COLOR_BG[1] + (COLOR_EGO_GLOW[1] - COLOR_BG[1]) * pct * 0.25),
                int(COLOR_BG[2] + (COLOR_EGO_GLOW[2] - COLOR_BG[2]) * pct * 0.25)
            )
            pygame.draw.line(screen, glow_color, p1, p2, line_width + 2)
            pygame.draw.line(screen, core_color, p1, p2, line_width)

    def draw_vehicle(self, screen: pygame.Surface, vid: int, row: pd.Series, 
                     scale_x: float, scale_y: float, offset_x: float, offset_y: float, is_ego: bool = False):
        """Renders polished top-down vector cars with headlights, windshields, and shadows."""
        py_m = float(row["Local_Y_m"])
        px_m = float(row["Local_X_m"])
        acc = float(row["v_Acc_mps2"])
        
        screen_x = py_m * scale_x + offset_x
        screen_y = offset_y + px_m * scale_y
        
        pix_len = max(10, int(self.vehicle_length * scale_x))
        pix_wid = max(5, int(self.vehicle_width * scale_y))
        
        # 1. Projected 3D Shadow
        shadow_offset_x = 4
        shadow_offset_y = 4
        shadow_rect = pygame.Rect(
            screen_x - pix_len / 2 + shadow_offset_x,
            screen_y - pix_wid / 2 + shadow_offset_y,
            pix_len,
            pix_wid
        )
        shadow_surf = pygame.Surface((pix_len, pix_wid), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 95), (0, 0, pix_len, pix_wid), border_radius=4)
        screen.blit(shadow_surf, shadow_rect.topleft)
        
        # 2. Vehicle Body Rect
        veh_rect = pygame.Rect(
            screen_x - pix_len / 2,
            screen_y - pix_wid / 2,
            pix_len,
            pix_wid
        )
        
        main_color = COLOR_EGO if is_ego else get_vehicle_color(vid)
        
        # Draw dynamic headlight beams (pointing forward, which is rightward)
        if self.view_mode == "ego_centered":
            headlight_len = 16
            headlight_width = 8
            hl_surf = pygame.Surface((headlight_len, pix_wid + headlight_width * 2), pygame.SRCALPHA)
            
            poly_top = [(0, headlight_width), (headlight_len, 0), (headlight_len, headlight_width * 2), (0, headlight_width * 2)]
            poly_bot = [(0, pix_wid), (headlight_len, pix_wid - headlight_width), (headlight_len, pix_wid + headlight_width), (0, pix_wid + headlight_width)]
            
            pygame.draw.polygon(hl_surf, (255, 255, 200, 35), poly_top)
            pygame.draw.polygon(hl_surf, (255, 255, 200, 35), poly_bot)
            
            screen.blit(hl_surf, (veh_rect.right, veh_rect.y - headlight_width))
            
        pygame.draw.rect(screen, main_color, veh_rect, border_radius=3)
        pygame.draw.rect(screen, (240, 240, 250), veh_rect, 1, border_radius=3)  
        
        # 3. Top-Down Styling Details (Windshield, Rear window, mirrors)
        if self.view_mode == "ego_centered" and pix_len > 18:
            # Windshield (dark glass)
            windshield_width = max(3, int(pix_len * 0.18))
            windshield_rect = pygame.Rect(
                veh_rect.x + int(pix_len * 0.6),
                veh_rect.y + 2,
                windshield_width,
                pix_wid - 4
            )
            pygame.draw.rect(screen, (20, 24, 30), windshield_rect, border_radius=1)
            
            # Rear Window
            rear_window_width = max(2, int(pix_len * 0.12))
            rear_window_rect = pygame.Rect(
                veh_rect.x + int(pix_len * 0.2),
                veh_rect.y + 2,
                rear_window_width,
                pix_wid - 4
            )
            pygame.draw.rect(screen, (25, 28, 35), rear_window_rect, border_radius=1)
            
            # Side Mirrors
            mirror_len = 3
            mirror_wid = 2
            pygame.draw.rect(screen, main_color, (veh_rect.x + int(pix_len * 0.55), veh_rect.y - mirror_wid, mirror_len, mirror_wid))
            pygame.draw.rect(screen, main_color, (veh_rect.x + int(pix_len * 0.55), veh_rect.bottom, mirror_len, mirror_wid))
            
            # 4. Dynamic Taillights / Brake Lights
            pygame.draw.circle(screen, (255, 255, 180), (veh_rect.right, veh_rect.y + 2), 1)
            pygame.draw.circle(screen, (255, 255, 180), (veh_rect.right, veh_rect.bottom - 2), 1)
            
            is_braking = (acc < -0.5)
            light_color = COLOR_TAIL_LIGHT_BRIGHT if is_braking else COLOR_TAIL_LIGHT_DIM
            light_rad = 3 if is_braking else 1
            
            pygame.draw.circle(screen, light_color, (veh_rect.left, veh_rect.y + 2), light_rad)
            pygame.draw.circle(screen, light_color, (veh_rect.left, veh_rect.bottom - 2), light_rad)
            
            if is_braking:
                flare_surf = pygame.Surface((light_rad * 4, light_rad * 4), pygame.SRCALPHA)
                pygame.draw.circle(flare_surf, (*COLOR_TAIL_LIGHT_BRIGHT, 85), (light_rad*2, light_rad*2), light_rad*2)
                screen.blit(flare_surf, (veh_rect.left - light_rad*2, veh_rect.y + 2 - light_rad*2))
                screen.blit(flare_surf, (veh_rect.left - light_rad*2, veh_rect.bottom - 2 - light_rad*2))
                
        # Ego floating nameplate
        if is_ego:
            lbl = FONT_LABEL.render("EGO", True, COLOR_TEXT)
            screen.blit(lbl, (veh_rect.centerx - lbl.get_width() // 2, veh_rect.y - 14))
        else:
            if self.view_mode == "ego_centered":
                lbl_text = f"v{vid % 1000:03d}"
                lbl = FONT_LABEL.render(lbl_text, True, (160, 165, 180))
                screen.blit(lbl, (veh_rect.centerx - lbl.get_width() // 2, veh_rect.y - 12))

    def render_hud(self, screen: pygame.Surface, ego_row: pd.Series, elapsed_time: float, total_time: float):
        """Draws a premium translucent glassmorphic HUD dashboard overlay."""
        # Main glass backdrop
        hud_surface = pygame.Surface((self.screen_width - 80, 115), pygame.SRCALPHA)
        pygame.draw.rect(hud_surface, COLOR_HUD_BG, (0, 0, hud_surface.get_width(), hud_surface.get_height()), border_radius=8)
        pygame.draw.rect(hud_surface, (70, 75, 95, 255), (0, 0, hud_surface.get_width(), hud_surface.get_height()), 1, border_radius=8)
        
        screen.blit(hud_surface, (40, 20))
        
        # 1. Main Title Block & Segment Info
        scenario_num = f"{self.scenario_index + 1}/{len(self.scenario_paths)}"
        title_text = f"NGSIM US-101 Scenario {scenario_num}: Vehicle {self.metadata.get('vehicle_id')}"
        title_lbl = FONT_TITLE.render(title_text, True, COLOR_ACCENT)
        screen.blit(title_lbl, (60, 30))
        
        segment_label = self.metadata.get("time_segment", "7:50 AM - 8:05 AM")
        seg_lbl = FONT_HUD.render(f"Time segment: {segment_label}", True, COLOR_TEXT)
        screen.blit(seg_lbl, (60, 68))
        
        source_lbl = FONT_HUD.render(f"Source file: {self.metadata.get('source_file', '')}", True, (150, 155, 170))
        screen.blit(source_lbl, (60, 88))
        
        # 2. Ego Dynamics Dashboard
        ego_x_offset = 640
        speed_mps = float(ego_row["v_Vel_mps"])
        speed_mph = speed_mps * 2.23694
        acc_mps2 = float(ego_row["v_Acc_mps2"])
        pos_y_m = float(ego_row["Local_Y_m"])
        pos_x_m = float(ego_row["Local_X_m"])
        
        # Draw vertical divider lines inside HUD
        pygame.draw.line(screen, (60, 65, 80), (ego_x_offset - 25, 30), (ego_x_offset - 25, 115), 1)
        pygame.draw.line(screen, (60, 65, 80), (980, 30), (980, 115), 1)
        
        dynamics_text = [
            f"Ego Speed:  {speed_mps:5.1f} m/s ({speed_mph:4.1f} mph)",
            f"Ego Accel:  {acc_mps2:5.2f} m/s²",
            f"Position:   Y = {pos_y_m:5.1f} m | X = {pos_x_m:4.1f} m",
            f"Active Lane: Lane {int(ego_row['Lane_ID'])} (Locally Leader-Free)"
        ]
        
        for idx, line in enumerate(dynamics_text):
            lbl = FONT_HUD.render(line, True, COLOR_TEXT)
            screen.blit(lbl, (ego_x_offset, 35 + idx * 18))
            
        # 3. Status Block & Key Bindings Help
        hud_right_offset = 1005
        status_play = "PAUSED" if self.paused else "PLAYING"
        status_lbl = FONT_HUD.render(f"Status: {status_play} | Rate: {self.playback_speed}x", True, COLOR_ACCENT)
        screen.blit(status_lbl, (hud_right_offset, 35))
        
        # Draw pulsing indicators
        dot_x = hud_right_offset - 16
        dot_y = 43
        if self.paused:
            pygame.draw.circle(screen, (240, 60, 60), (dot_x, dot_y), 4)
        else:
            pulse_rad = 4 + int(math.sin(self.ticks * 8) * 2)
            pulse_rad = max(2, min(6, pulse_rad))
            pygame.draw.circle(screen, (0, 240, 100), (dot_x, dot_y), pulse_rad)
        
        time_lbl = FONT_HUD.render(f"Time:   {elapsed_time:4.1f} s / {total_time:4.1f} s", True, COLOR_TEXT)
        screen.blit(time_lbl, (hud_right_offset, 57))
        
        frame_lbl = FONT_HUD.render(f"Frame:  {int(ego_row['Frame_ID'])}", True, (160, 165, 180))
        screen.blit(frame_lbl, (hud_right_offset, 77))
        
        surr_mode = "Full Broad Pool" if self.show_full_surrounding else "Simulator Compact"
        pool_lbl = FONT_HUD.render(f"Context: {surr_mode}", True, COLOR_TEXT)
        screen.blit(pool_lbl, (hud_right_offset, 97))
        
        # Bottom screen control help bar
        help_surface = pygame.Surface((self.screen_width - 80, 45), pygame.SRCALPHA)
        pygame.draw.rect(help_surface, (18, 20, 24, 195), (0, 0, help_surface.get_width(), help_surface.get_height()), border_radius=6)
        screen.blit(help_surface, (40, self.screen_height - 65))
        
        tails_status = "ON (-50m)" if self.show_tails else "OFF"
        future_status = "ON (+50m)" if self.show_future_paths else "OFF"
        help_text = (
            f"KEYS: [Space] Play/Pause | [<- / ->] Seek 1s | [Up / Down] Playback Rate | [V] Camera View | "
            f"[F] Context Pool | [T] Ego Trail: {tails_status} | [P] Ego Future Path: {future_status}"
        )
        help_lbl = FONT_HELP.render(help_text, True, (170, 175, 190))
        screen.blit(help_lbl, (self.screen_width // 2 - help_lbl.get_width() // 2, self.screen_height - 52))

    def handle_keyboard_events(self):
        """Processes keystroke callbacks to update simulation state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self.running = False
                    
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                    
                elif event.key == pygame.K_r:
                    self.frame_index = 0
                    
                elif event.key == pygame.K_v:
                    self.view_mode = "full_road" if self.view_mode == "ego_centered" else "ego_centered"
                    
                elif event.key == pygame.K_f:
                    self.toggle_surrounding_mode()
                    
                elif event.key == pygame.K_t:
                    self.show_tails = not self.show_tails
                        
                elif event.key == pygame.K_p:
                    self.show_future_paths = not self.show_future_paths
                        
                elif event.key in (pygame.K_PAGEUP, pygame.K_RIGHTBRACKET):
                    self.load_scenario(self.scenario_index + 1)
                    
                elif event.key in (pygame.K_PAGEDOWN, pygame.K_LEFTBRACKET):
                    self.load_scenario(self.scenario_index - 1)
                    
                elif event.key == pygame.K_RIGHT:
                    self.frame_index = min(self.frame_index + 10, len(self.frames) - 1)
                    
                elif event.key == pygame.K_LEFT:
                    self.frame_index = max(self.frame_index - 10, 0)
                    
                elif event.key == pygame.K_UP:
                    rates = [0.25, 0.5, 1.0, 2.0, 5.0]
                    curr_idx = rates.index(self.playback_speed)
                    if curr_idx < len(rates) - 1:
                        self.playback_speed = rates[curr_idx + 1]
                        
                elif event.key == pygame.K_DOWN:
                    rates = [0.25, 0.5, 1.0, 2.0, 5.0]
                    curr_idx = rates.index(self.playback_speed)
                    if curr_idx > 0:
                        self.playback_speed = rates[curr_idx - 1]
                        
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(self.scenario_paths):
                        self.load_scenario(idx)

    def run(self):
        """Starts the visualizer application event loop."""
        pygame.init()
        screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("NGSIM US-101 Ego Scenario Vector Visualizer")
        clock = pygame.time.Clock()
        
        frame_time_acc = 0.0
        
        while self.running:
            dt = clock.tick(self.fps) / 1000.0  
            self.ticks += dt
            
            self.handle_keyboard_events()
            
            if not self.running:
                break
                
            screen.fill(COLOR_BG)
            
            if not self.frames:
                lbl = FONT_TITLE.render("No Scenario Data Discovered under outputs/scenarios/", True, COLOR_TEXT)
                screen.blit(lbl, (self.screen_width // 2 - lbl.get_width() // 2, self.screen_height // 2))
                pygame.display.flip()
                continue
                
            # Time-based frame advancement
            if not self.paused:
                frame_time_acc += dt * self.playback_speed
                if frame_time_acc >= 0.1:
                    frames_to_advance = int(frame_time_acc // 0.1)
                    self.frame_index += frames_to_advance
                    frame_time_acc = frame_time_acc % 0.1
                    
                    if self.frame_index >= len(self.frames):
                        self.frame_index = 0
                        
            curr_frame = self.frames[self.frame_index]
            ego_row = self.ego_by_frame.get(curr_frame)
            
            if ego_row is None or ego_row.empty:
                self.frame_index = 0
                continue
                
            row_ego = ego_row.iloc[0]
            ego_y_pos = float(row_ego["Local_Y_m"])
            
            min_y = float(self.ego_df["Local_Y_m"].min())
            max_y = float(self.ego_df["Local_Y_m"].max())
            
            # Render Road Base
            scale_x, scale_y, offset_x, offset_y = self.render_road(screen, min_y, max_y, ego_y_pos)
            
            # Render Ego Past Trail dynamically sliced to -50m
            if self.show_tails:
                self.render_tails(screen, scale_x, scale_y, offset_x, offset_y, curr_frame)
                
            # Render Ego Future Predicted Path dynamically sliced to +50m
            if self.show_future_paths:
                self.render_future_paths(screen, scale_x, scale_y, offset_x, offset_y, curr_frame)
                
            # Render surrounding vehicles
            curr_surr = self.surr_by_frame.get(curr_frame)
            if curr_surr is not None and not curr_surr.empty:
                for _, row in curr_surr.iterrows():
                    vid = int(row["Vehicle_ID"])
                    self.draw_vehicle(screen, vid, row, scale_x, scale_y, offset_x, offset_y, is_ego=False)
                    
            # Render Ego vehicle
            ego_vid = int(row_ego["Vehicle_ID"])
            self.draw_vehicle(screen, ego_vid, row_ego, scale_x, scale_y, offset_x, offset_y, is_ego=True)
            
            # Render HUD Overlay
            elapsed_time = float(row_ego["scenario_time_s"])
            total_time = float(self.ego_df["scenario_time_s"].max())
            self.render_hud(screen, row_ego, elapsed_time, total_time)
            
            pygame.display.flip()
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    scenarios_dir = project_root / "outputs" / "scenarios"
    visualizer = ScenarioVisualizer(scenarios_dir)
    visualizer.run()
