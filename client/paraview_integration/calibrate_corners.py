#!/usr/bin/env python3
"""
Falconia AprilTag Corner Calibration
Place AprilTags 0-3 on the corners of your Falconia model and run this script.
"""

import cv2
import json
import numpy as np
from pupil_apriltags import Detector

def calibrate_falconia_corners(camera_url="http://192.168.0.11:7123/stream.mjpg"):
    """Calibrate the 4 corners of Falconia using AprilTags 0-3"""
    
    print("🎯 Falconia Corner Calibration")
    print("=" * 40)
    print("📍 Place AprilTags on corners:")
    print("  Tag 0: Back-Left corner")
    print("  Tag 1: Back-Right corner") 
    print("  Tag 2: Front-Right corner")
    print("  Tag 3: Front-Left corner")
    print(f"📹 Camera: {camera_url}")
    print("🔍 Press SPACE to capture, ESC to quit")
    print()

    # Initialize detector
    detector = Detector(families='tag36h11')
    
    # Open camera
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"❌ Failed to open camera: {camera_url}")
        return None
    
    corners = {}
    target_tags = [0, 1, 2, 3]
    
    while len(corners) < 4:
        ret, frame = cap.read()
        if not ret:
            continue
            
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect AprilTags
        detections = detector.detect(gray)
        
        # Draw detections and check for target tags
        display_frame = frame.copy()
        found_tags = []
        
        for detection in detections:
            tag_id = detection.tag_id
            center = detection.center
            
            # Draw tag
            cv2.circle(display_frame, (int(center[0]), int(center[1])), 5, (0, 255, 0), -1)
            cv2.putText(display_frame, f"Tag {tag_id}", 
                       (int(center[0]) + 10, int(center[1])), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Check if this is a corner tag
            if tag_id in target_tags:
                found_tags.append(tag_id)
                if tag_id not in corners:
                    cv2.circle(display_frame, (int(center[0]), int(center[1])), 10, (0, 0, 255), 3)
        
        # Show status
        status_text = f"Found corners: {list(corners.keys())} | Current frame: {found_tags}"
        cv2.putText(display_frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow('Falconia Corner Calibration', display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
        elif key == 32:  # SPACE
            # Capture current detections
            for detection in detections:
                tag_id = detection.tag_id
                if tag_id in target_tags and tag_id not in corners:
                    corners[tag_id] = {
                        "pixel": [float(detection.center[0]), float(detection.center[1])],
                        "tag_id": int(tag_id)
                    }
                    print(f"✅ Captured Tag {tag_id}: {corners[tag_id]['pixel']}")
    
    cap.release()
    cv2.destroyAllWindows()
    
    if len(corners) == 4:
        # Save corners to file
        corner_data = {
            "timestamp": cv2.getTickCount() / cv2.getTickFrequency(),
            "camera_url": camera_url,
            "corners": {
                "back_left": corners[0],      # Tag 0
                "back_right": corners[1],     # Tag 1  
                "front_right": corners[2],    # Tag 2
                "front_left": corners[3]      # Tag 3
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