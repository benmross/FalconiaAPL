#!/usr/bin/env python3
"""
Test Pipeline for Rover Tracking System

This module provides testing utilities to validate the complete
rover tracking pipeline with mock data.
"""

import json
import time
import threading
import random
import math
import argparse
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Warning: paho-mqtt not installed. Install with: pip install paho-mqtt")
    mqtt = None

class MockRoverTracker:
    """Mock rover that publishes simulated position data"""
    
    def __init__(self, config_file: str = "config/test_config.json"):
        self.config = self.load_config(config_file)
        self.mqtt_client = None
        self.running = False
        self.current_position = [0.5, 0.5, 0.1]  # Start in center
        self.movement_pattern = "random"
        self.setup_mqtt()
        
    def load_config(self, config_file: str):
        """Load test configuration"""
        default_config = {
            "mqtt_broker": "localhost",
            "mqtt_port": 1883,
            "mqtt_topic": "rover/position",
            "update_rate": 10,  # Hz
            "movement_pattern": "random",  # random, circle, square, figure8
            "movement_speed": 0.1,  # m/s
            "workspace": {
                "x_min": 0.0,
                "x_max": 2.0,
                "y_min": 0.0,
                "y_max": 1.5,
                "z_min": 0.05,
                "z_max": 0.15
            },
            "noise_level": 0.01,  # Position noise in meters
            "tag_id": 42
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
                
        return default_config
        
    def setup_mqtt(self):
        """Initialize MQTT client"""
        if mqtt is None:
            print("MQTT not available")
            return False
            
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        
        try:
            self.mqtt_client.connect(
                self.config["mqtt_broker"], 
                self.config["mqtt_port"], 
                60
            )
            return True
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False
            
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            print(f"Mock rover connected to MQTT broker")
        else:
            print(f"Failed to connect to MQTT broker, code {rc}")
            
    def update_position(self):
        """Update rover position based on movement pattern"""
        dt = 1.0 / self.config["update_rate"]
        speed = self.config["movement_speed"]
        pattern = self.config["movement_pattern"]
        workspace = self.config["workspace"]
        
        if pattern == "random":
            # Random walk with bounds checking
            dx = random.uniform(-speed * dt, speed * dt)
            dy = random.uniform(-speed * dt, speed * dt)
            
            new_x = max(workspace["x_min"], min(workspace["x_max"], 
                       self.current_position[0] + dx))
            new_y = max(workspace["y_min"], min(workspace["y_max"],
                       self.current_position[1] + dy))
            new_z = random.uniform(workspace["z_min"], workspace["z_max"])
            
        elif pattern == "circle":
            # Circular motion
            t = time.time() * speed
            center_x = (workspace["x_min"] + workspace["x_max"]) / 2
            center_y = (workspace["y_min"] + workspace["y_max"]) / 2
            radius = min(workspace["x_max"] - center_x, workspace["y_max"] - center_y) * 0.8
            
            new_x = center_x + radius * math.cos(t)
            new_y = center_y + radius * math.sin(t)
            new_z = (workspace["z_min"] + workspace["z_max"]) / 2
            
        elif pattern == "square":
            # Square motion
            t = time.time() * speed
            side_length = min(workspace["x_max"] - workspace["x_min"],
                            workspace["y_max"] - workspace["y_min"]) * 0.8
            
            # Determine which side of square we're on
            cycle_time = side_length * 4
            t_normalized = (t % cycle_time) / cycle_time
            
            if t_normalized < 0.25:  # Bottom side
                progress = t_normalized * 4
                new_x = workspace["x_min"] + side_length * progress
                new_y = workspace["y_min"]
            elif t_normalized < 0.5:  # Right side
                progress = (t_normalized - 0.25) * 4
                new_x = workspace["x_min"] + side_length
                new_y = workspace["y_min"] + side_length * progress
            elif t_normalized < 0.75:  # Top side
                progress = (t_normalized - 0.5) * 4
                new_x = workspace["x_min"] + side_length * (1 - progress)
                new_y = workspace["y_min"] + side_length
            else:  # Left side
                progress = (t_normalized - 0.75) * 4
                new_x = workspace["x_min"]
                new_y = workspace["y_min"] + side_length * (1 - progress)
                
            new_z = (workspace["z_min"] + workspace["z_max"]) / 2
            
        elif pattern == "figure8":
            # Figure-8 motion
            t = time.time() * speed * 0.5
            center_x = (workspace["x_min"] + workspace["x_max"]) / 2
            center_y = (workspace["y_min"] + workspace["y_max"]) / 2
            scale_x = (workspace["x_max"] - workspace["x_min"]) * 0.4
            scale_y = (workspace["y_max"] - workspace["y_min"]) * 0.4
            
            new_x = center_x + scale_x * math.sin(t)
            new_y = center_y + scale_y * math.sin(2 * t)
            new_z = (workspace["z_min"] + workspace["z_max"]) / 2
            
        else:
            # Stationary
            new_x, new_y, new_z = self.current_position
            
        # Add noise
        noise = self.config["noise_level"]
        new_x += random.uniform(-noise, noise)
        new_y += random.uniform(-noise, noise)
        new_z += random.uniform(-noise, noise)
        
        self.current_position = [new_x, new_y, new_z]
        
    def publish_position(self):
        """Publish current position via MQTT"""
        position_data = {
            "timestamp": time.time(),
            "tag_id": self.config["tag_id"],
            "position": {
                "x": self.current_position[0],
                "y": self.current_position[1],
                "z": self.current_position[2]
            },
            "raw_position": {
                "x": self.current_position[0],
                "y": self.current_position[1],
                "z": self.current_position[2]
            },
            "distance": math.sqrt(sum(x**2 for x in self.current_position)),
            "confidence": 1.0
        }
        
        if self.mqtt_client and self.mqtt_client.is_connected():
            try:
                message = json.dumps(position_data)
                self.mqtt_client.publish(self.config["mqtt_topic"], message)
            except Exception as e:
                print(f"Error publishing position: {e}")
        
        # Print position for debugging
        pos = self.current_position
        print(f"Mock rover position: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
        
    def run(self):
        """Main simulation loop"""
        self.running = True
        
        if self.mqtt_client:
            self.mqtt_client.loop_start()
            
        print(f"Starting mock rover simulation...")
        print(f"Movement pattern: {self.config['movement_pattern']}")
        print(f"Update rate: {self.config['update_rate']} Hz")
        print(f"Publishing to topic: {self.config['mqtt_topic']}")
        print("Press Ctrl+C to stop")
        
        update_interval = 1.0 / self.config["update_rate"]
        
        try:
            while self.running:
                start_time = time.time()
                
                self.update_position()
                self.publish_position()
                
                # Maintain update rate
                elapsed = time.time() - start_time
                sleep_time = max(0, update_interval - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\nStopping mock rover simulation...")
            
        self.cleanup()
        
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
        print("Mock rover simulation stopped")

class PipelineTester:
    """Test the complete rover tracking pipeline"""
    
    def __init__(self):
        self.mock_rover = None
        self.bridge_process = None
        
    def test_coordinate_transform(self):
        """Test coordinate transformation accuracy"""
        print("Testing coordinate transformation...")
        
        from paraview_integration.coordinate_transform import CoordinateTransform
        
        # Create test transformation
        transform = CoordinateTransform()
        
        # Add test reference points (pixel -> world)
        test_points = [
            ((100, 100), (0.0, 0.0)),    # Bottom-left
            ((500, 100), (2.0, 0.0)),    # Bottom-right
            ((500, 400), (2.0, 1.5)),    # Top-right
            ((100, 400), (0.0, 1.5)),    # Top-left
        ]
        
        for pixel, world in test_points:
            transform.add_reference_point(pixel, world)
            
        # Calibrate
        if transform.calibrate_homography():
            print("✓ Homography calibration successful")
            
            # Test transformation accuracy
            error = transform.calculate_transformation_error()
            print(f"  RMS error: {error:.6f} meters")
            
            # Test some transformations
            test_pixels = [(300, 250), (200, 150), (400, 350)]
            for pixel in test_pixels:
                world = transform.pixel_to_world(pixel)
                print(f"  Pixel {pixel} -> World ({world[0]:.3f}, {world[1]:.3f})")
                
            return True
        else:
            print("✗ Coordinate transformation test failed")
            return False
            
    def test_mqtt_communication(self):
        """Test MQTT communication"""
        print("Testing MQTT communication...")
        
        received_messages = []
        
        def on_message(client, userdata, msg):
            try:
                data = json.loads(msg.payload.decode())
                received_messages.append(data)
            except:
                pass
                
        if mqtt is None:
            print("✗ MQTT not available")
            return False
            
        try:
            # Set up subscriber
            subscriber = mqtt.Client()
            subscriber.on_message = on_message
            subscriber.connect("localhost", 1883, 60)
            subscriber.subscribe("rover/position")
            subscriber.loop_start()
            
            # Set up publisher
            publisher = mqtt.Client()
            publisher.connect("localhost", 1883, 60)
            
            # Send test message
            test_data = {
                "timestamp": time.time(),
                "tag_id": 99,
                "position": {"x": 1.0, "y": 0.5, "z": 0.1},
                "raw_position": {"x": 1.0, "y": 0.5, "z": 0.1},
                "distance": 1.12,
                "confidence": 1.0
            }
            
            publisher.publish("rover/position", json.dumps(test_data))
            
            # Wait for message
            time.sleep(1.0)
            
            # Check if message was received
            if received_messages:
                print("✓ MQTT communication test passed")
                print(f"  Received: {received_messages[0]['position']}")
                success = True
            else:
                print("✗ MQTT communication test failed")
                success = False
                
            # Cleanup
            subscriber.loop_stop()
            subscriber.disconnect()
            publisher.disconnect()
            
            return success
            
        except Exception as e:
            print(f"✗ MQTT communication test failed: {e}")
            return False
            
    def run_full_pipeline_test(self, duration: float = 30.0):
        """Run complete pipeline test"""
        print(f"Running full pipeline test for {duration} seconds...")
        
        # Start mock rover
        mock_rover = MockRoverTracker("config/test_config.json")
        mock_rover.config["movement_pattern"] = "circle"
        mock_rover.config["update_rate"] = 5
        
        # Run in separate thread
        rover_thread = threading.Thread(target=mock_rover.run)
        rover_thread.daemon = True
        rover_thread.start()
        
        print("Mock rover started. You can now:")
        print("1. Run paraview_bridge.py to see visualization")
        print("2. Monitor MQTT messages")
        print("3. Check position accuracy")
        
        # Wait for test duration
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            
        # Stop mock rover
        mock_rover.cleanup()
        
        print("Full pipeline test completed")
        return True

def main():
    parser = argparse.ArgumentParser(description="Test rover tracking pipeline")
    parser.add_argument("--test", choices=["transform", "mqtt", "full"], 
                       default="full", help="Test to run")
    parser.add_argument("--duration", type=float, default=30.0,
                       help="Test duration in seconds (for full test)")
    
    args = parser.parse_args()
    
    tester = PipelineTester()
    
    if args.test == "transform":
        success = tester.test_coordinate_transform()
    elif args.test == "mqtt":
        success = tester.test_mqtt_communication()
    elif args.test == "full":
        # Run all tests
        print("Running comprehensive pipeline test...")
        print("=" * 50)
        
        transform_ok = tester.test_coordinate_transform()
        mqtt_ok = tester.test_mqtt_communication()
        
        if transform_ok and mqtt_ok:
            print("\nAll individual tests passed. Starting full pipeline test...")
            success = tester.run_full_pipeline_test(args.duration)
        else:
            print("\nSome individual tests failed. Skipping full pipeline test.")
            success = False
    else:
        print(f"Unknown test: {args.test}")
        success = False
        
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())