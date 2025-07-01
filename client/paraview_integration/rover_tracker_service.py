#!/usr/bin/env python3
"""
Falconia Rover Tracking Background Service
Continuously detects AprilTag 4, transforms coordinates, and publishes to MQTT.
"""

import cv2
import json
import numpy as np
import time
import threading
import argparse
from pupil_apriltags import Detector
import paho.mqtt.client as mqtt

class RoverTrackerService:
    def __init__(self, config_file="falconia_corners.json", camera_url=None, mqtt_broker="localhost", mqtt_port=1883):
        self.config_file = config_file
        self.camera_url = camera_url
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        
        # State variables
        self.corners_data = None
        self.pixel_corners = None
        self.model_coords = None
        self.detector = None
        self.camera_capture = None
        self.mqtt_client = None
        self.running = False
        self.last_position = None
        self.stats = {
            "detections": 0,
            "missed": 0,
            "published": 0,
            "start_time": time.time()
        }
        
    def load_corner_calibration(self):
        """Load corner calibration data"""
        try:
            with open(self.config_file, 'r') as f:
                self.corners_data = json.load(f)
            print(f"✅ Loaded corner calibration from: {self.config_file}")
            
            # Setup coordinate transformation
            self.setup_coordinate_transform()
            return True
            
        except FileNotFoundError:
            print(f"❌ Corner calibration not found: {self.config_file}")
            print("   Run: python calibrate_corners.py")
            return False
        except Exception as e:
            print(f"❌ Error loading calibration: {e}")
            return False
    
    def setup_coordinate_transform(self):
        """Setup homography transformation from pixel to model coordinates"""
        if not self.corners_data:
            return False
            
        camera_corners = self.corners_data["corners"]
        
        # Support both old AprilTag format and new click format
        if "top_left" in camera_corners:
            # New click-based format
            pixel_points = [
                camera_corners["top_left"]["pixel"],
                camera_corners["top_right"]["pixel"],
                camera_corners["bottom_right"]["pixel"],
                camera_corners["bottom_left"]["pixel"]
            ]
            print("📌 Using click-based corner format")
        else:
            # Old AprilTag format
            pixel_points = [
                camera_corners["back_left"]["pixel"],
                camera_corners["back_right"]["pixel"], 
                camera_corners["front_right"]["pixel"],
                camera_corners["front_left"]["pixel"]
            ]
            print("📌 Using AprilTag corner format")
        
        # Use manually calibrated model coordinates (since we don't have ParaView access)
        # These should match your ParaView model bounds
        model_points = [
            [-1.25, -1.8],  # top_left [x, z]
            [1.25, -1.8],   # top_right [x, z]
            [1.25, 1.8],    # bottom_right [x, z]  
            [-1.25, 1.8]    # bottom_left [x, z]
        ]
        
        try:
            self.pixel_corners = np.array(pixel_points, dtype=np.float32)
            self.model_coords = np.array(model_points, dtype=np.float32)
            print("✅ Coordinate transformation ready")
            return True
        except Exception as e:
            print(f"❌ Failed to setup transformation: {e}")
            return False
    
    def pixel_to_model_coords(self, pixel_x, pixel_y):
        """Transform pixel coordinates to model coordinates"""
        try:
            # Calculate homography matrix
            homography_matrix = cv2.getPerspectiveTransform(self.pixel_corners, self.model_coords)
            
            # Transform the pixel point
            pixel_point = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)
            model_point = cv2.perspectiveTransform(pixel_point, homography_matrix)
            
            # Extract coordinates
            model_x = float(model_point[0][0][0])
            model_z = float(model_point[0][0][1])
            model_y = 0.2  # Fixed hover height
            
            return [model_x, model_y, model_z]
            
        except Exception as e:
            print(f"❌ Transformation error: {e}")
            return None
    
    def setup_camera(self):
        """Setup camera capture"""
        if not self.camera_url:
            self.camera_url = self.corners_data.get("camera_url", "http://192.168.0.11:7123/stream.mjpg")
        
        print(f"📹 Setting up camera: {self.camera_url}")
        self.camera_capture = cv2.VideoCapture(self.camera_url)
        
        if not self.camera_capture.isOpened():
            print(f"❌ Failed to open camera: {self.camera_url}")
            return False
            
        # Initialize AprilTag detector
        self.detector = Detector(families='tag36h11')
        print("✅ Camera and detector ready")
        return True
    
    def setup_mqtt(self):
        """Setup MQTT client"""
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            print(f"✅ MQTT client connected to {self.mqtt_broker}:{self.mqtt_port}")
            return True
        except Exception as e:
            print(f"❌ MQTT setup failed: {e}")
            return False
    
    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            print("📡 MQTT broker connected successfully")
        else:
            print(f"❌ MQTT connection failed: {rc}")
    
    def detect_rover_position(self):
        """Detect rover AprilTag and return model coordinates"""
        try:
            # Capture frame
            ret, frame = self.camera_capture.read()
            if not ret:
                return None
            
            # Detect AprilTags
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detections = self.detector.detect(gray)
            
            # Look for rover tag (ID 4)
            for detection in detections:
                if detection.tag_id == 4:
                    pixel_pos = detection.center
                    model_pos = self.pixel_to_model_coords(pixel_pos[0], pixel_pos[1])
                    
                    if model_pos:
                        self.stats["detections"] += 1
                        return model_pos
            
            self.stats["missed"] += 1
            return None
            
        except Exception as e:
            print(f"❌ Detection error: {e}")
            return None
    
    def publish_position(self, position):
        """Publish rover position to MQTT"""
        try:
            position_data = {
                "timestamp": time.time(),
                "rover_id": 4,
                "position": {
                    "x": position[0],
                    "y": position[1], 
                    "z": position[2]
                },
                "source": "rover_tracker_service"
            }
            
            message = json.dumps(position_data)
            self.mqtt_client.publish("rover/position", message)
            self.stats["published"] += 1
            
        except Exception as e:
            print(f"❌ MQTT publish error: {e}")
    
    def tracking_loop(self):
        """Main tracking loop"""
        print("🚀 Starting rover tracking loop...")
        
        while self.running:
            try:
                position = self.detect_rover_position()
                
                if position:
                    # Only publish if position changed significantly
                    if (self.last_position is None or 
                        abs(position[0] - self.last_position[0]) > 0.01 or
                        abs(position[2] - self.last_position[2]) > 0.01):
                        
                        self.publish_position(position)
                        self.last_position = position
                        print(f"📍 Rover: [{position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f}]")
                
                # Control update rate
                time.sleep(0.05)  # 20 Hz
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Tracking loop error: {e}")
                time.sleep(1)
    
    def print_stats(self):
        """Print tracking statistics"""
        runtime = time.time() - self.stats["start_time"]
        print(f"\n📊 Tracking Statistics ({runtime:.1f}s):")
        print(f"   Detections: {self.stats['detections']}")
        print(f"   Missed: {self.stats['missed']}")
        print(f"   Published: {self.stats['published']}")
        if runtime > 0:
            print(f"   Detection rate: {self.stats['detections']/runtime:.1f} Hz")
    
    def start(self):
        """Start the tracking service"""
        print("🎯 Falconia Rover Tracking Service")
        print("=" * 40)
        
        # Initialize components
        if not self.load_corner_calibration():
            return False
        
        if not self.setup_camera():
            return False
            
        if not self.setup_mqtt():
            return False
        
        # Start tracking
        self.running = True
        
        try:
            self.tracking_loop()
        except KeyboardInterrupt:
            print("\n🛑 Stopping tracker service...")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the tracking service"""
        self.running = False
        
        if self.camera_capture:
            self.camera_capture.release()
            
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        self.print_stats()
        print("✅ Rover tracking service stopped")

def main():
    parser = argparse.ArgumentParser(description="Falconia Rover Tracking Service")
    parser.add_argument("--config", default="falconia_corners.json", help="Corner calibration file")
    parser.add_argument("--camera", help="Camera URL (overrides config)")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    
    args = parser.parse_args()
    
    # Create and start service
    service = RoverTrackerService(
        config_file=args.config,
        camera_url=args.camera,
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port
    )
    
    service.start()

if __name__ == "__main__":
    main()