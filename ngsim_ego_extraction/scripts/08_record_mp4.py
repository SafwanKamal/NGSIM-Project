import os
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import imageio

# Set SDL to dummy mode before pygame is initialized
os.environ["SDL_VIDEODRIVER"] = "dummy"

# Add src to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

import pygame
from ngsim_visualizer.visualizer import ScenarioVisualizer

def record_mp4():
    scenarios_dir = project_root / "outputs" / "scenarios"
    visualizer = ScenarioVisualizer(scenarios_dir)
    
    # Ensure a scenario is loaded
    if not visualizer.frames:
        print("No scenarios found to record.")
        return
        
    # We will record scenario 23 (vehicle 2001164)
    target_idx = 0
    for idx, path in enumerate(visualizer.scenario_paths):
        if "2001164" in path.name:
            target_idx = idx
            break
    visualizer.load_scenario(target_idx)
    
    # Initialize Pygame and screen
    pygame.init()
    screen = pygame.display.set_mode((visualizer.screen_width, visualizer.screen_height))
    
    temp_dir = Path("temp_frames_mp4")
    temp_dir.mkdir(exist_ok=True)
    
    # Record 150 frames (15 seconds at 10 FPS) for a comprehensive, professional clip
    num_frames_to_record = min(150, len(visualizer.frames))
    frame_files = []
    
    print(f"Recording {num_frames_to_record} frames of scenario {visualizer.scenario_paths[visualizer.scenario_index].name} in headless mode...")
    
    for f_idx in range(num_frames_to_record):
        visualizer.frame_index = f_idx
        curr_frame = visualizer.frames[f_idx]
        
        # Render the state
        screen.fill((22, 24, 28))  # COLOR_BG
        
        ego_row = visualizer.ego_by_frame.get(curr_frame)
        if ego_row is None or ego_row.empty:
            continue
            
        row_ego = ego_row.iloc[0]
        ego_y_pos = float(row_ego["Local_Y_m"])
        min_y = float(visualizer.ego_df["Local_Y_m"].min())
        max_y = float(visualizer.ego_df["Local_Y_m"].max())
        
        # Render components
        scale_x, scale_y, offset_x, offset_y = visualizer.render_road(screen, min_y, max_y, ego_y_pos)
        
        if visualizer.show_tails:
            visualizer.render_tails(screen, scale_x, scale_y, offset_x, offset_y, curr_frame)
            
        if visualizer.show_future_paths:
            visualizer.render_future_paths(screen, scale_x, scale_y, offset_x, offset_y, curr_frame)
            
        curr_surr = visualizer.surr_by_frame.get(curr_frame)
        if curr_surr is not None and not curr_surr.empty:
            for _, row in curr_surr.iterrows():
                vid = int(row["Vehicle_ID"])
                visualizer.draw_vehicle(screen, vid, row, scale_x, scale_y, offset_x, offset_y, is_ego=False)
                
        ego_vid = int(row_ego["Vehicle_ID"])
        visualizer.draw_vehicle(screen, ego_vid, row_ego, scale_x, scale_y, offset_x, offset_y, is_ego=True)
        
        elapsed_time = float(row_ego["scenario_time_s"])
        total_time = float(visualizer.ego_df["scenario_time_s"].max())
        visualizer.render_hud(screen, row_ego, elapsed_time, total_time)
        
        # Save frame to disk
        frame_path = temp_dir / f"frame_{f_idx:03d}.png"
        pygame.image.save(screen, str(frame_path))
        frame_files.append(frame_path)
        
        # Increment visualizer ticks for pulse animation
        visualizer.ticks += 0.1
        
    pygame.quit()
    
    # Compile frames to MP4 using imageio FFMPEG writer
    print("Compiling frames into high-fidelity MP4 video (H.264)...")
    output_mp4_path = project_root / "simulation_recording.mp4"
    
    # 854x480 (480p) widescreen aspect ratio
    writer = imageio.get_writer(
        str(output_mp4_path),
        fps=10,
        format="FFMPEG",
        mode="I",
        codec="libx264",
        pixelformat="yuv420p"  # Ensures high compatibility with all video players
    )
    
    for f in frame_files:
        img = Image.open(f)
        resized_img = img.resize((854, 480), Image.Resampling.LANCZOS)
        # Convert PIL Image to a numpy array expected by imageio
        img_array = np.array(resized_img)
        writer.append_data(img_array)
        
    writer.close()
    print(f"MP4 Video saved successfully to: {output_mp4_path}")
    
    # Clean up temp frames
    for f in frame_files:
        f.unlink()
    temp_dir.rmdir()
    print("Temporary frames cleaned up.")

if __name__ == "__main__":
    record_mp4()
