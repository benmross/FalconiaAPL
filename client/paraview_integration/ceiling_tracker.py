#!/usr/bin/env python3
"""
Ceiling-mounted AprilTag Tracker for Rover Position Detection

This service runs on a ceiling-mounted Raspberry Pi and detects AprilTags
on the rover to provide real-time position updates via MQTT.
"""

import cv2
import numpy as np
import json
import time
import threading
import argparse
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.apriltag_detector import AprilTagDetector

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Warning: paho-mqtt not installed. Install with: pip install paho-mqtt")
    mqtt = None

class CeilingTracker:
    def __init__(self, config_file="config/ceiling_camera_config.json"):
        """Initialize the ceiling tracker with configuration"""
        self.config = self.load_config(config_file)
        self.detector = AprilTagDetector()
        self.mqtt_client = None
        self.running = False
        self.capture = None
        self.position_history = []
        self.last_detection_time = 0
        
        # Position smoothing parameters
        self.position_filter_alpha = self.config.get('position_filter_alpha', 0.3)
        self.smoothed_position = None
        
        self.setup_mqtt()
        self.setup_camera()
        
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        default_config = {
            "camera_url": "http://192.168.1.100:7123/stream.mjpg",
            "camera_index": 0,
            "use_camera_index": False,
            "mqtt_broker": "localhost",
            "mqtt_port": 1883,
            "mqtt_topic": "rover/position",
            "target_tag_id": None,
            "ceiling_height": 2.5,
            "camera_params": {
                "fx": 640.0,
                "fy": 640.0,
                "cx": 320.0,
                "cy": 240.0
            },
            "tag_size": 0.15,
            "detection_rate": 30,
            "position_filter_alpha": 0.3,
            "coordinate_transform": {
                "enabled": False,
                "scale_x": 1.0,
                "scale_y": 1.0,
                "offset_x": 0.0,
                "offset_y": 0.0,
                "rotation": 0.0
            }
        }
        
        try:
            with open(config_file, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)
        except FileNotFoundError:
            print(f"Config file {config_file} not found, using defaults")
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        except json.JSONDecodeError as e:
            print(f"Error parsing config file: {e}")
            
        return default_config
        
    def setup_mqtt(self):
        """Initialize MQTT client"""
        if mqtt is None:
            print("MQTT not available, position data will only be printed to console")
            return
            
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(
                self.config["mqtt_broker"], 
                self.config["mqtt_port"], 
                60
            )
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            self.mqtt_client = None
            
    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            print(f"Connected to MQTT broker at {self.config['mqtt_broker']}")
        else:
            print(f"Failed to connect to MQTT broker, code {rc}")
            
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        print("Disconnected from MQTT broker")
        
    def setup_camera(self):
        """Initialize camera capture"""
        cam_params = self.config["camera_params"]
        self.detector.set_camera_params(
            fx=cam_params["fx"],
            fy=cam_params["fy"], 
            cx=cam_params["cx"],
            cy=cam_params["cy"],
            tag_size=self.config["tag_size"]
        )
        
        if self.config["use_camera_index"]:
            self.capture = cv2.VideoCapture(self.config["camera_index"])
        else:
            self.capture = cv2.VideoCapture(self.config["camera_url"])
            
        if not self.capture.isOpened():
            raise RuntimeError("Failed to open camera")
            
        print("Camera initialized successfully")
        
    def apply_coordinate_transform(self, x, y):
        """Apply coordinate transformation to convert camera coordinates to world coordinates"""
        transform = self.config["coordinate_transform"]
        
        if not transform["enabled"]:
            return x, y
            
        # Apply rotation
        angle = np.radians(transform["rotation"])
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        
        x_rot = x * cos_a - y * sin_a
        y_rot = x * sin_a + y * cos_a
        
        # Apply scaling and offset
        x_world = x_rot * transform["scale_x"] + transform["offset_x"]
        y_world = y_rot * transform["scale_y"] + transform["offset_y"]
        
        return x_world, y_world
        
    def smooth_position(self, new_position):
        """Apply smoothing filter to position data"""
        if self.smoothed_position is None:
            self.smoothed_position = new_position
        else:
            alpha = self.position_filter_alpha
            self.smoothed_position = (
                alpha * new_position[0] + (1 - alpha) * self.smoothed_position[0],
                alpha * new_position[1] + (1 - alpha) * self.smoothed_position[1],
                alpha * new_position[2] + (1 - alpha) * self.smoothed_position[2]
            )
        return self.smoothed_position
        
    def process_detections(self, tags):
        """Process detected AprilTags and extract position"""
        target_tag_id = self.config.get("target_tag_id")
        
        # Filter for target tag if specified
        if target_tag_id is not None:
            tags = [tag for tag in tags if tag.tag_id == target_tag_id]
            
        if not tags:
            return None
            
        # Use the first (or only) tag
        tag = tags[0]
        
        if not (hasattr(tag, 'pose_t') and hasattr(tag, 'pose_R')):
            return None
            
        # Extract 3D position from tag pose
        translation = tag.pose_t.flatten()
        
        # Convert camera coordinates to world coordinates
        x_cam, y_cam = translation[0], translation[1]
        x_world, y_world = self.apply_coordinate_transform(x_cam, y_cam)
        z_world = self.config["ceiling_height"] - translation[2]
        
        # Apply position smoothing
        raw_position = (x_world, y_world, z_world)
        smoothed_position = self.smooth_position(raw_position)
        
        # Create position data structure
        position_data = {
            "timestamp": datetime.now().isoformat(),
            "tag_id": tag.tag_id,
            "position": {
                "x": smoothed_position[0],
                "y": smoothed_position[1], 
                "z": smoothed_position[2]
            },
            "raw_position": {
                "x": raw_position[0],
                "y": raw_position[1],
                "z": raw_position[2]
            },
            "distance": np.linalg.norm(translation),
            "confidence": 1.0  # Could be enhanced with detection confidence
        }
        
        return position_data
        
    def publish_position(self, position_data):
        """Publish position data via MQTT"""
        if self.mqtt_client and self.mqtt_client.is_connected():
            try:
                message = json.dumps(position_data)
                self.mqtt_client.publish(self.config["mqtt_topic"], message)
            except Exception as e:
                print(f"Error publishing to MQTT: {e}")
        
        # Always print to console for debugging
        pos = position_data["position"]
        print(f"Rover position: x={pos['x']:.3f}, y={pos['y']:.3f}, z={pos['z']:.3f}")
        
    def run(self):
        """Main tracking loop"""
        self.running = True
        frame_interval = 1.0 / self.config["detection_rate"]
        
        print("Starting ceiling tracker...")
        print(f"Detection rate: {self.config['detection_rate']} Hz")
        print(f"Target tag ID: {self.config.get('target_tag_id', 'Any')}")
        print("Press Ctrl+C to stop")
        
        try:
            while self.running:
                start_time = time.time()
                
                ret, frame = self.capture.read()
                if not ret:
                    print("Failed to capture frame")
                    time.sleep(0.1)
                    continue
                    
                # Detect AprilTags
                tags = self.detector.detect(frame)
                
                if tags:
                    position_data = self.process_detections(tags)
                    if position_data:
                        self.publish_position(position_data)
                        self.last_detection_time = time.time()
                        
                        # Store in history (keep last 100 positions)
                        self.position_history.append(position_data)
                        if len(self.position_history) > 100:
                            self.position_history.pop(0)
                else:
                    # Check if we haven't seen the tag for a while
                    if time.time() - self.last_detection_time > 2.0:
                        print("No AprilTag detected")
                        self.last_detection_time = time.time()
                
                # Maintain frame rate
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\nShutting down ceiling tracker...")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        if self.capture:
            self.capture.release()
            
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
        print("Cleanup complete")

def main():
    parser = argparse.ArgumentParser(description="Ceiling-mounted AprilTag tracker")
    parser.add_argument("--config", default="config/ceiling_camera_config.json",
                        help="Configuration file path")
    parser.add_argument("--tag-id", type=int, default=None,
                        help="Target AprilTag ID (overrides config)")
    parser.add_argument("--mqtt-broker", default=None,
                        help="MQTT broker address (overrides config)")
    
    args = parser.parse_args()
    
    try:
        tracker = CeilingTracker(args.config)
        
        # Override config with command line arguments
        if args.tag_id is not None:
            tracker.config["target_tag_id"] = args.tag_id
        if args.mqtt_broker is not None:
            tracker.config["mqtt_broker"] = args.mqtt_broker
            tracker.setup_mqtt()
            
        tracker.run()
        
    except Exception as e:
        print(f"Error starting tracker: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())