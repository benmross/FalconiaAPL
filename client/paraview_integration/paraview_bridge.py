#!/usr/bin/env python3
"""
ParaView Integration Bridge for Live Rover Tracking

This module connects to MQTT to receive rover position updates and
displays them as a live red dot in ParaView on the exoplanet mockup.
"""

import json
import time
import threading
import argparse
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, List
import sys
import os

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Warning: paho-mqtt not installed. Install with: pip install paho-mqtt")
    mqtt = None

try:
    import paraview.simple as pv
    PARAVIEW_AVAILABLE = True
except ImportError:
    print("Warning: ParaView not available. Install ParaView with Python support.")
    PARAVIEW_AVAILABLE = False

class ParaViewBridge:
    """Bridge between MQTT rover position data and ParaView visualization"""
    
    def __init__(self, config_file: str = "config/paraview_config.json"):
        self.config = self.load_config(config_file)
        self.mqtt_client = None
        self.running = False
        
        # ParaView objects
        self.pv_data_source = None
        self.pv_representation = None
        self.pv_view = None
        
        # Position data
        self.current_position = None
        self.position_history = []
        self.last_update_time = 0
        
        # Threading
        self.update_lock = threading.Lock()
        self.paraview_thread = None
        
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        default_config = {
            "mqtt_broker": "localhost",
            "mqtt_port": 1883,
            "mqtt_topic": "rover/position",
            "paraview_file": None,
            "rover_marker": {
                "size": 0.05,
                "color": [1.0, 0.0, 0.0],  # Red
                "opacity": 1.0,
                "shape": "sphere"
            },
            "trail": {
                "enabled": True,
                "max_points": 100,
                "color": [1.0, 0.5, 0.0],  # Orange
                "opacity": 0.7,
                "line_width": 2.0
            },
            "update_rate": 30,  # Hz
            "position_timeout": 5.0,  # seconds
            "coordinate_offset": [0.0, 0.0, 0.0],
            "coordinate_scale": [1.0, 1.0, 1.0]
        }
        
        try:
            with open(config_file, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)
        except FileNotFoundError:
            print(f"Config file {config_file} not found, using defaults")
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            self.save_config(default_config, config_file)
        except json.JSONDecodeError as e:
            print(f"Error parsing config file: {e}")
            
        return default_config
        
    def save_config(self, config: Dict[str, Any], config_file: str):
        """Save configuration to JSON file"""
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
    def setup_mqtt(self):
        """Initialize MQTT client"""
        if mqtt is None:
            print("MQTT not available, cannot receive position updates")
            return False
            
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
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
            print(f"Connected to MQTT broker at {self.config['mqtt_broker']}")
            client.subscribe(self.config["mqtt_topic"])
            print(f"Subscribed to topic: {self.config['mqtt_topic']}")
        else:
            print(f"Failed to connect to MQTT broker, code {rc}")
            
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        print("Disconnected from MQTT broker")
        
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT position messages"""
        try:
            data = json.loads(msg.payload.decode())
            self.update_rover_position(data)
        except json.JSONDecodeError as e:
            print(f"Error parsing MQTT message: {e}")
        except Exception as e:
            print(f"Error processing position update: {e}")
            
    def update_rover_position(self, position_data: Dict[str, Any]):
        """Update rover position from MQTT data"""
        with self.update_lock:
            # Apply coordinate transformations
            pos = position_data["position"]
            offset = self.config["coordinate_offset"]
            scale = self.config["coordinate_scale"]
            
            transformed_position = [
                pos["x"] * scale[0] + offset[0],
                pos["y"] * scale[1] + offset[1],
                pos["z"] * scale[2] + offset[2]
            ]
            
            self.current_position = {
                "position": transformed_position,
                "timestamp": position_data["timestamp"],
                "tag_id": position_data["tag_id"],
                "confidence": position_data.get("confidence", 1.0)
            }
            
            # Add to history for trail
            if self.config["trail"]["enabled"]:
                self.position_history.append({
                    "position": transformed_position.copy(),
                    "timestamp": time.time()
                })
                
                # Limit history size
                max_points = self.config["trail"]["max_points"]
                if len(self.position_history) > max_points:
                    self.position_history = self.position_history[-max_points:]
                    
            self.last_update_time = time.time()
            
            print(f"Updated rover position: ({transformed_position[0]:.3f}, "
                  f"{transformed_position[1]:.3f}, {transformed_position[2]:.3f})")
                  
    def setup_paraview(self):
        """Initialize ParaView environment"""
        if not PARAVIEW_AVAILABLE:
            print("ParaView not available, using simulation mode")
            return False
            
        try:
            # Load base scene if specified
            if self.config.get("paraview_file"):
                if os.path.exists(self.config["paraview_file"]):
                    pv.LoadState(self.config["paraview_file"])
                    print(f"Loaded ParaView state: {self.config['paraview_file']}")
                else:
                    print(f"Warning: ParaView file not found: {self.config['paraview_file']}")
                    
            # Get or create render view
            self.pv_view = pv.GetActiveViewOrCreate('RenderView')
            
            # Create rover marker data source
            self.create_rover_marker()
            
            # Create trail if enabled
            if self.config["trail"]["enabled"]:
                self.create_trail()
                
            print("ParaView environment initialized")
            return True
            
        except Exception as e:
            print(f"Error setting up ParaView: {e}")
            return False
            
    def create_rover_marker(self):
        """Create the rover position marker in ParaView"""
        if not PARAVIEW_AVAILABLE:
            return
            
        try:
            # Create a sphere source for the rover marker
            self.pv_rover_source = pv.Sphere()
            self.pv_rover_source.Radius = self.config["rover_marker"]["size"]
            
            # Create representation
            self.pv_rover_rep = pv.Show(self.pv_rover_source, self.pv_view)
            
            # Set appearance
            marker_config = self.config["rover_marker"]
            self.pv_rover_rep.DiffuseColor = marker_config["color"]
            self.pv_rover_rep.Opacity = marker_config["opacity"]
            
            # Position initially at origin
            self.pv_rover_source.Center = [0.0, 0.0, 0.0]
            
            print("Rover marker created in ParaView")
            
        except Exception as e:
            print(f"Error creating rover marker: {e}")
            
    def create_trail(self):
        """Create the rover trail in ParaView"""
        if not PARAVIEW_AVAILABLE or not self.config["trail"]["enabled"]:
            return
            
        try:
            # Create programmable source for trail
            self.pv_trail_source = pv.ProgrammableSource()
            
            # Set up trail representation
            self.pv_trail_rep = pv.Show(self.pv_trail_source, self.pv_view)
            
            # Configure trail appearance
            trail_config = self.config["trail"]
            self.pv_trail_rep.DiffuseColor = trail_config["color"]
            self.pv_trail_rep.Opacity = trail_config["opacity"]
            self.pv_trail_rep.LineWidth = trail_config["line_width"]
            self.pv_trail_rep.Representation = 'Wireframe'
            
            print("Rover trail created in ParaView")
            
        except Exception as e:
            print(f"Error creating rover trail: {e}")
            
    def update_paraview_visualization(self):
        """Update ParaView visualization with current rover position"""
        if not PARAVIEW_AVAILABLE:
            return
            
        with self.update_lock:
            try:
                # Update rover position
                if self.current_position and self.pv_rover_source:
                    pos = self.current_position["position"]
                    self.pv_rover_source.Center = pos
                    
                    # Check if position is recent
                    age = time.time() - self.last_update_time
                    if age > self.config["position_timeout"]:
                        # Fade marker if position is old
                        self.pv_rover_rep.Opacity = self.config["rover_marker"]["opacity"] * 0.3
                    else:
                        self.pv_rover_rep.Opacity = self.config["rover_marker"]["opacity"]
                        
                # Update trail
                if self.config["trail"]["enabled"] and self.pv_trail_source:
                    self.update_trail_data()
                    
                # Refresh view
                self.pv_view.StillRender()
                
            except Exception as e:
                print(f"Error updating ParaView visualization: {e}")
                
    def update_trail_data(self):
        """Update trail data in ParaView"""
        if not self.position_history:
            return
            
        try:
            # Create trail geometry from position history
            script = f"""
import vtk
from paraview import vtk as pv_vtk

# Create polydata for trail
polydata = vtk.vtkPolyData()
points = vtk.vtkPoints()
lines = vtk.vtkCellArray()

# Add points from history
trail_data = {self.position_history}

for i, pos_data in enumerate(trail_data):
    pos = pos_data['position']
    points.InsertNextPoint(pos[0], pos[1], pos[2])

# Create line segments
for i in range(len(trail_data) - 1):
    line = vtk.vtkLine()
    line.GetPointIds().SetId(0, i)
    line.GetPointIds().SetId(1, i + 1)
    lines.InsertNextCell(line)

polydata.SetPoints(points)
polydata.SetLines(lines)

# Set output
self.GetOutput().ShallowCopy(polydata)
"""
            
            self.pv_trail_source.Script = script
            self.pv_trail_source.Modified()
            
        except Exception as e:
            print(f"Error updating trail data: {e}")
            
    def paraview_update_loop(self):
        """Main ParaView update loop running in separate thread"""
        update_interval = 1.0 / self.config["update_rate"]
        
        while self.running:
            try:
                self.update_paraview_visualization()
                time.sleep(update_interval)
            except Exception as e:
                print(f"Error in ParaView update loop: {e}")
                time.sleep(1.0)
                
    def run(self):
        """Main execution loop"""
        print("Starting ParaView Bridge...")
        
        # Setup MQTT
        if not self.setup_mqtt():
            print("Failed to setup MQTT, exiting")
            return 1
            
        # Setup ParaView
        paraview_success = self.setup_paraview()
        
        self.running = True
        
        # Start MQTT client
        if self.mqtt_client:
            self.mqtt_client.loop_start()
            
        # Start ParaView update thread
        if paraview_success:
            self.paraview_thread = threading.Thread(target=self.paraview_update_loop)
            self.paraview_thread.daemon = True
            self.paraview_thread.start()
        else:
            print("Running in simulation mode (no ParaView visualization)")
            
        print("ParaView Bridge running. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                if not paraview_success:
                    # Simulation mode - just print position updates
                    if self.current_position:
                        pos = self.current_position["position"]
                        age = time.time() - self.last_update_time
                        print(f"[SIM] Rover at ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}) "
                              f"(age: {age:.1f}s)")
                    time.sleep(1.0)
                else:
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\nShutting down ParaView Bridge...")
            
        self.cleanup()
        return 0
        
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
        if self.paraview_thread:
            self.paraview_thread.join(timeout=2.0)
            
        print("ParaView Bridge shutdown complete")

def main():
    parser = argparse.ArgumentParser(description="ParaView Bridge for rover tracking")
    parser.add_argument("--config", default="config/paraview_config.json",
                        help="Configuration file path")
    parser.add_argument("--mqtt-broker", help="MQTT broker address (overrides config)")
    parser.add_argument("--mqtt-topic", help="MQTT topic (overrides config)")
    parser.add_argument("--sim-mode", action="store_true",
                        help="Run in simulation mode without ParaView")
    
    args = parser.parse_args()
    
    try:
        bridge = ParaViewBridge(args.config)
        
        # Override config with command line arguments
        if args.mqtt_broker:
            bridge.config["mqtt_broker"] = args.mqtt_broker
        if args.mqtt_topic:
            bridge.config["mqtt_topic"] = args.mqtt_topic
            
        # Force simulation mode if requested
        if args.sim_mode:
            global PARAVIEW_AVAILABLE
            PARAVIEW_AVAILABLE = False
            
        return bridge.run()
        
    except Exception as e:
        print(f"Error starting ParaView Bridge: {e}")
        return 1

if __name__ == "__main__":
    exit(main())