#!/usr/bin/env python3
"""
Automated ParaView Rover Demo
Creates a self-updating rover that moves over your 3D scan without threading crashes
"""

from paraview.simple import *
import json
import time

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

# Global variables
rover_source = None
rover_rep = None
trail_source = None
trail_rep = None
mqtt_client = None
latest_position = [0, 0, 0.1]
position_history = []
demo_active = False
last_update = 0

def create_rover_visualization():
    """Create rover and trail visualization"""
    global rover_source, rover_rep, trail_source, trail_rep
    
    print("Creating rover visualization...")
    
    # Create rover sphere
    rover_source = Sphere()
    rover_source.Radius = 0.02  # Smaller rover for scale
    rover_source.Center = [0, 0, 0.1]
    
    # Show rover
    rover_rep = Show(rover_source)
    rover_rep.DiffuseColor = [1.0, 0.0, 0.0]  # Bright red
    rover_rep.Opacity = 1.0
    rover_rep.Specular = 0.8  # Make it shiny
    
    # Create trail
    trail_source = ProgrammableSource()
    trail_source.Script = """
import vtk

# Create empty polydata
polydata = vtk.vtkPolyData()
points = vtk.vtkPoints()
points.InsertNextPoint(0, 0, 0.1)
polydata.SetPoints(points)

self.GetOutput().ShallowCopy(polydata)
"""
    
    # Show trail
    trail_rep = Show(trail_source)
    trail_rep.DiffuseColor = [1.0, 0.5, 0.0]  # Orange trail
    trail_rep.Opacity = 0.8
    trail_rep.LineWidth = 3.0
    
    # Render
    Render()
    print("✅ Rover and trail created!")
    
def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    """MQTT connection callback"""
    if rc == 0:
        print("✅ Connected to MQTT broker")
        client.subscribe("rover/position")
    else:
        print(f"❌ MQTT connection failed: {rc}")

def on_mqtt_message(client, userdata, msg):
    """Handle MQTT position updates"""
    global latest_position, position_history
    
    try:
        data = json.loads(msg.payload.decode())
        pos = data["position"]
        
        # Transform coordinates to fit over your 3D scan
        # Adjust these values based on your Falconia model scale
        latest_position = [
            (pos["x"] - 1.0) * 2.0,  # Center and scale X
            (pos["y"] - 0.75) * 2.0, # Center and scale Y  
            pos["z"] + 0.05          # Hover above surface
        ]
        
        # Add to trail history
        position_history.append(latest_position.copy())
        if len(position_history) > 50:  # Limit trail length
            position_history.pop(0)
            
    except Exception as e:
        print(f"Error parsing MQTT: {e}")

def setup_mqtt():
    """Setup MQTT connection"""
    global mqtt_client
    
    if not MQTT_AVAILABLE:
        print("⚠️ MQTT not available")
        return False
        
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_mqtt_connect  
    mqtt_client.on_message = on_mqtt_message
    
    try:
        mqtt_client.connect("localhost", 1883, 60)
        mqtt_client.loop_start()
        print("✅ MQTT connected")
        return True
    except Exception as e:
        print(f"❌ MQTT failed: {e}")
        return False

def update_visualization():
    """Update rover and trail positions"""
    global rover_source, trail_source, latest_position, position_history
    
    # Update rover position
    if rover_source:
        rover_source.Center = latest_position
        
    # Update trail
    if trail_source and len(position_history) > 1:
        trail_script = f"""
import vtk

# Create trail polydata
polydata = vtk.vtkPolyData()
points = vtk.vtkPoints()
lines = vtk.vtkCellArray()

# Add points from history
trail_points = {position_history}
for point in trail_points:
    points.InsertNextPoint(point[0], point[1], point[2])

# Create line segments
for i in range(len(trail_points) - 1):
    line = vtk.vtkLine()
    line.GetPointIds().SetId(0, i)
    line.GetPointIds().SetId(1, i + 1)
    lines.InsertNextCell(line)

polydata.SetPoints(points)
polydata.SetLines(lines)

self.GetOutput().ShallowCopy(polydata)
"""
        trail_source.Script = trail_script
        trail_source.Modified()
    
    # Render the view
    Render()

def auto_update():
    """Auto-update function - call this repeatedly for live demo"""
    global last_update, demo_active
    
    current_time = time.time()
    
    # Process MQTT messages more aggressively
    if mqtt_client:
        # Process multiple messages per update
        for _ in range(10):
            mqtt_client.loop(timeout=0.001)
    
    # Update every 100ms for smooth animation
    if current_time - last_update > 0.1:
        update_visualization()
        last_update = current_time
        print(f"Position: {latest_position}")  # Debug output
        
    return demo_active

def start_demo():
    """Start the automated demo"""
    global demo_active
    
    print("🚀 Starting Automated Rover Demo")
    print("=" * 40)
    
    # Create visualization
    create_rover_visualization()
    
    # Setup MQTT
    mqtt_connected = setup_mqtt()
    
    if mqtt_connected:
        print("✅ Demo ready - rover will move automatically!")
        print("📍 Load your Falconia 3D scan now")
        print("🔄 Call auto_update() repeatedly to see live movement")
        print("⏹️  Call stop_demo() to stop")
    else:
        print("⚠️  MQTT not connected - rover will stay at origin")
        
    demo_active = True
    
    # Setup auto-update timer (ParaView-safe approach)
    print("\n🎯 FOR CONTINUOUS DEMO:")
    print("Run this in ParaView Python shell:")
    print(">>> while auto_update(): pass")
    print("(Press Ctrl+C to stop)")

def stop_demo():
    """Stop the demo"""
    global demo_active, mqtt_client
    
    demo_active = False
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    print("🛑 Demo stopped")

def test_position_updates():
    """Test if positions are updating from MQTT"""
    global latest_position
    
    print("Testing position updates...")
    old_pos = latest_position.copy()
    
    # Process MQTT for 2 seconds
    for i in range(20):
        if mqtt_client:
            for _ in range(5):
                mqtt_client.loop(timeout=0.001)
        time.sleep(0.1)
        if latest_position != old_pos:
            print(f"✅ Position updated! {old_pos} → {latest_position}")
            return True
            
    print(f"❌ Position not updating. Still at: {latest_position}")
    return False

def manual_update_test():
    """Manually update position for testing"""
    global latest_position
    import math
    
    print("Manual position test...")
    for i in range(10):
        t = i * 0.5
        latest_position = [
            math.cos(t) * 0.5,
            math.sin(t) * 0.5, 
            0.1
        ]
        update_visualization()
        print(f"Manual position: {latest_position}")
        time.sleep(0.2)

def setup_camera_for_demo():
    """Position camera for best demo view"""
    view = GetActiveView()
    if view:
        # Set camera for overhead view of Falconia
        view.CameraPosition = [0, 0, 5]
        view.CameraFocalPoint = [0, 0, 0]
        view.CameraViewUp = [0, 1, 0]
        Render()
        print("📷 Camera positioned for demo")

# Initialize
print("🌍 Falconia Rover Demo Loaded!")
print("=" * 40)
print("SETUP STEPS:")
print("1. Load your Falconia 3D scan file")
print("2. Call: start_demo()")
print("3. Call: setup_camera_for_demo()")
print("4. Run: while auto_update(): pass")
print("=" * 40)