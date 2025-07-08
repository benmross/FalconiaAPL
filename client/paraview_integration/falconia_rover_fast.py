#!/usr/bin/env python3
"""
Fast Falconia Rover Tracking for ParaView
Subscribes to MQTT coordinates from background service - no camera processing!

USAGE IN PARAVIEW:
1. Start background service: python rover_tracker_service.py
2. Load your Falconia 3D model in ParaView
3. exec(open('falconia_rover_fast.py').read())
4. setup_fast_tracking()
5. update_position() - Very fast updates from MQTT only!
"""

from paraview.simple import *
import json
import time

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("⚠️ Install paho-mqtt for live tracking")

# Global variables
rover_source = None
rover_rep = None
mqtt_client = None
latest_position = [0, 0, 0]
position_history = []
last_update_time = 0

def setup_fast_tracking(mqtt_broker="localhost", mqtt_port=1883):
    """Setup fast rover tracking (MQTT only, no camera processing)"""
    
    print("⚡ Setting up Fast Falconia Rover Tracking")
    print("=" * 45)
    print("📡 This script only subscribes to MQTT coordinates")
    print("🚀 Make sure rover_tracker_service.py is running!")
    print()
    
    # Create rover visualization
    create_rover_sphere()
    
    # Setup MQTT subscription
    if MQTT_AVAILABLE:
        setup_mqtt_subscription(mqtt_broker, mqtt_port)
    else:
        print("❌ MQTT not available - install paho-mqtt")
        return False
    
    print("✅ Fast rover tracking ready!")
    print("🔄 Run: update_position() for instant updates")
    print("📊 Run: show_status() for connection info")
    return True

def create_rover_sphere():
    """Create red rover sphere"""
    global rover_source, rover_rep
    
    # Get model bounds for sizing
    active_source = GetActiveSource()
    if active_source:
        data_info = active_source.GetDataInformation()
        bounds = data_info.GetBounds()
        model_size = max(bounds[1] - bounds[0], bounds[5] - bounds[4])
        rover_size = model_size * 0.02
        hover_y = bounds[3] * 0.95
    else:
        rover_size = 0.05
        hover_y = 0.2
    
    # Create dynamic rover sphere
    rover_source = LiveProgrammableSource()
    update_rover_geometry([0, hover_y, 0], rover_size)
    
    # Style the rover
    rover_rep = Show(rover_source)
    rover_rep.DiffuseColor = [1.0, 0.0, 0.0]  # Bright red
    rover_rep.Opacity = 1.0
    rover_rep.Specular = 0.8
    
    Render()
    print(f"🔴 Created rover sphere (radius: {rover_size:.3f})")

def update_rover_geometry(position, size):
    """Update rover sphere geometry"""
    global rover_source
    
    if rover_source:
        x, y, z = position
        print(f"🔧 Updating sphere: pos=[{x:.3f}, {y:.3f}, {z:.3f}], size={size:.3f}")
        
        rover_source.Script = f"""
import vtk
sphere = vtk.vtkSphereSource()
sphere.SetCenter({x}, {y}, {z})
sphere.SetRadius({size})
sphere.SetPhiResolution(20)
sphere.SetThetaResolution(20)
sphere.Update()
output = self.GetOutput()
output.ShallowCopy(sphere.GetOutput())
print(f"VTK: Created sphere at [{x}, {y}, {z}] with radius {size}")
"""
        rover_source.Modified()
        rover_source.UpdatePipeline()
        print(f"✅ Geometry updated and pipeline refreshed")
    else:
        print("❌ No rover_source available!")

def setup_mqtt_subscription(mqtt_broker, mqtt_port):
    """Setup MQTT subscription to rover coordinates"""
    global mqtt_client
    
    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_message = on_mqtt_message
        
        mqtt_client.connect(mqtt_broker, mqtt_port, 60)
        mqtt_client.loop_start()
        print(f"📡 MQTT client connected to {mqtt_broker}:{mqtt_port}")
        return True
        
    except Exception as e:
        print(f"❌ MQTT setup failed: {e}")
        return False

def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    """MQTT connection callback"""
    if rc == 0:
        result = client.subscribe("rover/position")
        print(f"✅ Subscribed to rover/position: {result}")
    else:
        print(f"❌ MQTT connection failed: {rc}")

def on_mqtt_message(client, userdata, msg):
    """Handle incoming rover position from background service"""
    global latest_position, position_history, last_update_time
    
    try:
        data = json.loads(msg.payload.decode())
        
        # Extract position from service message
        pos = data["position"]
        latest_position = [pos["x"], pos["y"], pos["z"]]
        
        # Add to history
        position_history.append(latest_position.copy())
        if len(position_history) > 100:
            position_history.pop(0)
        
        last_update_time = time.time()
        
        # Optional: auto-update visualization
        # update_position()  # Uncomment for automatic updates
        
    except Exception as e:
        print(f"❌ MQTT message error: {e}")

def update_position():
    """Update rover position - very fast since no camera processing!"""
    global latest_position, last_update_time
    
    if not latest_position:
        print("⚠️ No rover position received yet")
        return
    
    # Get model info for sizing
    active_source = GetActiveSource()
    if active_source:
        data_info = active_source.GetDataInformation()
        bounds = data_info.GetBounds()
        model_size = max(bounds[1] - bounds[0], bounds[5] - bounds[4])
        rover_size = 0.05
    else:
        rover_size = 0.05
    
    # Update visualization
    update_rover_geometry(latest_position, rover_size)
    
    # Force render
    view = GetActiveView()
    if view:
        view.StillRender()
    else:
        Render()
    
    age = time.time() - last_update_time if last_update_time > 0 else 0
    print(f"⚡ Fast update: [{latest_position[0]:.3f}, {latest_position[1]:.3f}, {latest_position[2]:.3f}] (age: {age:.2f}s)")

def set_rover_position(x, y, z):
    """Manually set rover position (bypasses MQTT)"""
    global latest_position
    
    latest_position = [x, y, z]
    
    active_source = GetActiveSource()
    if active_source:
        data_info = active_source.GetDataInformation()
        bounds = data_info.GetBounds()
        model_size = max(bounds[1] - bounds[0], bounds[5] - bounds[4])
        rover_size = model_size * 0.02
    else:
        rover_size = 0.05
    
    update_rover_geometry(latest_position, rover_size)
    
    view = GetActiveView()
    if view:
        view.StillRender()
    else:
        Render()
    
    print(f"🎯 Manual position: [{x:.3f}, {y:.3f}, {z:.3f}]")

def show_status():
    """Show tracking status and statistics"""
    global rover_source, rover_rep
    
    print("📊 Fast Tracking Status")
    print("=" * 30)
    
    if mqtt_client and mqtt_client.is_connected():
        print("📡 MQTT: Connected ✅")
    else:
        print("📡 MQTT: Disconnected ❌")
    
    print(f"📍 Latest position: {latest_position}")
    print(f"📈 Position history: {len(position_history)} points")
    
    if last_update_time > 0:
        age = time.time() - last_update_time
        print(f"⏰ Last update: {age:.2f}s ago")
    else:
        print("⏰ No updates received yet")
    
    # Check rover visualization
    print(f"🔴 Rover source: {'✅' if rover_source else '❌'}")
    print(f"🎨 Rover representation: {'✅' if rover_rep else '❌'}")
    
    if rover_source:
        try:
            rover_source.UpdatePipeline()
            data_info = rover_source.GetDataInformation()
            bounds = data_info.GetBounds()
            print(f"📦 Sphere bounds: X=[{bounds[0]:.3f}, {bounds[1]:.3f}], Y=[{bounds[2]:.3f}, {bounds[3]:.3f}], Z=[{bounds[4]:.3f}, {bounds[5]:.3f}]")
        except Exception as e:
            print(f"❌ Error getting sphere info: {e}")
    
    if rover_rep:
        try:
            visibility = rover_rep.Visibility
            print(f"👁️ Sphere visibility: {visibility}")
        except Exception as e:
            print(f"❌ Error getting visibility: {e}")

def force_sphere_visible():
    """Force the sphere to be visible and rendered"""
    global rover_source, rover_rep
    
    if rover_rep:
        rover_rep.Visibility = 1
        print("👁️ Set sphere visibility = 1")
    
    if rover_source:
        rover_source.Modified()
        rover_source.UpdatePipeline()
        print("🔄 Forced pipeline update")
    
    # Force full render
    view = GetActiveView()
    if view:
        view.StillRender()
        print("🖼️ Forced view render")
    else:
        Render()
        print("🖼️ Forced global render")
    
    print("✅ Forced sphere visibility update")

def cleanup():
    """Clean up MQTT connection"""
    global mqtt_client
    
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("🧹 MQTT connection closed")

# Auto-run setup message
print("⚡ Fast Falconia Rover Tracking Loaded!")
print("📋 Run: setup_fast_tracking()")
print("🚀 Remember to start: python rover_tracker_service.py")