#!/usr/bin/env python3
"""
Find Real Corner Points - Extract actual corner vertices from rotated geometry
"""

from paraview.simple import *
import numpy as np

def extract_corner_vertices():
    """Extract actual corner vertices from Clip4 geometry"""
    
    # Find Clip4
    sources = GetSources()
    clip4_source = None
    
    for name, source in sources.items():
        if 'Clip4' in str(name) or 'clip4' in str(name).lower():
            clip4_source = source
            break
    
    if not clip4_source:
        print("❌ Could not find Clip4!")
        return None
    
    print("🔍 Extracting corner vertices from Clip4...")
    
    # Convert to PolyData to access vertices
    extract_surface = ExtractSurface(Input=clip4_source)
    extract_surface.UpdatePipeline()
    
    # Use a programmable filter to extract point coordinates
    programmable_filter = ProgrammableFilter(Input=extract_surface)
    programmable_filter.Script = """
import numpy as np

# Get input data
input_data = self.GetInput()
points = input_data.GetPoints()
num_points = points.GetNumberOfPoints()

# Extract all point coordinates
point_coords = []
for i in range(num_points):
    point = points.GetPoint(i)
    point_coords.append([point[0], point[1], point[2]])

# Store in field data for retrieval
import vtk
coords_array = vtk.vtkFloatArray()
coords_array.SetName("point_coordinates")
coords_array.SetNumberOfComponents(3)
coords_array.SetNumberOfTuples(len(point_coords))

for i, coord in enumerate(point_coords):
    coords_array.SetTuple3(i, coord[0], coord[1], coord[2])

output = self.GetOutput()
output.GetFieldData().AddArray(coords_array)
"""
    
    programmable_filter.UpdatePipeline()
    
    # Get the coordinates back
    output_data = programmable_filter.GetOutput()
    field_data = output_data.GetFieldData()
    
    if field_data.GetArray("point_coordinates"):
        coords_array = field_data.GetArray("point_coordinates")
        num_points = coords_array.GetNumberOfTuples()
        
        # Extract coordinates
        points = []
        for i in range(num_points):
            coord = coords_array.GetTuple3(i)
            points.append([coord[0], coord[1], coord[2]])
        
        points = np.array(points)
        print(f"📊 Extracted {len(points)} vertices")
        
        # Clean up temporary filters
        Delete(programmable_filter)
        Delete(extract_surface)
        
        return analyze_corner_points(points)
    else:
        print("❌ Could not extract point coordinates")
        Delete(programmable_filter)
        Delete(extract_surface)
        return None

def analyze_corner_points(points):
    """Find the actual corner points from all vertices"""
    
    # Get Y bounds for surface detection
    y_min, y_max = np.min(points[:, 1]), np.max(points[:, 1])
    
    # Focus on top surface points
    surface_threshold = y_max - (y_max - y_min) * 0.2  # Top 20%
    surface_points = points[points[:, 1] > surface_threshold]
    
    print(f"📏 Y range: {y_min:.3f} to {y_max:.3f}")
    print(f"🔝 Found {len(surface_points)} surface points")
    
    # Get XZ coordinates of surface points
    xz_points = surface_points[:, [0, 2]]
    
    # Find convex hull to get boundary points
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(xz_points)
        boundary_points = xz_points[hull.vertices]
        
        print(f"🔷 Convex hull has {len(boundary_points)} boundary points")
        
        # Find the 4 most extreme points (corners)
        corners_xz = find_rectangle_corners(boundary_points)
        
    except ImportError:
        print("⚠️ SciPy not available, using distance method")
        corners_xz = find_corners_by_distance(xz_points)
    
    # Convert back to 3D with proper hover height
    hover_height = y_max + (y_max - y_min) * 0.05
    corners_3d = []
    
    for corner_xz in corners_xz:
        corners_3d.append([corner_xz[0], hover_height, corner_xz[1]])
    
    # Add center
    center_x = np.mean([c[0] for c in corners_3d])
    center_z = np.mean([c[2] for c in corners_3d])
    corners_3d.append([center_x, hover_height, center_z])
    
    # Label corners
    corner_names = ["Corner-1", "Corner-2", "Corner-3", "Corner-4", "Center"]
    
    print("\n🎯 REAL CORNER VERTICES:")
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

def find_rectangle_corners(boundary_points):
    """Find 4 corners of rectangle from boundary points"""
    
    # For a rectangle, we want the 4 points that are furthest from center
    center = np.mean(boundary_points, axis=0)
    distances = np.linalg.norm(boundary_points - center, axis=1)
    
    # Get the 4 furthest points
    corner_indices = np.argsort(distances)[-4:]
    corners = boundary_points[corner_indices]
    
    # Sort corners in order (roughly counterclockwise)
    center = np.mean(corners, axis=0)
    angles = np.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0])
    sorted_indices = np.argsort(angles)
    
    return corners[sorted_indices]

def find_corners_by_distance(xz_points):
    """Fallback method to find corners by distance from center"""
    
    center = np.mean(xz_points, axis=0)
    distances = np.linalg.norm(xz_points - center, axis=1)
    
    # Get the 10% most distant points
    num_far = max(4, len(xz_points) // 10)
    far_indices = np.argsort(distances)[-num_far:]
    far_points = xz_points[far_indices]
    
    # Cluster these into 4 groups to find corners
    from sklearn.cluster import KMeans
    
    try:
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        clusters = kmeans.fit(far_points)
        corner_centers = clusters.cluster_centers_
        
        # Sort corners
        center = np.mean(corner_centers, axis=0)
        angles = np.arctan2(corner_centers[:, 1] - center[1], corner_centers[:, 0] - center[0])
        sorted_indices = np.argsort(angles)
        
        return corner_centers[sorted_indices]
        
    except ImportError:
        # Ultimate fallback - just take 4 most distant unique points
        unique_points = np.unique(far_points, axis=0)
        if len(unique_points) >= 4:
            center = np.mean(unique_points, axis=0)
            distances = np.linalg.norm(unique_points - center, axis=1)
            corner_indices = np.argsort(distances)[-4:]
            return unique_points[corner_indices]
        else:
            return unique_points

def update_rover_with_real_corners():
    """Update rover demo with real corner vertices"""
    
    corner_info = extract_corner_vertices()
    
    if not corner_info:
        print("❌ Could not extract real corners!")
        return False
    
    # Store globally for testing
    globals()['real_corners'] = corner_info['corners']
    globals()['real_corner_names'] = corner_info['names']
    globals()['test_corners'] = corner_info['corners']
    globals()['test_corner_names'] = corner_info['names']
    globals()['test_corner_index'] = 0
    
    print("✅ Real corners extracted and ready for testing!")
    print("Call move_to_next_corner() to test them")
    
    return True

# Initialize
print("🔍 Real Corner Finder Loaded!")
print("=" * 40)
print("USAGE:")
print("1. extract_corner_vertices() - Find real corners")
print("2. update_rover_with_real_corners() - Apply to rover")
print("3. Use move_to_next_corner() to test")
print("=" * 40)