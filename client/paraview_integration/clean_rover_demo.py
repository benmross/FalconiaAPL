#!/usr/bin/env python3
"""
Clean Rover Demo - Using manually calibrated corners
Simple and reliable rover tracking for presentation
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

# Model configuration - manually calibrated
MODEL_X_RANGE = 2.5  # -1.25 to +1.25
MODEL_Z_RANGE = 3.6  # -1.8 to +1.8
MODEL_Y_HOVER = 0.2  # Hover height above surface

def create_rover_visualization():
    """Create rover and trail visualization using LiveProgrammableSource"""
    global rover_source, rover_rep, trail_source, trail_rep
    
    print("Creating rover visualization...")
    
    # Calculate rover size
    rover_size = MODEL_X_RANGE * 0.02  # 2% of model width
    
    # Create LiveProgrammableSource for dynamic rover sphere
    rover_source = LiveProgrammableSource()
    
    # Initial script with default position
    update_rover_script([0.0, MODEL_Y_HOVER, 0.0], rover_size)
    
    # Show rover
    rover_rep = Show(rover_source)
    rover_rep.DiffuseColor = [1.0, 0.0, 0.0]  # Bright red
    rover_rep.Opacity = 1.0
    rover_rep.Specular = 0.8
    
    # Create trail visualization
    create_trail_visualization()
    
    Render()
    print(f"✅ Rover created! Size: {rover_size:.3f}")

def update_rover_script(position, rover_size):
    """Update the LiveProgrammableSource script with new position"""
    global rover_source
    
    if rover_source:
        x, y, z = position
        print(f"🔧 Updating rover script: position=[{x:.3f}, {y:.3f}, {z:.3f}], size={rover_size:.3f}")
        
        rover_source.Script = f"""
import vtk

# Create sphere at current rover position
sphere = vtk.vtkSphereSource()
sphere.SetCenter({x}, {y}, {z})
sphere.SetRadius({rover_size})
sphere.SetPhiResolution(20)
sphere.SetThetaResolution(20)
sphere.Update()

# Set the output
output = self.GetOutput()
output.ShallowCopy(sphere.GetOutput())

# Debug output
print(f"VTK Script executed: sphere at [{x}, {y}, {z}] with radius {rover_size}")
"""
        rover_source.Modified()
        print(f"✅ Script updated and Modified() called")
    
def create_trail_visualization():
    """Create trail visualization using LiveProgrammableSource"""
    global trail_source, trail_rep
    
    # Create trail using LiveProgrammableSource
    trail_source = LiveProgrammableSource()
    trail_source.Script = """
import vtk
polydata = vtk.vtkPolyData()
points = vtk.vtkPoints()
points.InsertNextPoint(0, 0, 0)
polydata.SetPoints(points)
self.GetOutput().ShallowCopy(polydata)
"""
    
    # Show trail
    trail_rep = Show(trail_source)
    trail_rep.DiffuseColor = [1.0, 0.5, 0.0]  # Orange
    trail_rep.Opacity = 0.8
    trail_rep.LineWidth = 3.0

def setup_mqtt():
    """Setup MQTT connection with threaded client"""
    global mqtt_client
    
    if not MQTT_AVAILABLE:
        print("⚠️ MQTT not available")
        return False
        
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    
    try:
        print("🔗 Connecting to MQTT broker...")
        mqtt_client.connect("localhost", 1883, 60)
        print("🔄 Starting MQTT loop in background thread...")
        mqtt_client.loop_start()  # This runs in a separate thread
        print("✅ MQTT connected")
        return True
    except Exception as e:
        print(f"❌ MQTT failed: {e}")
        return False

def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    """MQTT connection callback"""
    if rc == 0:
        print("✅ Connected to MQTT broker")
        result = client.subscribe("rover/position")
        print(f"📡 Subscribed to rover/position: {result}")
    else:
        print(f"❌ MQTT connection failed: {rc}")

def on_mqtt_message(client, userdata, msg):
    """Handle MQTT position updates with proper scaling"""
    global latest_position, position_history
    
    print(f"📨 MQTT message received on topic: {msg.topic}")
    
    try:
        data = json.loads(msg.payload.decode())
        pos = data["position"]
        
        print(f"🔍 Raw rover position: [{pos['x']:.3f}, {pos['y']:.3f}, {pos['z']:.3f}]")
        
        # Map rover coordinates (0-2, 0-1.5) to model coordinates (-1.25 to +1.25, -1.8 to +1.8)
        # Rover X,Y → Model X,Z (surface), Rover Z → Model Y (height)
        latest_position = [
            (pos["x"] - 1.0) * MODEL_X_RANGE / 2.0,  # Rover X → Model X: 0-2 becomes -1.25 to +1.25
            pos["z"] * 0.1 + MODEL_Y_HOVER,          # Rover Z → Model Y: hover above surface
            (pos["y"] - 0.75) * MODEL_Z_RANGE / 1.5  # Rover Y → Model Z: 0-1.5 becomes -1.8 to +1.8
        ]
        
        print(f"🎯 Mapped to model: [{latest_position[0]:.3f}, {latest_position[1]:.3f}, {latest_position[2]:.3f}]")
        
        # Add to trail
        position_history.append(latest_position.copy())
        if len(position_history) > 100:
            position_history.pop(0)
            
    except Exception as e:
        print(f"❌ Error parsing MQTT: {e}")
        print(f"   Raw payload: {msg.payload.decode()}")

def update_visualization():
    """Update rover and trail positions"""
    global rover_source, trail_source, latest_position, position_history
    
    # Update rover position using LiveProgrammableSource
    if rover_source:
        try:
            # Calculate rover size
            rover_size = MODEL_X_RANGE * 0.02
            
            # Update the script with new position
            update_rover_script(latest_position, rover_size)
            print(f"🔧 Updated rover script with position: {latest_position}")
            
            # Force pipeline update
            rover_source.UpdatePipeline()
            
        except Exception as e:
            print(f"❌ Error updating rover position: {e}")
        
    # Update trail
    if trail_source and len(position_history) > 1:
        trail_script = f"""
import vtk
polydata = vtk.vtkPolyData()
points = vtk.vtkPoints()
lines = vtk.vtkCellArray()

trail_points = {position_history}
for point in trail_points:
    points.InsertNextPoint(point[0], point[1], point[2])

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
        trail_source.UpdatePipeline()
    
    # Force render view update
    view = GetActiveView()
    if view:
        view.StillRender()
    else:
        Render()

def auto_update():
    """Auto-update function for live tracking"""
    global last_update, demo_active
    
    current_time = time.time()
    
    # MQTT messages are processed automatically in background thread
    # No need to call loop() since we use loop_start()
    
    # Update visualization every 100ms
    if current_time - last_update > 0.1:
        update_visualization()
        last_update = current_time
        
    return demo_active

def test_mqtt_simple():
    """Simple MQTT test function"""
    global mqtt_client
    
    if mqtt_client:
        print(f"🔍 MQTT client connected: {mqtt_client.is_connected()}")
        print(f"📊 Position history length: {len(position_history)}")
        print(f"📍 Latest position: {latest_position}")
    else:
        print("❌ No MQTT client available")

def send_test_position():
    """Send a test position manually"""
    global latest_position, position_history
    
    # Simulate receiving an MQTT message directly
    test_pos = {"x": 1.0, "y": 0.75, "z": 0.1}
    
    print(f"🧪 Sending test position: {test_pos}")
    
    # Apply the same coordinate transformation
    latest_position = [
        (test_pos["x"] - 1.0) * MODEL_X_RANGE / 2.0,  # Should be 0.0
        test_pos["z"] * 0.1 + MODEL_Y_HOVER,          # Should be 0.21
        (test_pos["y"] - 0.75) * MODEL_Z_RANGE / 1.5  # Should be 0.0
    ]
    
    print(f"🎯 Mapped position: {latest_position}")
    
    position_history.append(latest_position.copy())
    update_visualization()
    
    # Wait a moment then check the actual sphere position
    import time
    time.sleep(0.1)
    check_actual_sphere_position()
    
    print("✅ Test position sent and visualization updated")

def check_actual_sphere_position():
    """Check what the actual sphere position is in the pipeline"""
    global rover_source
    
    if rover_source:
        print("🔍 Checking actual sphere position...")
        try:
            rover_source.UpdatePipeline()
            # Get data information instead of direct output
            data_info = rover_source.GetDataInformation()
            if data_info:
                bounds = data_info.GetBounds()
                center_x = (bounds[0] + bounds[1]) / 2
                center_y = (bounds[2] + bounds[3]) / 2  
                center_z = (bounds[4] + bounds[5]) / 2
                print(f"📍 Actual sphere center: [{center_x:.3f}, {center_y:.3f}, {center_z:.3f}]")
                print(f"📦 Sphere bounds: X=[{bounds[0]:.3f}, {bounds[1]:.3f}], Y=[{bounds[2]:.3f}, {bounds[3]:.3f}], Z=[{bounds[4]:.3f}, {bounds[5]:.3f}]")
            else:
                print("❌ No data information from rover source")
        except Exception as e:
            print(f"❌ Error checking sphere position: {e}")

def test_simple_movement():
    """Test moving to a very obvious position"""
    global latest_position, position_history
    
    print("🧪 Testing simple movement to [1.0, 0.5, 1.0]...")
    
    latest_position = [1.0, 0.5, 1.0]  # Very obvious position
    position_history.append(latest_position.copy())
    update_visualization()
    
    import time
    time.sleep(0.2)
    check_actual_sphere_position()
    
    print("✅ Simple movement test complete")

def get_calibrated_corners():
    """Get the 4 calibrated corner positions"""
    
    corners = [
        [-1.25, MODEL_Y_HOVER, -1.8],  # Back-Left
        [1.25, MODEL_Y_HOVER, -1.8],   # Back-Right
        [1.25, MODEL_Y_HOVER, 1.8],    # Front-Right
        [-1.25, MODEL_Y_HOVER, 1.8],   # Front-Left
        [0, MODEL_Y_HOVER, 0]          # Center
    ]
    
    corner_names = ["Back-Left", "Back-Right", "Front-Right", "Front-Left", "Center"]
    
    print("\n🎯 CALIBRATED CORNERS:")
    print("=" * 50)
    for name, corner in zip(corner_names, corners):
        print(f"{name}: X={corner[0]:.3f}, Y={corner[1]:.3f}, Z={corner[2]:.3f}")
    print("=" * 50)
    
    # Store for testing
    globals()['test_corners'] = corners
    globals()['test_corner_names'] = corner_names
    globals()['test_corner_index'] = 0
    
    return corners

def move_to_next_corner():
    """Move to the next corner in sequence"""
    global latest_position
    
    if 'test_corners' not in globals():
        print("❌ Run get_calibrated_corners() first!")
        return
        
    corners = globals()['test_corners']
    names = globals()['test_corner_names']
    index = globals()['test_corner_index']
    
    if index >= len(corners):
        print("✅ All corners visited! Starting over...")
        index = 0
        globals()['test_corner_index'] = 0
    
    corner = corners[index]
    name = names[index]
    
    latest_position = corner
    print(f"Moving to {name}: [{corner[0]:.3f}, {corner[1]:.3f}, {corner[2]:.3f}]")
    update_visualization()
    
    globals()['test_corner_index'] = index + 1

def clear_trail():
    """Clear the trail"""
    global position_history, trail_source
    
    position_history = []
    
    if trail_source:
        trail_source.Script = """
import vtk
polydata = vtk.vtkPolyData()
points = vtk.vtkPoints()
points.InsertNextPoint(0, 0, 0)
polydata.SetPoints(points)
self.GetOutput().ShallowCopy(polydata)
"""
        trail_source.Modified()
        Render()
        print("🧹 Trail cleared!")

def start_demo():
    """Start the complete demo"""
    global demo_active
    
    print("🚀 Starting Clean Rover Demo")
    print("=" * 40)
    
    # Create visualization
    create_rover_visualization()
    
    # Setup MQTT
    setup_mqtt()
    
    # Get calibrated corners
    get_calibrated_corners()
    
    demo_active = True
    print("✅ Demo ready!")
    print("🔄 Run: while auto_update(): pass")
    print("📍 Test corners: move_to_next_corner()")

def stop_demo():
    """Stop the demo"""
    global demo_active, mqtt_client
    
    demo_active = False
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    print("🛑 Demo stopped")

# Initialize
print("🌍 Clean Falconia Rover Demo!")
print("=" * 40)
print("USAGE:")
print("1. Load your Falconia 3D model")
print("2. start_demo()")
print("3. move_to_next_corner() - Test corners")
print("4. while auto_update(): pass - Live tracking")
print("=" * 40)