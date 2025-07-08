#!/usr/bin/env python3
"""
Falconia Rover Tracking Background Service
Continuously detects AprilTag, transforms coordinates, and publishes to MQTT.
"""

import cv2
import json
import numpy as np
import time
import threading
import argparse
from pupil_apriltags import Detector
import paho.mqtt.client as mqtt

# Configuration
APRILTAG_ID = 1  # AprilTag ID to track (easily configurable)

class RoverTrackerService:
    def __init__(self, config_file="falconia_corners.json", camera_url=None, mqtt_broker="localhost", mqtt_port=1883, show_display=True):
        self.config_file = config_file
        self.camera_url = camera_url
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.show_display = show_display
        
        # State variables
        self.corners_data = None
        self.pixel_corners = None
        self.model_coords = None
        self.detector = None
        self.camera_capture = None
        self.mqtt_client = None
        self.running = False
        self.last_position = None
        self.current_frame = None
        self.current_detections = []
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
            # Old AprilTag format - map to consistent ordering
            # back_left -> top_left, back_right -> top_right, front_right -> bottom_right, front_left -> bottom_left
            pixel_points = [
                camera_corners["back_left"]["pixel"],    # top_left
                camera_corners["back_right"]["pixel"],   # top_right
                camera_corners["front_right"]["pixel"],  # bottom_right
                camera_corners["front_left"]["pixel"]    # bottom_left
            ]
            print("📌 Using AprilTag corner format")
        
        # Use ParaView model bounds - corner coordinates from user
        # Format: [x, z] (y is fixed at 0.2 for hover height)
        model_points = [
            [-0.6, -0.75],  # top_left [x, z]
            [0.6, -0.75],   # top_right [x, z]
            [0.6, 1.0],     # bottom_right [x, z]  
            [-0.6, 1.0]     # bottom_left [x, z]
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
        
        # Optimize camera capture for low latency
        self.camera_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer
        self.camera_capture.set(cv2.CAP_PROP_FPS, 30)  # Request higher FPS
            
        # Initialize AprilTag detector
        self.detector = Detector(families='tag36h11')
        print("✅ Camera and detector ready")
        
        # Setup display window if enabled
        if self.show_display:
            cv2.namedWindow("Falconia Rover Tracker", cv2.WINDOW_AUTOSIZE)
            print("📺 Display window created")
        
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
    
    def draw_apriltag_detection(self, frame, detection):
        """Draw AprilTag detection on frame"""
        # Draw tag outline
        corners = detection.corners.astype(int)
        cv2.polylines(frame, [corners], True, (0, 255, 0), 2)
        
        # Draw center point
        center = detection.center.astype(int)
        cv2.circle(frame, tuple(center), 5, (0, 255, 0), -1)
        
        # Draw tag ID
        cv2.putText(frame, f"ID: {detection.tag_id}", 
                   (center[0] - 20, center[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # If this is our target tag, highlight it differently
        if detection.tag_id == APRILTAG_ID:
            cv2.polylines(frame, [corners], True, (0, 0, 255), 3)
            cv2.putText(frame, "TRACKING", 
                       (center[0] - 35, center[1] + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    def get_latest_frame(self):
        """Get the most recent frame by dropping buffered frames"""
        # Read multiple frames to clear the buffer and get the latest one
        frame = None
        for _ in range(5):  # Clear buffer by reading multiple frames
            ret, temp_frame = self.camera_capture.read()
            if ret:
                frame = temp_frame
            else:
                break
        return frame
    
    def detect_rover_position(self):
        """Detect rover AprilTag and return model coordinates"""
        try:
            # Get latest frame (drop buffered frames)
            frame = self.get_latest_frame()
            if frame is None:
                return None
            
            # Store frame for display
            self.current_frame = frame.copy()
            
            # Detect AprilTags
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detections = self.detector.detect(gray)
            self.current_detections = detections
            
            # Look for target tag
            for detection in detections:
                if detection.tag_id == APRILTAG_ID:
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
    
    def update_display(self):
        """Update the live camera display"""
        if not self.show_display or self.current_frame is None:
            return
        
        display_frame = self.current_frame.copy()
        
        # Draw all detected AprilTags
        for detection in self.current_detections:
            self.draw_apriltag_detection(display_frame, detection)
        
        # Draw corner calibration points if available
        if self.pixel_corners is not None:
            for i, corner in enumerate(self.pixel_corners):
                cv2.circle(display_frame, tuple(corner.astype(int)), 8, (255, 0, 0), 2)
                cv2.putText(display_frame, f"C{i+1}", 
                           (int(corner[0]) + 10, int(corner[1]) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        # Add status information
        status_text = [
            f"Tracking AprilTag ID: {APRILTAG_ID}",
            f"Detections: {self.stats['detections']} | Missed: {self.stats['missed']}",
            f"Published: {self.stats['published']}"
        ]
        
        for i, text in enumerate(status_text):
            cv2.putText(display_frame, text, (10, 25 + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Show the frame
        cv2.imshow("Falconia Rover Tracker", display_frame)
        
        # Handle window events (non-blocking)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # 'q' or ESC to quit
            self.running = False
    
    def publish_position(self, position):
        """Publish rover position to MQTT"""
        try:
            position_data = {
                "timestamp": time.time(),
                "rover_id": APRILTAG_ID,
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
        print(f"🚀 Starting rover tracking loop for AprilTag ID {APRILTAG_ID}...")
        
        while self.running:
            try:
                position = self.detect_rover_position()
                
                # Update display
                self.update_display()
                
                if position:
                    # Only publish if position changed significantly
                    if (self.last_position is None or 
                        abs(position[0] - self.last_position[0]) > 0.01 or
                        abs(position[2] - self.last_position[2]) > 0.01):
                        
                        self.publish_position(position)
                        self.last_position = position
                        print(f"📍 Rover: [{position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f}]")
                
                # Control update rate
                time.sleep(0.1)  # 10 Hz
                
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
        print(f"📌 Tracking AprilTag ID: {APRILTAG_ID}")
        
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
        
        if self.show_display:
            cv2.destroyAllWindows()
        
        self.print_stats()
        print("✅ Rover tracking service stopped")

def main():
    parser = argparse.ArgumentParser(description="Falconia Rover Tracking Service")
    parser.add_argument("--config", default="falconia_corners.json", help="Corner calibration file")
    parser.add_argument("--camera", help="Camera URL (overrides config)")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--no-display", action="store_true", help="Disable live camera display")
    
    args = parser.parse_args()
    
    # Create and start service
    service = RoverTrackerService(
        config_file=args.config,
        camera_url=args.camera,
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        show_display=not args.no_display
    )
    
    service.start()

if __name__ == "__main__":
    main()