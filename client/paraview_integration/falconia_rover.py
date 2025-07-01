#!/usr/bin/env python3
"""
Falconia Rover Tracking for ParaView
Simple script to track rover position over 3D model.

USAGE IN PARAVIEW:
1. Load your Falconia 3D model
2. exec(open('falconia_rover.py').read())
3. setup_rover_tracking()
4. update_position() - Call repeatedly to update rover position
"""

from paraview.simple import *
import json
import cv2

try:
    import paho.mqtt.client as mqtt
    from pupil_apriltags import Detector
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False
    print("⚠️ Install paho-mqtt and pupil-apriltags for live tracking")

# Global variables
rover_source = None
rover_rep = None
trail_source = None  
trail_rep = None
mqtt_client = None
detector = None
camera_capture = None
latest_position = [0, 0, 0]
position_history = []
corners_data = None

# Falconia model bounds (manually calibrated)
MODEL_X_RANGE = 2.5  # -1.25 to +1.25
MODEL_Z_RANGE = 3.6  # -1.8 to +1.8  
MODEL_Y_HOVER = 0.2  # Height above surface

def setup_rover_tracking():
    """Initialize rover tracking system"""
    global corners_data
    
    print("🚀 Setting up Falconia Rover Tracking")
    print("=" * 45)
    
    # Load corner calibration - try multiple paths
    import os
    script_dir = "/home/benmross/Documents/Projects/FalconiaAPL/client/paraview_integration"
    corner_paths = [
        'falconia_corners.json',  # Current directory
        os.path.join(script_dir, 'falconia_corners.json'),  # Script directory
        os.path.expanduser('~/falconia_corners.json')  # Home directory
    ]
    
    corners_data = None
    for path in corner_paths:
        try:
            print(f"🔍 Checking: {path}")
            with open(path, 'r') as f:
                corners_data = json.load(f)
            print(f"✅ Loaded corner calibration from: {path}")
            break
        except FileNotFoundError:
            continue
    
    if not corners_data:
        print("❌ No corner calibration found!")
        print("   Searched paths:")
        for path in corner_paths:
            print(f"     {path}")
        print("   Run: python calibrate_corners.py")
        return False
    
    # Create rover visualization
    create_rover_sphere()
    
    # Setup tracking if available
    if TRACKING_AVAILABLE:
        setup_mqtt_tracking()
        setup_camera_tracking()
    
    print("✅ Rover tracking ready!")
    print("🔄 Run: update_position() to update rover")
    print("📍 Manual: set_rover_position(x, y, z)")
    return True

def create_rover_sphere():
    """Create red rover sphere using LiveProgrammableSource"""
    global rover_source, rover_rep
    
    rover_size = MODEL_X_RANGE * 0.02  # 2% of model width
    
    # Create dynamic rover sphere
    rover_source = LiveProgrammableSource()
    update_rover_geometry([0, MODEL_Y_HOVER, 0], rover_size)
    
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
        print(f"🔧 Updating sphere geometry to: [{x:.3f}, {y:.3f}, {z:.3f}]")
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
"""
        rover_source.Modified()
        rover_source.UpdatePipeline()  # This was missing!

def setup_mqtt_tracking():
    """Setup MQTT for rover position updates"""
    global mqtt_client
    
    if not TRACKING_AVAILABLE:
        return
        
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    
    try:
        mqtt_client.connect("localhost", 1883, 60)
        mqtt_client.loop_start()
        print("📡 MQTT tracking enabled")
    except:
        print("⚠️ MQTT not available")

def setup_camera_tracking():
    """Setup camera tracking"""
    global detector, camera_capture
    
    if not TRACKING_AVAILABLE or not corners_data:
        return
        
    detector = Detector(families='tag36h11')
    # Camera will be opened when needed
    print("📹 Camera tracking enabled")

def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    """MQTT connection callback"""
    if rc == 0:
        client.subscribe("rover/position")

def on_mqtt_message(client, userdata, msg):
    """Handle MQTT position updates"""
    global latest_position, position_history
    
    try:
        data = json.loads(msg.payload.decode())
        pos = data["position"]
        
        # Transform coordinates to model space
        latest_position = transform_to_model_coords(pos["x"], pos["y"], pos["z"])
        position_history.append(latest_position.copy())
        
        if len(position_history) > 100:
            position_history.pop(0)
            
    except Exception as e:
        print(f"❌ MQTT error: {e}")

def transform_to_model_coords(rover_x, rover_y, rover_z):
    """Transform rover coordinates to 3D model coordinates"""
    # Map rover space (0-2, 0-1.5) to model space (-1.25 to +1.25, -1.8 to +1.8)
    model_x = (rover_x - 1.0) * MODEL_X_RANGE / 2.0
    model_y = rover_z * 0.1 + MODEL_Y_HOVER  
    model_z = (rover_y - 0.75) * MODEL_Z_RANGE / 1.5
    
    return [model_x, model_y, model_z]

def get_camera_position():
    """Get rover position from camera using AprilTag detection"""
    global camera_capture, detector, corners_data
    
    if not TRACKING_AVAILABLE or not detector or not corners_data:
        print("⚠️ Camera tracking not available")
        return None
        
    # Always try to get a fresh frame - recreate camera connection each time
    camera_url = corners_data.get("camera_url", "http://192.168.0.11:7123/stream.mjpg")
    
    # Release old connection if it exists
    if camera_capture is not None:
        camera_capture.release()
    
    print(f"📹 Opening fresh camera connection: {camera_url}")
    camera_capture = cv2.VideoCapture(camera_url)
    
    if not camera_capture.isOpened():
        print("❌ Camera not opened")
        return None
        
    # Skip a few frames to get latest
    for i in range(3):
        ret, frame = camera_capture.read()
        if not ret:
            print(f"❌ Failed to capture frame {i+1}")
            return None
    
    print(f"✅ Captured fresh frame")
        
    # Detect rover AprilTag (tag ID 4)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detections = detector.detect(gray)
    
    print(f"🔍 Found {len(detections)} AprilTags")
    for detection in detections:
        print(f"   Tag {detection.tag_id} at {detection.center}")
        if detection.tag_id == 4:  # Rover tag
            # Convert pixel position to model coordinates using corner calibration
            pixel_pos = detection.center
            model_pos = pixel_to_model_coords(pixel_pos[0], pixel_pos[1])
            print(f"✅ Rover found! Pixel: {pixel_pos} → Model: {model_pos}")
            return model_pos
    
    print("❌ Rover tag (ID 4) not found")        
    return None

def pixel_to_model_coords(pixel_x, pixel_y):
    """Convert pixel coordinates to model coordinates using corner calibration"""
    if not corners_data:
        return [0, MODEL_Y_HOVER, 0]
    
    corners = corners_data["corners"]
    
    # Get corner pixel positions
    back_left = corners["back_left"]["pixel"]
    back_right = corners["back_right"]["pixel"] 
    front_right = corners["front_right"]["pixel"]
    front_left = corners["front_left"]["pixel"]
    
    # Simple bilinear interpolation
    # Normalize pixel position within the quadrilateral
    # This is a simplified version - for production use homography
    
    # For now, use a simple bounding box approach
    min_x = min(back_left[0], front_left[0])
    max_x = max(back_right[0], front_right[0])
    min_y = min(back_left[1], back_right[1])
    max_y = max(front_left[1], front_right[1])
    
    # Normalize to 0-1
    norm_x = (pixel_x - min_x) / (max_x - min_x) if max_x > min_x else 0.5
    norm_y = (pixel_y - min_y) / (max_y - min_y) if max_y > min_y else 0.5
    
    # Map to model coordinates  
    model_x = (norm_x - 0.5) * MODEL_X_RANGE
    model_z = (norm_y - 0.5) * MODEL_Z_RANGE
    model_y = MODEL_Y_HOVER
    
    return [model_x, model_y, model_z]

def update_position():
    """Update rover position - call this repeatedly"""
    global latest_position
    
    # Try to get new position from camera
    camera_pos = get_camera_position()
    if camera_pos:
        latest_position = camera_pos
        
    # Update visualization
    rover_size = MODEL_X_RANGE * 0.02
    update_rover_geometry(latest_position, rover_size)
    
    # Force render
    view = GetActiveView()
    if view:
        view.StillRender()
    else:
        Render()
        
    print(f"📍 Rover: [{latest_position[0]:.3f}, {latest_position[1]:.3f}, {latest_position[2]:.3f}]")

def set_rover_position(x, y, z):
    """Manually set rover position"""
    global latest_position
    
    latest_position = [x, y, z]
    rover_size = MODEL_X_RANGE * 0.02
    update_rover_geometry(latest_position, rover_size)
    
    view = GetActiveView()
    if view:
        view.StillRender()
    else:
        Render()
        
    print(f"🎯 Set rover to: [{x:.3f}, {y:.3f}, {z:.3f}]")

def test_corners():
    """Test rover at all 4 corners"""
    corners = [
        [-1.25, MODEL_Y_HOVER, -1.8],  # Back-left
        [1.25, MODEL_Y_HOVER, -1.8],   # Back-right  
        [1.25, MODEL_Y_HOVER, 1.8],    # Front-right
        [-1.25, MODEL_Y_HOVER, 1.8]    # Front-left
    ]
    
    for i, (x, y, z) in enumerate(corners):
        set_rover_position(x, y, z)
        input(f"Corner {i+1}/4: [{x}, {y}, {z}] - Press Enter for next...")

def test_camera():
    """Test camera detection without updating position"""
    global camera_capture, detector, corners_data
    
    if not TRACKING_AVAILABLE:
        print("❌ Camera tracking not available - install pupil-apriltags and opencv-python")
        return
        
    if not corners_data:
        print("❌ No corner calibration - run setup_rover_tracking() first")
        return
        
    if detector is None:
        detector = Detector(families='tag36h11')
        print("✅ Detector initialized")
        
    print("🧪 Testing camera detection...")
    print("   Looking for AprilTag ID 4 (rover)")
    print("   Camera will capture one frame and show results")
    
    # Get position without updating rover
    pos = get_camera_position()
    
    if pos:
        print(f"🎯 Detected rover at: [{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}]")
        print("   ✅ Camera detection working!")
    else:
        print("❌ No rover detected")
        print("   Check:")
        print("   1. AprilTag ID 4 is visible to camera")
        print("   2. Camera URL is correct")
        print("   3. Lighting is adequate")
        print("   4. Tag is not occluded")

def update_position_now():
    """Detect rover and immediately update position with full debugging"""
    global latest_position, detector
    
    print("🔄 Updating rover position...")
    
    # Ensure detector is initialized
    if detector is None:
        detector = Detector(families='tag36h11')
        print("✅ Detector initialized")
    
    # Get current camera position
    camera_pos = get_camera_position()
    
    if camera_pos:
        print(f"📍 New position detected: [{camera_pos[0]:.3f}, {camera_pos[1]:.3f}, {camera_pos[2]:.3f}]")
        latest_position = camera_pos
        
        # Update visualization immediately
        rover_size = MODEL_X_RANGE * 0.02
        update_rover_geometry(latest_position, rover_size)
        
        # Force render
        view = GetActiveView()
        if view:
            view.StillRender()
        else:
            Render()
            
        print(f"✅ Rover updated to: [{latest_position[0]:.3f}, {latest_position[1]:.3f}, {latest_position[2]:.3f}]")
    else:
        print("❌ No rover position detected - rover sphere stays at current position")
        print(f"   Current position: [{latest_position[0]:.3f}, {latest_position[1]:.3f}, {latest_position[2]:.3f}]")

def cleanup():
    """Clean up resources"""
    global mqtt_client, camera_capture
    
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        
    if camera_capture:
        camera_capture.release()
        
    print("🧹 Cleanup complete")

# Auto-run setup message
print("🌍 Falconia Rover Tracking Loaded!")
print("📋 Run: setup_rover_tracking()")