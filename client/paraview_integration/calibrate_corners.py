#!/usr/bin/env python3
"""
Falconia Manual Corner Calibration
Click on the 4 corners of your Falconia model in the camera stream.
"""

import cv2
import json
import numpy as np

# Global variables for mouse callback
corners = {}
current_corner = 0
corner_names = ["top_left", "top_right", "bottom_right", "bottom_left"]
corner_labels = ["Top-Left", "Top-Right", "Bottom-Right", "Bottom-Left"]
frame_for_click = None

def mouse_callback(event, x, y, flags, param):
    """Handle mouse clicks to capture corner positions"""
    global corners, current_corner, frame_for_click
    
    if event == cv2.EVENT_LBUTTONDOWN and current_corner < 4:
        corner_name = corner_names[current_corner]
        corners[corner_name] = {"pixel": [float(x), float(y)]}
        
        print(f"✅ {corner_labels[current_corner]}: ({x}, {y})")
        
        # Draw the clicked point on the frame
        cv2.circle(frame_for_click, (x, y), 8, (0, 255, 0), -1)
        cv2.putText(frame_for_click, f"{current_corner + 1}", (x + 15, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        current_corner += 1

def calibrate_falconia_corners(camera_url="http://192.168.0.11:7123/stream.mjpg"):
    """Calibrate the 4 corners of Falconia by clicking on camera stream"""
    global corners, current_corner, frame_for_click
    
    print("🎯 Falconia Manual Corner Calibration")
    print("=" * 50)
    print("📍 Click on these corners in order:")
    print("  1. Top-Left corner (where tag 0 would be)")
    print("  2. Top-Right corner (where tag 1 would be)")
    print("  3. Bottom-Right corner (where tag 2 would be)")
    print("  4. Bottom-Left corner (where tag 3 would be)")
    print()
    print(f"📹 Camera: {camera_url}")
    print("🖱️  Left-click to mark corners")
    print("⌨️  Press ESC to quit, SPACE to restart")
    print()

    # Open camera
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"❌ Failed to open camera: {camera_url}")
        return None
    
    # Setup window and mouse callback
    window_name = 'Falconia Corner Calibration - Click Corners'
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)
    
    # Reset state
    corners = {}
    current_corner = 0
    
    while current_corner < 4:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to capture frame")
            continue
            
        frame_for_click = frame.copy()
        
        # Draw instructions and progress
        instruction = f"Click on: {corner_labels[current_corner]} ({current_corner + 1}/4)"
        cv2.putText(frame_for_click, instruction, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Draw already captured corners
        for i, (name, data) in enumerate(corners.items()):
            x, y = int(data["pixel"][0]), int(data["pixel"][1])
            cv2.circle(frame_for_click, (x, y), 8, (0, 255, 0), -1)
            cv2.putText(frame_for_click, f"{i + 1}", (x + 15, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Show corner order guide
        guide_y = 60
        for i, label in enumerate(corner_labels):
            color = (0, 255, 0) if i < current_corner else (255, 255, 255)
            status = "✓" if i < current_corner else f"{i + 1}."
            cv2.putText(frame_for_click, f"{status} {label}", (10, guide_y + i * 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        cv2.imshow(window_name, frame_for_click)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            print("❌ Calibration cancelled")
            cap.release()
            cv2.destroyAllWindows()
            return None
        elif key == 32:  # SPACE - restart
            print("🔄 Restarting calibration...")
            corners = {}
            current_corner = 0
    
    cap.release()
    cv2.destroyAllWindows()
    
    if len(corners) == 4:
        # Save corners to file
        corner_data = {
            "timestamp": cv2.getTickCount() / cv2.getTickFrequency(),
            "camera_url": camera_url,
            "corners": {
                "back_left": corners["top_left"],      # Tag 0
                "back_right": corners["top_right"],     # Tag 1  
                "front_right": corners["bottom_right"],    # Tag 2
                "front_left": corners["bottom_left"]      # Tag 3
            }
        }
        
        # Save to multiple locations for easier access
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_paths = [
            'falconia_corners.json',  # Current directory
            os.path.join(script_dir, 'falconia_corners.json'),  # Script directory
            os.path.expanduser('~/falconia_corners.json')  # Home directory
        ]
        
        for path in save_paths:
            try:
                with open(path, 'w') as f:
                    json.dump(corner_data, f, indent=2)
                print(f"📁 Saved to: {path}")
            except:
                pass
        
        print()
        print("✅ Calibration Complete!")
        print("🎯 Corner positions:")
        for name, data in corner_data["corners"].items():
            print(f"  {name}: {data['pixel']}")
        
        return corner_data
    else:
        print(f"❌ Only found {len(corners)}/4 corners")
        return None

if __name__ == "__main__":
    import sys
    
    camera_url = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.0.11:7123/stream.mjpg"
    calibrate_falconia_corners(camera_url)