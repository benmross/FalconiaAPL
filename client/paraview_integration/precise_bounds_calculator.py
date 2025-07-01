#!/usr/bin/env python3
"""
Precise Bounds Calculator - Extract exact clip plane intersections
"""

from paraview.simple import *
import numpy as np

def get_clip_plane_info():
    """Extract clip plane parameters from all clips in the pipeline"""
    
    sources = GetSources()
    clip_planes = {}
    
    print("🔍 Searching for clip planes...")
    
    for name, source in sources.items():
        name_str = str(name)
        if 'clip' in name_str.lower():
            try:
                # Get clip plane properties
                if hasattr(source, 'ClipType'):
                    clip_type = source.ClipType
                    if hasattr(clip_type, 'Origin') and hasattr(clip_type, 'Normal'):
                        origin = list(clip_type.Origin)
                        normal = list(clip_type.Normal)
                        
                        clip_planes[name_str] = {
                            'origin': origin,
                            'normal': normal,
                            'source': source
                        }
                        
                        print(f"  📎 {name_str}:")
                        print(f"     Origin: [{origin[0]:.2f}, {origin[1]:.2f}, {origin[2]:.2f}]")
                        print(f"     Normal: [{normal[0]:.2f}, {normal[1]:.2f}, {normal[2]:.2f}]")
                        
            except Exception as e:
                print(f"  ⚠️ Error reading {name_str}: {e}")
    
    return clip_planes

def calculate_intersection_bounds(clip_planes):
    """Calculate the intersection bounds from clip planes"""
    
    if len(clip_planes) != 4:
        print(f"⚠️ Expected 4 clip planes, found {len(clip_planes)}")
        return None
    
    print("\n🧮 Calculating intersection bounds...")
    
    # For each clip plane, we have: normal·(point - origin) = 0
    # The clipped region is where normal·(point - origin) <= 0
    
    # We need to find the intersection of all 4 half-spaces
    # This creates a rectangular region on the XZ plane
    
    bounds = {'x_min': None, 'x_max': None, 'z_min': None, 'z_max': None}
    
    for clip_name, clip_info in clip_planes.items():
        origin = np.array(clip_info['origin'])
        normal = np.array(clip_info['normal'])
        
        print(f"  📎 {clip_name}: normal=[{normal[0]:.2f}, {normal[1]:.2f}, {normal[2]:.2f}]")
        
        # Determine which boundary this clip defines
        # Assuming normals point inward to the clipped region
        
        if abs(normal[0]) > 0.9:  # X-direction clip
            if normal[0] > 0:  # Points in +X direction, so this is X-min boundary
                bounds['x_min'] = origin[0]
                print(f"    → X-min boundary at {origin[0]:.2f}")
            else:  # Points in -X direction, so this is X-max boundary
                bounds['x_max'] = origin[0]
                print(f"    → X-max boundary at {origin[0]:.2f}")
                
        elif abs(normal[2]) > 0.9:  # Z-direction clip
            if normal[2] > 0:  # Points in +Z direction, so this is Z-min boundary
                bounds['z_min'] = origin[2]
                print(f"    → Z-min boundary at {origin[2]:.2f}")
            else:  # Points in -Z direction, so this is Z-max boundary
                bounds['z_max'] = origin[2]
                print(f"    → Z-max boundary at {origin[2]:.2f}")
        else:
            print(f"    → Unrecognized clip direction")
    
    return bounds

def get_y_bounds_from_clip4():
    """Get Y bounds specifically from Clip4"""
    sources = GetSources()
    
    for name, source in sources.items():
        if 'Clip4' in str(name) or 'clip4' in str(name).lower():
            bounds = source.GetDataInformation().GetBounds()
            return bounds[2], bounds[3]  # Y-min, Y-max
    
    return None, None

def calculate_precise_corners():
    """Calculate precise corner positions from clip plane intersections"""
    
    clip_planes = get_clip_plane_info()
    
    if not clip_planes:
        print("❌ No clip planes found!")
        return None
        
    intersection_bounds = calculate_intersection_bounds(clip_planes)
    
    if not intersection_bounds:
        print("❌ Could not calculate intersection bounds!")
        return None
        
    # Get Y bounds from Clip4
    y_min, y_max = get_y_bounds_from_clip4()
    
    if y_min is None:
        print("⚠️ Could not get Y bounds, using defaults")
        y_min, y_max = 0, 1
    
    # Calculate hover height
    hover_height = y_max + (y_max - y_min) * 0.05
    
    # Define precise corners
    x_min = intersection_bounds['x_min']
    x_max = intersection_bounds['x_max']
    z_min = intersection_bounds['z_min']
    z_max = intersection_bounds['z_max']
    
    if None in [x_min, x_max, z_min, z_max]:
        print("❌ Missing boundary information!")
        return None
    
    precise_corners = [
        [x_min, hover_height, z_min],  # Back-left
        [x_max, hover_height, z_min],  # Back-right
        [x_max, hover_height, z_max],  # Front-right
        [x_min, hover_height, z_max],  # Front-left
        [(x_min + x_max)/2, hover_height, (z_min + z_max)/2]  # Center
    ]
    
    corner_names = ["Back-Left", "Back-Right", "Front-Right", "Front-Left", "Center"]
    
    print("\n🎯 PRECISE CORNERS:")
    print("=" * 40)
    for name, corner in zip(corner_names, precise_corners):
        print(f"{name}: X={corner[0]:.3f}, Y={corner[1]:.3f}, Z={corner[2]:.3f}")
    print("=" * 40)
    
    return {
        'corners': precise_corners,
        'names': corner_names,
        'bounds': {
            'x_min': x_min, 'x_max': x_max,
            'z_min': z_min, 'z_max': z_max,
            'y_min': y_min, 'y_max': y_max,
            'hover_height': hover_height
        }
    }

def update_rover_scaling_with_precise_bounds():
    """Update the rover demo with precise clip-based bounds"""
    
    precise_info = calculate_precise_corners()
    
    if not precise_info:
        print("❌ Could not calculate precise bounds")
        return False
    
    bounds_info = precise_info['bounds']
    
    # Update global variables for rover demo
    global coordinate_offset, coordinate_scale, model_bounds
    
    # Create bounds array in ParaView format: [x_min, x_max, y_min, y_max, z_min, z_max]
    model_bounds = [
        bounds_info['x_min'], bounds_info['x_max'],
        bounds_info['y_min'], bounds_info['y_max'],
        bounds_info['z_min'], bounds_info['z_max']
    ]
    
    # Calculate new scaling
    model_x_width = bounds_info['x_max'] - bounds_info['x_min']
    model_z_depth = bounds_info['z_max'] - bounds_info['z_min']
    model_y_height = bounds_info['y_max'] - bounds_info['y_min']
    
    rover_x_range = 2.0
    rover_y_range = 1.5
    
    coordinate_scale = [
        model_x_width / rover_x_range,
        model_z_depth / rover_y_range,
        model_y_height * 0.1
    ]
    
    coordinate_offset = [
        bounds_info['x_min'],
        bounds_info['z_min'],
        bounds_info['hover_height']
    ]
    
    print("✅ Updated rover scaling with precise bounds!")
    print(f"   Scale: [{coordinate_scale[0]:.3f}, {coordinate_scale[1]:.3f}, {coordinate_scale[2]:.3f}]")
    print(f"   Offset: [{coordinate_offset[0]:.3f}, {coordinate_offset[1]:.3f}, {coordinate_offset[2]:.3f}]")
    
    # Store corners for testing
    globals()['precise_corners'] = precise_info['corners']
    globals()['precise_corner_names'] = precise_info['names']
    
    return True

# Initialize
print("🎯 Precise Bounds Calculator Loaded!")
print("=" * 40)
print("USAGE:")
print("1. get_clip_plane_info() - Show all clip planes")
print("2. calculate_precise_corners() - Calculate exact corners")
print("3. update_rover_scaling_with_precise_bounds() - Apply to rover")
print("=" * 40)