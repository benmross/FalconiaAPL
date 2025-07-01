#!/usr/bin/env python3
"""
Rotated Bounds Calculator - Handle rotated/oriented models
Finds the actual corner points of a rotated rectangular model
"""

from paraview.simple import *
import numpy as np

def get_actual_corner_points():
    """Extract actual corner points from the rotated model geometry"""
    
    # Find Clip4
    sources = GetSources()
    clip4_source = None
    
    for name, source in sources.items():
        if 'Clip4' in str(name) or 'clip4' in str(name).lower():
            clip4_source = source
            print(f"✅ Found Clip4: {name}")
            break
    
    if not clip4_source:
        print("❌ Could not find Clip4!")
        return None
    
    # Get the actual geometry data
    clip4_source.UpdatePipeline()
    data = clip4_source.GetClientSideObject().GetOutput()
    
    if not data:
        print("❌ Could not get geometry data!")
        return None
    
    # Extract all points from the geometry
    points = data.GetPoints()
    num_points = points.GetNumberOfPoints()
    
    print(f"📊 Found {num_points} points in geometry")
    
    # Convert to numpy array for easier processing
    point_array = []
    for i in range(num_points):
        point = points.GetPoint(i)
        point_array.append([point[0], point[1], point[2]])
    
    point_array = np.array(point_array)
    
    # Find the Y range (height)
    y_min, y_max = np.min(point_array[:, 1]), np.max(point_array[:, 1])
    
    # Focus on points near the top surface (Y close to y_max)
    surface_threshold = y_max - (y_max - y_min) * 0.1  # Top 10%
    surface_points = point_array[point_array[:, 1] > surface_threshold]
    
    print(f"📏 Y range: {y_min:.3f} to {y_max:.3f}")
    print(f"🔝 Found {len(surface_points)} surface points")
    
    if len(surface_points) < 4:
        print("⚠️ Not enough surface points, using all points")
        surface_points = point_array
    
    # Find the extreme points in XZ plane
    xz_points = surface_points[:, [0, 2]]  # Extract X and Z coordinates
    
    # Find convex hull to get the boundary points
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(xz_points)
        hull_points = xz_points[hull.vertices]
        
        print(f"🔷 Convex hull has {len(hull_points)} vertices")
        
        # For a rectangular model, we should have 4 main corners
        # Find the 4 most extreme points
        corners_xz = find_rectangular_corners(hull_points)
        
    except ImportError:
        print("⚠️ SciPy not available, using simple method")
        corners_xz = find_corners_simple(xz_points)
    
    # Convert back to 3D with hover height
    hover_height = y_max + (y_max - y_min) * 0.05
    corners_3d = []
    
    for corner_xz in corners_xz:
        corners_3d.append([corner_xz[0], hover_height, corner_xz[1]])
    
    # Add center point
    center_x = np.mean([c[0] for c in corners_3d])
    center_z = np.mean([c[2] for c in corners_3d])
    corners_3d.append([center_x, hover_height, center_z])
    
    # Label corners based on their relative positions
    corner_names = label_corners(corners_3d[:-1]) + ["Center"]
    
    print("\n🎯 ACTUAL CORNER POINTS:")
    print("=" * 50)
    for name, corner in zip(corner_names, corners_3d):
        print(f"{name}: X={corner[0]:.3f}, Y={corner[1]:.3f}, Z={corner[2]:.3f}")
    print("=" * 50)
    
    return {
        'corners': corners_3d,
        'names': corner_names,
        'y_min': y_min,
        'y_max': y_max,
        'hover_height': hover_height
    }

def find_rectangular_corners(hull_points):
    """Find the 4 corners of a rectangular shape from convex hull points"""
    
    # For a rectangle, find the 4 points that are furthest from the center
    center = np.mean(hull_points, axis=0)
    
    # Calculate distances from center
    distances = np.linalg.norm(hull_points - center, axis=1)
    
    # Sort by distance and take the 4 furthest points
    far_indices = np.argsort(distances)[-4:]
    corners = hull_points[far_indices]
    
    # Sort corners in a sensible order (counterclockwise)
    corners = sort_corners_counterclockwise(corners)
    
    return corners

def find_corners_simple(xz_points):
    """Simple method to find corners without scipy"""
    
    x_coords = xz_points[:, 0]
    z_coords = xz_points[:, 1]
    
    # Find extreme points
    x_min_idx = np.argmin(x_coords)
    x_max_idx = np.argmax(x_coords)
    z_min_idx = np.argmin(z_coords)
    z_max_idx = np.argmax(z_coords)
    
    # Get the extreme points
    corners = np.array([
        xz_points[x_min_idx],  # Leftmost
        xz_points[x_max_idx],  # Rightmost
        xz_points[z_min_idx],  # Backmost
        xz_points[z_max_idx]   # Frontmost
    ])
    
    # Remove duplicates
    corners = np.unique(corners, axis=0)
    
    # If we don't have 4 unique corners, find the 4 most spread out points
    if len(corners) < 4:
        # Use all points and find the 4 most extreme
        center = np.mean(xz_points, axis=0)
        distances = np.linalg.norm(xz_points - center, axis=1)
        far_indices = np.argsort(distances)[-4:]
        corners = xz_points[far_indices]
    
    return sort_corners_counterclockwise(corners)

def sort_corners_counterclockwise(corners):
    """Sort corner points in counterclockwise order"""
    center = np.mean(corners, axis=0)
    
    # Calculate angles from center
    angles = np.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0])
    
    # Sort by angle
    sorted_indices = np.argsort(angles)
    return corners[sorted_indices]

def label_corners(corners_3d):
    """Label corners based on their relative positions"""
    
    # Find center
    center_x = np.mean([c[0] for c in corners_3d])
    center_z = np.mean([c[2] for c in corners_3d])
    
    labels = []
    for corner in corners_3d:
        x, z = corner[0], corner[2]
        
        # Determine position relative to center
        x_label = "Right" if x > center_x else "Left"
        z_label = "Front" if z > center_z else "Back"
        
        labels.append(f"{z_label}-{x_label}")
    
    return labels

def update_rover_with_actual_corners():
    """Update rover demo to use actual corner points"""
    
    corner_info = get_actual_corner_points()
    
    if not corner_info:
        print("❌ Could not get corner points!")
        return False
    
    # Store globally for testing
    globals()['actual_corners'] = corner_info['corners']
    globals()['actual_corner_names'] = corner_info['names']
    
    # Update model bounds to encompass all corners
    corners = corner_info['corners'][:-1]  # Exclude center
    
    x_coords = [c[0] for c in corners]
    z_coords = [c[2] for c in corners]
    
    global model_bounds, coordinate_offset, coordinate_scale
    
    model_bounds = [
        min(x_coords), max(x_coords),  # X range
        corner_info['y_min'], corner_info['y_max'],  # Y range
        min(z_coords), max(z_coords)   # Z range
    ]
    
    # Calculate scaling based on actual corner spread
    model_x_width = max(x_coords) - min(x_coords)
    model_z_depth = max(z_coords) - min(z_coords)
    model_y_height = corner_info['y_max'] - corner_info['y_min']
    
    rover_x_range = 2.0
    rover_y_range = 1.5
    
    coordinate_scale = [
        model_x_width / rover_x_range,
        model_z_depth / rover_y_range,
        model_y_height * 0.1
    ]
    
    coordinate_offset = [
        min(x_coords),
        min(z_coords),
        corner_info['hover_height']
    ]
    
    print("✅ Updated rover scaling with actual corner points!")
    print(f"   X range: {min(x_coords):.3f} to {max(x_coords):.3f}")
    print(f"   Z range: {min(z_coords):.3f} to {max(z_coords):.3f}")
    print(f"   Scale: [{coordinate_scale[0]:.3f}, {coordinate_scale[1]:.3f}, {coordinate_scale[2]:.3f}]")
    print(f"   Offset: [{coordinate_offset[0]:.3f}, {coordinate_offset[1]:.3f}, {coordinate_offset[2]:.3f}]")
    
    return True

def test_actual_corners():
    """Test movement to actual corner points"""
    
    if 'actual_corners' not in globals():
        print("❌ Run update_rover_with_actual_corners() first!")
        return
    
    corners = globals()['actual_corners']
    names = globals()['actual_corner_names']
    
    globals()['test_corners'] = corners
    globals()['test_corner_names'] = names
    globals()['test_corner_index'] = 0
    
    print("📍 Ready to test actual corners!")
    print("Call move_to_next_corner() to step through them")

# Initialize
print("🔄 Rotated Bounds Calculator Loaded!")
print("=" * 40)
print("USAGE:")
print("1. get_actual_corner_points() - Extract real corners")
print("2. update_rover_with_actual_corners() - Apply to rover")
print("3. test_actual_corners() - Test corner movement")
print("=" * 40)