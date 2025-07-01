#!/usr/bin/env python3
"""
ParaView Rover Tracking Plugin
Run this script inside ParaView's Python shell to enable live rover tracking
"""

import json
import time
import threading
from typing import Dict, Any, List, Optional

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("Warning: paho-mqtt not installed. Install with: pip install paho-mqtt")
    MQTT_AVAILABLE = False

try:
    import paraview.simple as pv
    PARAVIEW_AVAILABLE = True
except ImportError:
    print("This script must be run inside ParaView")
    PARAVIEW_AVAILABLE = False

class ParaViewRoverPlugin:
    """Plugin to display live rover tracking in ParaView"""
    
    def __init__(self, config_file: str = "client/paraview_integration/config/paraview_config.json"):
        self.config = self.load_config(config_file)
        self.mqtt_client = None
        self.running = False
        self.current_position = None
        self.position_history = []
        self.update_lock = threading.Lock()
        
        # ParaView objects
        self.pv_rover_source = None
        self.pv_rover_rep = None
        self.pv_trail_source = None
        self.pv_trail_rep = None
        
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file not found: {config_file}")
            return self.get_default_config()
        except json.JSONDecodeError as e:
            print(f"Error parsing config file: {e}")
            return self.get_default_config()
            
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "mqtt_broker": "localhost",
            "mqtt_port": 1883,
            "mqtt_topic": "rover/position",
            "rover_marker": {
                "size": 0.05,
                "color": [1.0, 0.0, 0.0],
                "opacity": 1.0
            },
            "trail": {
                "enabled": True,
                "max_points": 100,
                "color": [1.0, 0.5, 0.0],
                "opacity": 0.7
            },
            "coordinate_offset": [0.0, 0.0, 0.0],
            "coordinate_scale": [1.0, 1.0, 1.0]
        }
    
    def setup_mqtt(self):
        """Initialize MQTT client"""
        if not MQTT_AVAILABLE:
            print("MQTT not available")
            return False
            
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        
        try:
            self.mqtt_client.connect(
                self.config["mqtt_broker"],
                self.config["mqtt_port"],
                60
            )
            return True
        except Exception as e:
            print(f"Failed to connect to MQTT: {e}")
            return False
    
    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            print(f"Connected to MQTT broker at {self.config['mqtt_broker']}")
            client.subscribe(self.config["mqtt_topic"])
            print(f"Subscribed to: {self.config['mqtt_topic']}")
        else:
            print(f"Failed to connect to MQTT broker, code {rc}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            data = json.loads(msg.payload.decode())
            self.update_rover_position(data)
        except json.JSONDecodeError as e:
            print(f"Error parsing MQTT message: {e}")
    
    def update_rover_position(self, position_data: Dict[str, Any]):
        """Update rover position from MQTT data"""
        with self.update_lock:
            pos = position_data["position"]
            offset = self.config["coordinate_offset"]
            scale = self.config["coordinate_scale"]
            
            transformed_position = [
                pos["x"] * scale[0] + offset[0],
                pos["y"] * scale[1] + offset[1],
                pos["z"] * scale[2] + offset[2]
            ]
            
            self.current_position = transformed_position
            
            # Add to history for trail
            if self.config["trail"]["enabled"]:
                self.position_history.append(transformed_position.copy())
                if len(self.position_history) > self.config["trail"]["max_points"]:
                    self.position_history.pop(0)
            
            # Update ParaView visualization
            self.update_paraview()
            
            print(f"Rover position: ({transformed_position[0]:.3f}, "
                  f"{transformed_position[1]:.3f}, {transformed_position[2]:.3f})")
    
    def create_rover_marker(self):
        """Create rover marker in current ParaView view"""
        if not PARAVIEW_AVAILABLE:
            return
            
        # Create sphere for rover
        self.pv_rover_source = pv.Sphere()
        self.pv_rover_source.Radius = self.config["rover_marker"]["size"]
        self.pv_rover_source.Center = [0, 0, 0]
        
        # Show in current view
        self.pv_rover_rep = pv.Show(self.pv_rover_source)
        
        # Set appearance
        marker_config = self.config["rover_marker"]
        self.pv_rover_rep.DiffuseColor = marker_config["color"]
        self.pv_rover_rep.Opacity = marker_config["opacity"]
        
        print("Rover marker created")
    
    def create_trail(self):
        """Create trail visualization"""
        if not PARAVIEW_AVAILABLE or not self.config["trail"]["enabled"]:
            return
            
        # Create programmable source for trail
        self.pv_trail_source = pv.ProgrammableSource()
        
        # Show trail
        self.pv_trail_rep = pv.Show(self.pv_trail_source)
        
        # Set trail appearance
        trail_config = self.config["trail"]
        self.pv_trail_rep.DiffuseColor = trail_config["color"]
        self.pv_trail_rep.Opacity = trail_config["opacity"]
        
        print("Trail created")
    
    def update_paraview(self):
        """Update ParaView visualization"""
        if not PARAVIEW_AVAILABLE:
            return
            
        try:
            # Update rover position
            if self.pv_rover_source and self.current_position:
                self.pv_rover_source.Center = self.current_position
                
            # Update trail
            if self.pv_trail_source and self.position_history:
                self.update_trail()
                
            # Render
            pv.Render()
            
        except Exception as e:
            print(f"Error updating ParaView: {e}")
    
    def update_trail(self):
        """Update trail visualization"""
        if not self.position_history:
            return
            
        # Create trail script
        trail_points = self.position_history
        script = f"""
import vtk
from paraview import vtk as pv_vtk

# Create polydata for trail
polydata = vtk.vtkPolyData()
points = vtk.vtkPoints()
lines = vtk.vtkCellArray()

# Add points
trail_data = {trail_points}
for pos in trail_data:
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
    
    def start(self):
        """Start the rover tracking plugin"""
        print("Starting ParaView Rover Tracking Plugin...")
        
        if not PARAVIEW_AVAILABLE:
            print("ParaView not available!")
            return False
            
        # Create visualization objects
        self.create_rover_marker()
        self.create_trail()
        
        # Setup MQTT
        if not self.setup_mqtt():
            print("Failed to setup MQTT")
            return False
            
        # Start MQTT loop
        self.running = True
        self.mqtt_client.loop_start()
        
        print("Plugin started! Listening for rover position updates...")
        print(f"Topic: {self.config['mqtt_topic']}")
        return True
    
    def stop(self):
        """Stop the plugin"""
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        print("Plugin stopped")

# Global plugin instance
rover_plugin = None

def start_rover_tracking():
    """Start rover tracking in ParaView"""
    global rover_plugin
    
    if rover_plugin is not None:
        print("Rover tracking already running")
        return
        
    rover_plugin = ParaViewRoverPlugin()
    rover_plugin.start()

def stop_rover_tracking():
    """Stop rover tracking"""
    global rover_plugin
    
    if rover_plugin is not None:
        rover_plugin.stop()
        rover_plugin = None

# Auto-start when script is run
if __name__ == "__main__":
    print("=" * 50)
    print("ParaView Rover Tracking Plugin")
    print("=" * 50)
    print("To start tracking, run: start_rover_tracking()")
    print("To stop tracking, run: stop_rover_tracking()")
    print("=" * 50)
    
    # Auto-start
    start_rover_tracking()