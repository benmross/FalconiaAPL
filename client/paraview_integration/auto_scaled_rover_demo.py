#!/usr/bin/env python3
"""
Auto-Scaled Rover Demo - Automatically scales to your 3D model
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
model_bounds = None
coordinate_offset = [0, 0, 0]
coordinate_scale = [1, 1, 1]

def detect_model_scale():
    """Automatically detect the scale of the loaded 3D model (XZ plane oriented)"""
    global model_bounds, coordinate_offset, coordinate_scale
    
    # Get all sources and look for Clip4 specifically
    sources = GetSources()
    
    if not sources:
        print("⚠️ No 3D model loaded! Using default scale.")
        return False
    
    # Try to find Clip6 first, otherwise use first source
    clip6_source = None
    for name, source in sources.items():
        if 'Clip6' in str(name) or 'clip6' in str(name).lower():
            clip6_source = source
            print(f"✅ Found Clip6: {name}")
            break
    
    if clip6_source:
        main_source = clip6_source
    else:
        main_source = list(sources.values())[0]
        print("⚠️ Clip6 not found, using first source")
        
    bounds = main_source.GetDataInformation().GetBounds()
    model_bounds = bounds
    
    print(f"🌍 Detected model bounds:")
    print(f"   X: {bounds[0]:.2f} to {bounds[1]:.2f} (width)")
    print(f"   Y: {bounds[2]:.2f} to {bounds[3]:.2f} (height - small)")
    print(f"   Z: {bounds[4]:.2f} to {bounds[5]:.2f} (depth)")
    
    # For XZ plane model: X and Z are the main surface, Y is height
    model_x_width = bounds[1] - bounds[0]  # X dimension
    model_z_depth = bounds[5] - bounds[4]  # Z dimension  
    model_y_height = bounds[3] - bounds[2] # Y dimension (small)
    
    # Rover coordinates: map rover X,Y to model X,Z
    rover_x_range = 2.0  # Rover X maps to model X
    rover_y_range = 1.5  # Rover Y maps to model Z
    
    # Calculate scale and offset for XZ plane mapping
    coordinate_scale = [
        model_x_width / rover_x_range,   # Rover X → Model X
        model_z_depth / rover_y_range,   # Rover Y → Model Z  
        model_y_height * 0.1             # Rover Z → Model Y (small hover)
    ]
    
    coordinate_offset = [
        bounds[0],                       # Start at model X min
        bounds[4],                       # Start at model Z min
        bounds[3] + model_y_height * 0.1 # Hover above model Y max
    ]
    
    print(f"🎯 XZ-plane mapping:")
    print(f"   Rover X → Model X: scale {coordinate_scale[0]:.2f}, offset {coordinate_offset[0]:.2f}")
    print(f"   Rover Y → Model Z: scale {coordinate_scale[1]:.2f}, offset {coordinate_offset[1]:.2f}")
    print(f"   Rover Z → Model Y: scale {coordinate_scale[2]:.2f}, offset {coordinate_offset[2]:.2f}")
    
    return True

def create_rover_visualization():
    """Create rover and trail visualization"""
    global rover_source, rover_rep, trail_source, trail_rep
    
    print("Creating rover visualization...")
    
    # Auto-detect model scale
    if not detect_model_scale():
        print("⚠️ Using default scaling")
    
    # Calculate rover size based on model scale
    model_width = abs(coordinate_scale[0]) * 2.0  # Model width
    rover_size = model_width * 0.02  # 2% of model width
    
    # Create rover sphere
    rover_source = Sphere()
    rover_source.Radius = rover_size
    rover_source.Center = [coordinate_offset[0], coordinate_offset[1], coordinate_offset[2]]
    
    # Show rover
    rover_rep = Show(rover_source)
    rover_rep.DiffuseColor = [1.0, 0.0, 0.0]  # Bright red
    rover_rep.Opacity = 1.0
    rover_rep.Specular = 0.8
    
    # Create trail
    trail_source = ProgrammableSource()
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
    
    Render()
    print(f"✅ Rover created! Size: {rover_size:.3f}")

def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    """MQTT connection callback"""
    if rc == 0:
        print("✅ Connected to MQTT broker")
        client.subscribe("rover/position")
    else:
        print(f"❌ MQTT connection failed: {rc}")

def on_mqtt_message(client, userdata, msg):
    """Handle MQTT position updates with XZ-plane mapping"""
    global latest_position, position_history
    
    try:
        data = json.loads(msg.payload.decode())
        pos = data["position"]
        
        # Map rover coordinates to XZ-plane model:
        # Rover X,Y → Model X,Z (surface), Rover Z → Model Y (height)
        latest_position = [
            pos["x"] * coordinate_scale[0] + coordinate_offset[0],  # Rover X → Model X
            pos["z"] * coordinate_scale[2] + coordinate_offset[2],  # Rover Z → Model Y (height)
            pos["y"] * coordinate_scale[1] + coordinate_offset[1]   # Rover Y → Model Z
        ]
        
        # Add to trail
        position_history.append(latest_position.copy())
        if len(position_history) > 100:
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
    
    Render()

def auto_update():
    """Auto-update function"""
    global last_update, demo_active
    
    current_time = time.time()
    
    # Process MQTT messages
    if mqtt_client:
        for _ in range(10):
            mqtt_client.loop(timeout=0.001)
    
    # Update visualization every 100ms
    if current_time - last_update > 0.1:
        update_visualization()
        last_update = current_time
        
    return demo_active

def start_demo():
    """Start the auto-scaled demo"""
    global demo_active
    
    print("🚀 Starting Auto-Scaled Rover Demo")
    print("=" * 40)
    
    # Create visualization (auto-detects scale)
    create_rover_visualization()
    
    # Setup MQTT
    setup_mqtt()
    
    demo_active = True
    print("✅ Demo ready! Rover will move over your 3D model")
    print("🔄 Run: while auto_update(): pass")

def stop_demo():
    """Stop the demo"""
    global demo_active, mqtt_client
    demo_active = False
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    print("🛑 Demo stopped")

def test_random_movement():
    """Test by randomly moving the rover around the model"""
    global latest_position
    import random
    
    if not model_bounds:
        print("❌ No model detected! Load your 3D model first.")
        return
        
    print("🎲 Testing random rover movement...")
    
    # Get model bounds
    x_min, x_max = model_bounds[0], model_bounds[1]
    y_min, y_max = model_bounds[2], model_bounds[3]
    z_max = model_bounds[5]
    
    for i in range(20):
        # Random position within model bounds
        latest_position = [
            random.uniform(x_min, x_max),
            random.uniform(y_min, y_max), 
            z_max + abs(coordinate_scale[2])  # Hover above
        ]
        
        print(f"Random position {i+1}: [{latest_position[0]:.2f}, {latest_position[1]:.2f}, {latest_position[2]:.2f}]")
        update_visualization()
        
        # Small delay to see movement
        import time
        time.sleep(0.3)
    
    print("✅ Random movement test complete!")

def test_corner_movement():
    """Test by moving rover to each corner of the XZ-plane model"""
    global latest_position
    
    if not model_bounds:
        print("❌ No model detected! Load your 3D model first.")
        return
        
    print("📍 Testing corner movement on XZ-plane...")
    print("Call move_to_next_corner() repeatedly to step through corners")
    
    bounds = model_bounds
    # For XZ-plane model: hover above Y max
    hover_height = bounds[3] + abs(coordinate_scale[2])
    
    # Define corners in XZ plane (Y is up)
    corners = [
        [bounds[0], hover_height, bounds[4]],  # X-min, Z-min (back-left)
        [bounds[1], hover_height, bounds[4]],  # X-max, Z-min (back-right)  
        [bounds[1], hover_height, bounds[5]],  # X-max, Z-max (front-right)
        [bounds[0], hover_height, bounds[5]],  # X-min, Z-max (front-left)
        [(bounds[0]+bounds[1])/2, hover_height, (bounds[4]+bounds[5])/2]  # Center
    ]
    
    corner_names = ["Back-Left", "Back-Right", "Front-Right", "Front-Left", "Center"]
    
    # Store globally for interactive use
    globals()['test_corners'] = corners
    globals()['test_corner_names'] = corner_names
    globals()['test_corner_index'] = 0
    
    print("XZ-plane corners defined (Y is up):")
    for i, (name, corner) in enumerate(zip(corner_names, corners)):
        print(f"  {name}: X={corner[0]:.1f}, Y={corner[1]:.1f}, Z={corner[2]:.1f}")
    print("Ready! Call move_to_next_corner() to move step by step")

def move_to_next_corner():
    """Move to the next corner in the test sequence"""
    global latest_position
    
    if 'test_corners' not in globals():
        print("❌ Run test_corner_movement() first!")
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
    print(f"Moving to {name}: [{corner[0]:.2f}, {corner[1]:.2f}, {corner[2]:.2f}]")
    update_visualization()
    
    globals()['test_corner_index'] = index + 1

def clear_trail():
    """Clear the orange trail"""
    global position_history, trail_source
    
    position_history = []
    
    if trail_source:
        # Reset trail to empty
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

def disable_trail():
    """Disable trail creation entirely"""
    global trail_rep
    
    if trail_rep:
        Hide(trail_rep)
        Render()
        print("👻 Trail hidden!")

def enable_trail():
    """Re-enable trail visibility"""
    global trail_rep
    
    if trail_rep:
        Show(trail_rep)
        Render()
        print("🟠 Trail visible!")

def debug_clip_planes():
    """Debug clip planes to understand their actual effect"""
    sources = GetSources()
    
    print("🔍 DEBUGGING CLIP PLANES:")
    print("=" * 50)
    
    for name, source in sources.items():
        name_str = str(name)
        if 'clip' in name_str.lower():
            try:
                if hasattr(source, 'ClipType'):
                    clip_type = source.ClipType
                    if hasattr(clip_type, 'Origin') and hasattr(clip_type, 'Normal'):
                        origin = list(clip_type.Origin)
                        normal = list(clip_type.Normal)
                        
                        # Check if "Invert" or "Inside Out" is enabled
                        invert = False
                        if hasattr(source, 'Invert'):
                            invert = source.Invert
                        elif hasattr(source, 'InsideOut'):
                            invert = source.InsideOut
                        
                        print(f"📎 {name_str}:")
                        print(f"   Origin: [{origin[0]:.3f}, {origin[1]:.3f}, {origin[2]:.3f}]")
                        print(f"   Normal: [{normal[0]:.3f}, {normal[1]:.3f}, {normal[2]:.3f}]")
                        print(f"   Invert: {invert}")
                        
                        # Get bounds of this specific clip
                        clip_bounds = source.GetDataInformation().GetBounds()
                        print(f"   Result bounds: X=[{clip_bounds[0]:.2f}, {clip_bounds[1]:.2f}], Z=[{clip_bounds[4]:.2f}, {clip_bounds[5]:.2f}]")
                        
                        # Interpret what this clip does
                        if abs(normal[0]) > 0.9:  # X-direction
                            direction = "X-direction"
                            keeps = "X < " if not invert else "X > "
                            keeps += f"{origin[0]:.3f}"
                        elif abs(normal[2]) > 0.9:  # Z-direction
                            direction = "Z-direction"
                            keeps = "Z < " if not invert else "Z > "
                            keeps += f"{origin[2]:.3f}"
                        else:
                            direction = "Other"
                            keeps = "Unknown"
                            
                        print(f"   Effect: {direction} clip, keeps region where {keeps}")
                        print()
                        
            except Exception as e:
                print(f"   Error: {e}")

def use_precise_clip_bounds():
    """Use precise clip plane intersections - improved logic"""
    global model_bounds, coordinate_offset, coordinate_scale
    
    print("🎯 Calculating precise bounds from clip planes...")
    
    # First debug the clips
    debug_clip_planes()
    
    # Get Clip6 bounds as the actual result
    sources = GetSources()
    clip6_bounds = None
    
    for name, source in sources.items():
        if 'Clip6' in str(name) or 'clip6' in str(name).lower():
            clip6_bounds = source.GetDataInformation().GetBounds()
            print(f"✅ Using Clip6 actual bounds: {clip6_bounds}")
            break
    
    if clip6_bounds is None:
        print("❌ Could not find Clip6!")
        return False
    
    # Use the actual Clip6 bounds directly
    model_bounds = clip6_bounds
    
    x_min, x_max = clip6_bounds[0], clip6_bounds[1]
    y_min, y_max = clip6_bounds[2], clip6_bounds[3] 
    z_min, z_max = clip6_bounds[4], clip6_bounds[5]
    
    # Recalculate scaling with actual bounds
    model_x_width = x_max - x_min
    model_z_depth = z_max - z_min
    model_y_height = y_max - y_min
    
    rover_x_range = 2.0
    rover_y_range = 1.5
    
    coordinate_scale = [
        model_x_width / rover_x_range,
        model_z_depth / rover_y_range,
        model_y_height * 0.1
    ]
    
    coordinate_offset = [
        x_min,
        z_min,
        y_max + model_y_height * 0.05
    ]
    
    print("✅ Using ACTUAL Clip6 bounds!")
    print(f"   X: {x_min:.3f} to {x_max:.3f} (width: {model_x_width:.3f})")
    print(f"   Z: {z_min:.3f} to {z_max:.3f} (depth: {model_z_depth:.3f})")
    print(f"   Y: {y_min:.3f} to {y_max:.3f} (height: {model_y_height:.3f})")
    print(f"   Scale: [{coordinate_scale[0]:.3f}, {coordinate_scale[1]:.3f}, {coordinate_scale[2]:.3f}]")
    print(f"   Offset: [{coordinate_offset[0]:.3f}, {coordinate_offset[1]:.3f}, {coordinate_offset[2]:.3f}]")
    
    return True

def use_geometry_corners():
    """Extract actual corner points from the rotated geometry"""
    global model_bounds, coordinate_offset, coordinate_scale
    
    print("🔄 Extracting actual geometry corners...")
    
    # Find Clip6
    sources = GetSources()
    clip6_source = None
    
    for name, source in sources.items():
        if 'Clip6' in str(name) or 'clip6' in str(name).lower():
            clip6_source = source
            break
    
    if not clip6_source:
        print("❌ Could not find Clip6!")
        return False
    
    # Update pipeline to get fresh data
    clip6_source.UpdatePipeline()
    
    # Get the actual geometry using ParaView's data interface
    try:
        # Use ParaView's servermanager to get the data
        import paraview.servermanager as sm
        
        # Get data information
        data_info = clip6_source.GetDataInformation()
        bounds = data_info.GetBounds()
        
        print(f"📊 Using ParaView data bounds directly")
        print(f"   Raw bounds: {bounds}")
        
        # Extract bounds
        x_min, x_max = bounds[0], bounds[1]
        y_min, y_max = bounds[2], bounds[3]
        z_min, z_max = bounds[4], bounds[5]
        
        print(f"📏 Actual geometry bounds:")
        print(f"   X: {x_min:.3f} to {x_max:.3f}")
        print(f"   Y: {y_min:.3f} to {y_max:.3f}")
        print(f"   Z: {z_min:.3f} to {z_max:.3f}")
        
        # Update model bounds
        model_bounds = [x_min, x_max, y_min, y_max, z_min, z_max]
        
        # Recalculate scaling
        model_x_width = x_max - x_min
        model_z_depth = z_max - z_min
        model_y_height = y_max - y_min
        
        rover_x_range = 2.0
        rover_y_range = 1.5
        
        coordinate_scale = [
            model_x_width / rover_x_range,
            model_z_depth / rover_y_range,
            model_y_height * 0.1
        ]
        
        coordinate_offset = [
            x_min,
            z_min,
            y_max + model_y_height * 0.05
        ]
        
        print("✅ Updated with actual geometry bounds!")
        print(f"   Scale: [{coordinate_scale[0]:.3f}, {coordinate_scale[1]:.3f}, {coordinate_scale[2]:.3f}]")
        print(f"   Offset: [{coordinate_offset[0]:.3f}, {coordinate_offset[1]:.3f}, {coordinate_offset[2]:.3f}]")
        
        return True
        
    except Exception as e:
        print(f"❌ Error extracting geometry: {e}")
        return False

def find_actual_corners_simple():
    """Simple method to find actual corners by sampling edge points"""
    global model_bounds, coordinate_offset, coordinate_scale
    
    print("🔍 Finding actual corner points...")
    
    # Find Clip4
    sources = GetSources()
    clip4_source = None
    
    for name, source in sources.items():
        if 'Clip4' in str(name) or 'clip4' in str(name).lower():
            clip4_source = source
            break
    
    if not clip4_source:
        print("❌ Could not find Clip4!")
        return False
    
    # Create a probe to sample points around the perimeter
    bounds = clip6_source.GetDataInformation().GetBounds()
    x_min, x_max = bounds[0], bounds[1]
    y_min, y_max = bounds[2], bounds[3]
    z_min, z_max = bounds[4], bounds[5]
    
    print(f"📦 Bounding box: X=[{x_min:.2f}, {x_max:.2f}], Z=[{z_min:.2f}, {z_max:.2f}]")
    
    # Sample many points around the perimeter to find actual edges
    sample_points = []
    num_samples = 20
    
    # Sample along each edge of the bounding box
    for i in range(num_samples):
        t = i / (num_samples - 1)
        
        # Top edge (Z = z_max)
        sample_points.append([x_min + t * (x_max - x_min), (y_min + y_max) / 2, z_max])
        # Bottom edge (Z = z_min)  
        sample_points.append([x_min + t * (x_max - x_min), (y_min + y_max) / 2, z_min])
        # Left edge (X = x_min)
        sample_points.append([x_min, (y_min + y_max) / 2, z_min + t * (z_max - z_min)])
        # Right edge (X = x_max)
        sample_points.append([x_max, (y_min + y_max) / 2, z_min + t * (z_max - z_min)])
    
    # Create a probe filter to test which points are actually inside the geometry
    from paraview.simple import ProbeLocation
    
    valid_points = []
    hover_height = y_max + (y_max - y_min) * 0.05
    
    for point in sample_points:
        try:
            # Probe at this location
            probe = ProbeLocation(Input=clip6_source, ProbeType='Fixed Radius Point Source')
            probe.ProbeType.Center = point
            probe.ProbeType.Radius = 0.01
            probe.UpdatePipeline()
            
            # Check if the probe found valid data (point is inside geometry)
            probe_data = probe.GetDataInformation()
            if probe_data.GetNumberOfPoints() > 0:
                # This point is near the actual geometry
                valid_points.append([point[0], hover_height, point[2]])
            
            Delete(probe)
            
        except:
            # If probe fails, skip this point
            continue
    
    if len(valid_points) < 4:
        print(f"⚠️ Only found {len(valid_points)} valid edge points, using bounding box corners")
        return use_geometry_corners()
    
    print(f"✅ Found {len(valid_points)} valid edge points")
    
    # Find the 4 most extreme points as corners
    valid_points = np.array(valid_points)
    
    # Find extreme points
    x_coords = valid_points[:, 0]
    z_coords = valid_points[:, 2]
    
    # Find points closest to each corner of bounding box
    corners = []
    corner_targets = [
        [x_min, z_min],  # Back-left
        [x_max, z_min],  # Back-right
        [x_max, z_max],  # Front-right
        [x_min, z_max]   # Front-left
    ]
    
    for target in corner_targets:
        # Find the valid point closest to this target
        distances = np.sqrt((x_coords - target[0])**2 + (z_coords - target[1])**2)
        closest_idx = np.argmin(distances)
        corners.append(valid_points[closest_idx])
    
    # Add center
    center_x = np.mean([c[0] for c in corners])
    center_z = np.mean([c[2] for c in corners])
    corners.append([center_x, hover_height, center_z])
    
    corner_names = ["Back-Left", "Back-Right", "Front-Right", "Front-Left", "Center"]
    
    print("\n🎯 ACTUAL CORNER POINTS:")
    print("=" * 50)
    for name, corner in zip(corner_names, corners):
        print(f"{name}: X={corner[0]:.3f}, Y={corner[1]:.3f}, Z={corner[2]:.3f}")
    print("=" * 50)
    
    # Store for testing
    globals()['test_corners'] = corners
    globals()['test_corner_names'] = corner_names
    globals()['test_corner_index'] = 0
    
    return True

def set_manual_corners():
    """Manually define corner points - you can adjust these coordinates"""
    
    print("📍 Setting manual corner points...")
    print("You can adjust these coordinates based on visual inspection")
    
    # Get the hover height from current bounds
    if model_bounds:
        y_max = model_bounds[3]
        y_min = model_bounds[2]
        hover_height = y_max + (y_max - y_min) * 0.05
    else:
        hover_height = 0.2
    
    # ADJUST THESE COORDINATES based on your visual inspection!
    # Look at your model and estimate where the actual corners are
    # Based on your bounding box: X=[-1.55, 1.29], Z=[-1.88, 2.07]
    # Adjust these to match the ACTUAL rotated corners:
    manual_corners = [
        [-1.3, hover_height, -1.6],   # Back-Left - move closer to actual corner
        [1.1, hover_height, -1.7],    # Back-Right - adjust for rotation
        [1.2, hover_height, 1.9],     # Front-Right - adjust for rotation  
        [-1.4, hover_height, 2.0],    # Front-Left - adjust for rotation
        [-0.1, hover_height, 0.15]    # Center
    ]
    
    corner_names = ["Back-Left", "Back-Right", "Front-Right", "Front-Left", "Center"]
    
    print("\n🎯 MANUAL CORNER POINTS:")
    print("=" * 50)
    for name, corner in zip(corner_names, manual_corners):
        print(f"{name}: X={corner[0]:.3f}, Y={corner[1]:.3f}, Z={corner[2]:.3f}")
    print("=" * 50)
    print("💡 Adjust coordinates in set_manual_corners() function if needed")
    
    # Store for testing
    globals()['test_corners'] = manual_corners
    globals()['test_corner_names'] = corner_names
    globals()['test_corner_index'] = 0
    
    return True

def calculate_exact_clip_intersections():
    """Calculate exact corner points by sampling around the boundary"""
    global model_bounds, coordinate_offset, coordinate_scale
    
    print("🎯 Finding exact corners by boundary sampling...")
    
    # Import numpy
    import numpy as np
    
    # Get Clip6 bounds
    sources = GetSources()
    clip6_source = None
    
    for name, source in sources.items():
        if 'Clip6' in str(name) or 'clip6' in str(name).lower():
            clip6_source = source
            break
    
    if not clip6_source:
        print("❌ Could not find Clip6!")
        return False
    
    bounds = clip6_source.GetDataInformation().GetBounds()
    x_min, x_max = bounds[0], bounds[1]
    y_min, y_max = bounds[2], bounds[3]
    z_min, z_max = bounds[4], bounds[5]
    
    print(f"📦 Clip6 bounds: X=[{x_min:.2f}, {x_max:.2f}], Y=[{y_min:.2f}, {y_max:.2f}], Z=[{z_min:.2f}, {z_max:.2f}]")
    
    # Sample many points around the perimeter of the bounding box
    num_samples = 50
    sample_points = []
    
    # Sample around each edge/face of the bounding box
    for i in range(num_samples):
        t = i / (num_samples - 1)
        
        # 8 edges of the box at different Y levels
        y_test = y_max  # Focus on top surface
        
        # Bottom edges (Z = z_min)
        sample_points.append([x_min + t * (x_max - x_min), y_test, z_min])
        # Top edges (Z = z_max)  
        sample_points.append([x_min + t * (x_max - x_min), y_test, z_max])
        # Left edges (X = x_min)
        sample_points.append([x_min, y_test, z_min + t * (z_max - z_min)])
        # Right edges (X = x_max)
        sample_points.append([x_max, y_test, z_min + t * (z_max - z_min)])
    
    print(f"🔍 Testing {len(sample_points)} boundary points...")
    
    # Test which points are actually on the boundary of the clipped geometry
    valid_boundary_points = []
    
    for point in sample_points:
        if is_point_near_geometry_boundary(point, clip6_source):
            valid_boundary_points.append(point)
    
    print(f"✅ Found {len(valid_boundary_points)} valid boundary points")
    
    if len(valid_boundary_points) < 4:
        print("⚠️ Not enough boundary points found, trying fallback...")
        return extract_corners_from_geometry()
    
    # Find corner points from the valid boundary points
    boundary_points = np.array(valid_boundary_points)
    
    # Find the most extreme points (corners)
    xz_points = boundary_points[:, [0, 2]]  # Project to XZ plane
    center_xz = np.mean(xz_points, axis=0)
    
    # Find points furthest from center (likely corners)
    distances = np.linalg.norm(xz_points - center_xz, axis=1)
    num_corners = min(8, max(4, len(boundary_points) // 5))
    corner_indices = np.argsort(distances)[-num_corners:]
    
    corners = boundary_points[corner_indices]
    
    # Get hover height
    y_coords = corners[:, 1]
    y_max_corners = np.max(y_coords)
    hover_height = y_max_corners + (y_max - y_min) * 0.05
    
    # Create hover positions
    hover_corners = []
    for corner in corners:
        hover_corners.append([corner[0], hover_height, corner[2]])
    
    # Add center
    center_x = np.mean([c[0] for c in hover_corners])
    center_z = np.mean([c[2] for c in hover_corners])
    hover_corners.append([center_x, hover_height, center_z])
    
    # Generate names
    corner_names = [f"Corner-{i+1}" for i in range(len(corners))] + ["Center"]
    
    print(f"\n🎯 BOUNDARY-SAMPLED CORNERS:")
    print("=" * 50)
    for name, corner in zip(corner_names, hover_corners):
        print(f"{name}: X={corner[0]:.3f}, Y={corner[1]:.3f}, Z={corner[2]:.3f}")
    print("=" * 50)
    
    # Store for testing
    globals()['test_corners'] = hover_corners
    globals()['test_corner_names'] = corner_names
    globals()['test_corner_index'] = 0
    
    return True

def is_point_in_clipped_region(point):
    """Test if a point is inside the actual clipped region using distance check"""
    
    # Find Clip6
    sources = GetSources()
    clip6_source = None
    
    for name, source in sources.items():
        if 'Clip6' in str(name) or 'clip6' in str(name).lower():
            clip6_source = source
            break
    
    if not clip6_source:
        return False
    
    # Get bounds of clipped region
    bounds = clip6_source.GetDataInformation().GetBounds()
    
    # Check if point is roughly within bounds (with some tolerance)
    tolerance = 0.1  # 10cm tolerance
    
    in_bounds = (
        bounds[0] - tolerance <= point[0] <= bounds[1] + tolerance and
        bounds[2] - tolerance <= point[1] <= bounds[3] + tolerance and
        bounds[4] - tolerance <= point[2] <= bounds[5] + tolerance
    )
    
    return in_bounds

def is_point_near_geometry_boundary(point, clip6_source):
    """Test if a point is near the boundary of the clipped geometry"""
    
    try:
        # Create a small sphere at the point and see if it intersects with geometry
        test_sphere = Sphere()
        test_sphere.Center = point
        test_sphere.Radius = 0.05  # 5cm radius
        
        # Check intersection
        intersection = AppendGeometry()
        intersection.Input = [clip6_source, test_sphere]
        intersection.UpdatePipeline()
        
        # Get number of points - if > 0, there's an intersection
        intersection_data = intersection.GetDataInformation()
        num_points = intersection_data.GetNumberOfPoints()
        
        # Clean up
        Delete(intersection)
        Delete(test_sphere)
        
        return num_points > 0
        
    except:
        # If any error, just check if point is within bounds
        bounds = clip6_source.GetDataInformation().GetBounds()
        tolerance = 0.02
        
        return (bounds[0] - tolerance <= point[0] <= bounds[1] + tolerance and
                bounds[2] - tolerance <= point[1] <= bounds[3] + tolerance and
                bounds[4] - tolerance <= point[2] <= bounds[5] + tolerance)

def extract_corners_from_geometry():
    """Fallback method: extract corner points from the actual geometry vertices"""
    
    print("🔄 Extracting corners from Clip6 geometry vertices...")
    
    # Import numpy here too
    import numpy as np
    
    # Find Clip6
    sources = GetSources()
    clip6_source = None
    
    for name, source in sources.items():
        if 'Clip6' in str(name) or 'clip6' in str(name).lower():
            clip6_source = source
            break
    
    if not clip6_source:
        print("❌ Could not find Clip6!")
        return False
    
    try:
        # Use a programmable filter to extract all vertex coordinates
        prog_filter = ProgrammableFilter(Input=clip6_source)
        prog_filter.Script = """
import numpy as np
import vtk

input_data = self.GetInput()
points = input_data.GetPoints()
num_points = points.GetNumberOfPoints()

# Get all coordinates
coords = []
for i in range(num_points):
    point = points.GetPoint(i)
    coords.append([point[0], point[1], point[2]])

# Create output with coordinate data
output = self.GetOutput()
output.ShallowCopy(input_data)

# Store coordinates in field data
coords_array = vtk.vtkFloatArray()
coords_array.SetName("all_coordinates")
coords_array.SetNumberOfComponents(3)
coords_array.SetNumberOfTuples(len(coords))

for i, coord in enumerate(coords):
    coords_array.SetTuple3(i, coord[0], coord[1], coord[2])

output.GetFieldData().AddArray(coords_array)
"""
        prog_filter.UpdatePipeline()
        
        # Get the coordinates
        output_data = prog_filter.GetOutput()
        field_data = output_data.GetFieldData()
        
        if field_data.GetArray("all_coordinates"):
            coords_array = field_data.GetArray("all_coordinates")
            num_points = coords_array.GetNumberOfTuples()
            
            # Extract all points
            all_points = []
            for i in range(num_points):
                coord = coords_array.GetTuple3(i)
                all_points.append([coord[0], coord[1], coord[2]])
            
            all_points = np.array(all_points)
            print(f"📊 Extracted {len(all_points)} vertices from geometry")
            
            # Clean up
            Delete(prog_filter)
            
            # Find corner points by finding extremes
            corners = find_geometry_corners(all_points)
            
            if corners:
                # Store for testing
                globals()['test_corners'] = corners
                globals()['test_corner_names'] = [f"Corner-{i+1}" for i in range(len(corners)-1)] + ["Center"]
                globals()['test_corner_index'] = 0
                
                print("✅ Geometry corners extracted and ready for testing!")
                return True
        
        # Clean up if failed
        Delete(prog_filter)
        
    except Exception as e:
        print(f"❌ Error extracting geometry: {e}")
    
    return False

def find_geometry_corners(points):
    """Find corner points from geometry vertices"""
    import numpy as np
    
    # Get Y bounds
    y_min, y_max = np.min(points[:, 1]), np.max(points[:, 1])
    hover_height = y_max + (y_max - y_min) * 0.05
    
    # Focus on surface points (top 20% of Y range)
    surface_threshold = y_max - (y_max - y_min) * 0.2
    surface_points = points[points[:, 1] > surface_threshold]
    
    print(f"🔝 Found {len(surface_points)} surface points")
    
    if len(surface_points) < 4:
        surface_points = points  # Use all points if not enough surface points
    
    # Get XZ coordinates for corner finding
    xz_points = surface_points[:, [0, 2]]
    
    # Find the 4-8 most extreme points
    center_xz = np.mean(xz_points, axis=0)
    distances = np.linalg.norm(xz_points - center_xz, axis=1)
    
    # Take the most distant points (likely corners)
    num_corners = min(8, max(4, len(surface_points) // 10))
    corner_indices = np.argsort(distances)[-num_corners:]
    corner_points_xz = xz_points[corner_indices]
    
    # Convert to 3D hover positions
    corners = []
    for corner_xz in corner_points_xz:
        corners.append([corner_xz[0], hover_height, corner_xz[1]])
    
    # Add center
    center_x = np.mean([c[0] for c in corners])
    center_z = np.mean([c[2] for c in corners])
    corners.append([center_x, hover_height, center_z])
    
    print(f"\n🎯 GEOMETRY-BASED CORNERS:")
    print("=" * 50)
    for i, corner in enumerate(corners):
        name = f"Corner-{i+1}" if i < len(corners)-1 else "Center"
        print(f"{name}: X={corner[0]:.3f}, Y={corner[1]:.3f}, Z={corner[2]:.3f}")
    print("=" * 50)
    
    return corners

def test_simple_move():
    """Simple test - just move the rover slightly"""
    global latest_position, rover_source
    
    if not rover_source:
        print("❌ No rover created! Run start_demo() first.")
        return
        
    print("➡️ Testing simple movement...")
    
    # Get current position
    current = rover_source.Center
    print(f"Current position: [{current[0]:.2f}, {current[1]:.2f}, {current[2]:.2f}]")
    
    # Move it slightly
    new_pos = [current[0] + 1.0, current[1] + 1.0, current[2] + 0.5]
    latest_position = new_pos
    
    print(f"Moving to: [{new_pos[0]:.2f}, {new_pos[1]:.2f}, {new_pos[2]:.2f}]")
    update_visualization()
    
    # Check if it actually moved
    new_current = rover_source.Center
    print(f"New position: [{new_current[0]:.2f}, {new_current[1]:.2f}, {new_current[2]:.2f}]")
    
    if new_current != current:
        print("✅ Movement successful!")
    else:
        print("❌ Movement failed!")

# Initialize
print("🌍 Auto-Scaled Falconia Rover Demo!")
print("=" * 40)
print("SETUP:")
print("1. Load your Falconia 3D model FIRST")
print("2. start_demo()")
print("3. TEST MOVEMENT:")
print("   - test_simple_move() - Basic movement test")
print("   - test_corner_movement() - Move to all corners")
print("   - test_random_movement() - Random positions")
print("4. while auto_update(): pass - For live MQTT")
print("=" * 40)