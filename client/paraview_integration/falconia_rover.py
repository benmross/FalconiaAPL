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
import numpy as np

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
pixel_corners = None
model_coords = None

# Falconia model bounds (manually calibrated)
MODEL_X_RANGE = 2.5  # -1.25 to +1.25
MODEL_Z_RANGE = 3.6  # -1.8 to +1.8  
MODEL_Y_HOVER = 0.2  # Height above surface

def calculate_model_corners():
    """Calculate the 8 corners of the 3D model from ParaView pipeline"""
    
    print("📐 Calculating model corners from ParaView...")
    
    # Get the active source (should be your 3D model)
    active_source = GetActiveSource()
    if not active_source:
        print("❌ No active source found! Load your 3D model first.")
        return None
    
    # Update pipeline and get data info
    active_source.UpdatePipeline()
    data_info = active_source.GetDataInformation()
    bounds = data_info.GetBounds()
    
    # Extract bounding box: [x_min, x_max, y_min, y_max, z_min, z_max]
    x_min, x_max = bounds[0], bounds[1]
    y_min, y_max = bounds[2], bounds[3] 
    z_min, z_max = bounds[4], bounds[5]
    
    print(f"📦 Model bounds:")
    print(f"   X: [{x_min:.3f}, {x_max:.3f}]")
    print(f"   Y: [{y_min:.3f}, {y_max:.3f}]") 
    print(f"   Z: [{z_min:.3f}, {z_max:.3f}]")
    
    # Calculate 8 corners
    # Using your convention: top-left = (-X, -Z), top-right = (+X, -Z), etc.
    # Use Y coordinate of top surface for rover movement
    hover_y = y_max * 0.95  # Slightly below top surface
    
    corners = {
        # Top surface (where rover moves)
        "top_left": [x_min, hover_y, z_min],      # Tag 0: -X, -Z  
        "top_right": [x_max, hover_y, z_min],     # Tag 1: +X, -Z
        "bottom_right": [x_max, hover_y, z_max],  # Tag 2: +X, +Z
        "bottom_left": [x_min, hover_y, z_max],   # Tag 3: -X, +Z
        
        # Bottom surface (for reference)
        "bottom_top_left": [x_min, y_min, z_min],
        "bottom_top_right": [x_max, y_min, z_min], 
        "bottom_bottom_right": [x_max, y_min, z_max],
        "bottom_bottom_left": [x_min, y_min, z_max]
    }
    
    print("🎯 Calculated corners:")
    for name, coord in corners.items():
        if name.startswith("top_"):
            print(f"   {name}: [{coord[0]:.3f}, {coord[1]:.3f}, {coord[2]:.3f}]")
    
    return corners

def setup_coordinate_transform(model_corners):
    """Setup coordinate transformation from camera pixels to model coordinates"""
    global corners_data, pixel_to_model_matrix
    
    if not corners_data or not model_corners:
        return False
        
    print("🔗 Setting up coordinate transformation...")
    
    # Get pixel coordinates from calibration
    camera_corners = corners_data["corners"]
    
    # Map pixel corners to model corners
    # Support both old AprilTag format and new click format
    if "top_left" in camera_corners:
        # New click-based format
        pixel_points = [
            camera_corners["top_left"]["pixel"],      # Click 1 -> top_left  
            camera_corners["top_right"]["pixel"],     # Click 2 -> top_right
            camera_corners["bottom_right"]["pixel"],  # Click 3 -> bottom_right
            camera_corners["bottom_left"]["pixel"]    # Click 4 -> bottom_left
        ]
        print("📌 Using new click-based corner format")
    else:
        # Old AprilTag format (back_left, back_right, etc.)
        pixel_points = [
            camera_corners["back_left"]["pixel"],    # Tag 0 -> top_left  
            camera_corners["back_right"]["pixel"],   # Tag 1 -> top_right
            camera_corners["front_right"]["pixel"],  # Tag 2 -> bottom_right
            camera_corners["front_left"]["pixel"]    # Tag 3 -> bottom_left
        ]
        print("📌 Using old AprilTag corner format")
    
    # For XZ plane model, we need [x, z] coordinates 
    model_points = [
        [model_corners["top_left"][0], model_corners["top_left"][2]],      # [x, z]
        [model_corners["top_right"][0], model_corners["top_right"][2]],    # [x, z]
        [model_corners["bottom_right"][0], model_corners["bottom_right"][2]], # [x, z]
        [model_corners["bottom_left"][0], model_corners["bottom_left"][2]]     # [x, z]
    ]
    
    # Calculate homography transformation
    try:
        import numpy as np
        pixel_array = np.array(pixel_points, dtype=np.float32)
        model_array = np.array(model_points, dtype=np.float32)
        
        # Store for use in transformation
        global pixel_corners, model_coords
        pixel_corners = pixel_array
        model_coords = model_array
        
        print("✅ Coordinate transformation ready")
        print(f"   Pixel corners: {pixel_array.shape}")
        print(f"   Model corners: {model_array.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup transformation: {e}")
        return False

def setup_rover_tracking():
    """Initialize rover tracking system"""
    global corners_data
    
    print("🚀 Setting up Falconia Rover Tracking")
    print("=" * 45)
    
    # Load corner calibration - try multiple paths
    import os
    script_dir = "/home/benmross/Documents/Projects/FalconiaAPL/client/paraview_integration"
    corner_paths = [
        '/home/benmross/Documents/Projects/FalconiaAPL/client/paraview_integration/falconia_corners.json',  # Current directory
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
    
    # Calculate model corners from ParaView bounding box
    model_corners = calculate_model_corners()
    if not model_corners:
        print("❌ Failed to calculate model corners")
        return False
    
    # Create coordinate transformation
    setup_coordinate_transform(model_corners)
    
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
    """Convert pixel coordinates to model coordinates using homography transformation"""
    global pixel_corners, model_coords
    
    try:
        import numpy as np
        import cv2
        
        # Check if transformation is set up
        if 'pixel_corners' not in globals() or 'model_coords' not in globals():
            print("❌ Coordinate transformation not set up")
            return [0, 0, 0]
        
        # Calculate homography matrix
        homography_matrix = cv2.getPerspectiveTransform(pixel_corners, model_coords)
        
        # Transform the pixel point
        pixel_point = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)
        model_point = cv2.perspectiveTransform(pixel_point, homography_matrix)
        
        # Extract coordinates - homography gives us [x, z] for XZ plane
        model_x = float(model_point[0][0][0])  # X coordinate
        model_z = float(model_point[0][0][1])  # Z coordinate (from homography Y)
        
        # Get Y coordinate from model bounds (hover height)
        active_source = GetActiveSource()
        if active_source:
            data_info = active_source.GetDataInformation()
            bounds = data_info.GetBounds()
            model_y = bounds[3] * 0.95  # 95% of max Y (height above XZ plane)
        else:
            model_y = 0.2  # Default hover height
        
        print(f"🔧 Homography result: pixel({pixel_x:.1f}, {pixel_y:.1f}) → model({model_x:.3f}, {model_y:.3f}, {model_z:.3f})")
        return [model_x, model_y, model_z]
        
    except Exception as e:
        print(f"❌ Transformation error: {e}")
        return [0, 0, 0]

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