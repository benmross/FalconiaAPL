#!/usr/bin/env python3
"""
Precise Clip Intersection Calculator
Calculate exact corner points from clip plane intersections
"""

from paraview.simple import *
import numpy as np

def get_all_clip_planes():
    """Extract all clip plane equations"""
    
    sources = GetSources()
    clip_planes = []
    
    print("🔍 Extracting clip plane equations...")
    
    for name, source in sources.items():
        name_str = str(name)
        if 'clip' in name_str.lower():
            try:
                if hasattr(source, 'ClipType') and hasattr(source, 'InsideOut'):
                    clip_type = source.ClipType
                    if hasattr(clip_type, 'Origin') and hasattr(clip_type, 'Normal'):
                        origin = np.array(clip_type.Origin)
                        normal = np.array(clip_type.Normal)
                        inside_out = source.InsideOut
                        
                        # Flip normal if inside out
                        if inside_out:
                            normal = -normal
                        
                        clip_planes.append({
                            'name': name_str,
                            'origin': origin,
                            'normal': normal,
                            'inside_out': inside_out
                        })
                        
                        print(f"  📎 {name_str}:")
                        print(f"     Origin: [{origin[0]:.3f}, {origin[1]:.3f}, {origin[2]:.3f}]")
                        print(f"     Normal: [{normal[0]:.3f}, {normal[1]:.3f}, {normal[2]:.3f}]")
                        print(f"     InsideOut: {inside_out}")
                        
            except Exception as e:
                print(f"  ❌ Error reading {name_str}: {e}")
    
    return clip_planes

def find_line_intersections(clip_planes):
    """Find intersection lines between pairs of clip planes"""
    
    print("\n🔗 Finding clip plane intersections...")
    
    intersection_lines = []
    
    for i, plane1 in enumerate(clip_planes):
        for j, plane2 in enumerate(clip_planes[i+1:], i+1):
            
            n1, n2 = plane1['normal'], plane2['normal']
            p1, p2 = plane1['origin'], plane2['origin']
            
            # Check if planes are parallel
            cross_product = np.cross(n1, n2)
            if np.linalg.norm(cross_product) < 1e-6:
                continue  # Parallel planes
            
            # Find intersection line
            # Line direction is perpendicular to both normals
            line_direction = cross_product / np.linalg.norm(cross_product)
            
            # Find a point on the intersection line
            # Solve the system: n1·(x-p1) = 0, n2·(x-p2) = 0
            # We can set one coordinate arbitrarily and solve for the others
            
            # Choose the coordinate with largest absolute value in line_direction
            max_idx = np.argmax(np.abs(line_direction))
            
            # Create system Ax = b where x is the other two coordinates
            if max_idx == 0:  # Set x = 0
                A = np.array([n1[1:], n2[1:]])
                b = np.array([np.dot(n1, p1) - n1[0] * 0, np.dot(n2, p2) - n2[0] * 0])
                if np.linalg.det(A) != 0:
                    yz = np.linalg.solve(A, b)
                    point_on_line = np.array([0, yz[0], yz[1]])
                else:
                    continue
            elif max_idx == 1:  # Set y = 0  
                A = np.array([[n1[0], n1[2]], [n2[0], n2[2]]])
                b = np.array([np.dot(n1, p1) - n1[1] * 0, np.dot(n2, p2) - n2[1] * 0])
                if np.linalg.det(A) != 0:
                    xz = np.linalg.solve(A, b)
                    point_on_line = np.array([xz[0], 0, xz[1]])
                else:
                    continue
            else:  # Set z = 0
                A = np.array([n1[:2], n2[:2]])
                b = np.array([np.dot(n1, p1) - n1[2] * 0, np.dot(n2, p2) - n2[2] * 0])
                if np.linalg.det(A) != 0:
                    xy = np.linalg.solve(A, b)
                    point_on_line = np.array([xy[0], xy[1], 0])
                else:
                    continue
            
            intersection_lines.append({
                'plane1': plane1['name'],
                'plane2': plane2['name'],
                'point': point_on_line,
                'direction': line_direction
            })
            
            print(f"  📏 {plane1['name']} ∩ {plane2['name']}: line through {point_on_line} || {line_direction}")
    
    return intersection_lines

def find_corner_points(clip_planes, intersection_lines):
    """Find corner points where 3 planes intersect"""
    
    print("\n📍 Finding corner points (3-plane intersections)...")
    
    corners = []
    
    # For each set of 3 planes, find their intersection point
    for i, plane1 in enumerate(clip_planes):
        for j, plane2 in enumerate(clip_planes[i+1:], i+1):
            for k, plane3 in enumerate(clip_planes[j+1:], j+1):
                
                # Solve system: n1·x = d1, n2·x = d2, n3·x = d3
                A = np.array([plane1['normal'], plane2['normal'], plane3['normal']])
                b = np.array([
                    np.dot(plane1['normal'], plane1['origin']),
                    np.dot(plane2['normal'], plane2['origin']),
                    np.dot(plane3['normal'], plane3['origin'])
                ])
                
                try:
                    # Check if system is solvable
                    if np.abs(np.linalg.det(A)) < 1e-10:
                        continue  # Singular matrix
                    
                    intersection_point = np.linalg.solve(A, b)
                    
                    # Verify this point satisfies all clip constraints
                    valid = True
                    for plane in clip_planes:
                        # Check if point is on the "kept" side of each plane
                        distance = np.dot(plane['normal'], intersection_point - plane['origin'])
                        if distance > 1e-6:  # Point is on wrong side
                            valid = False
                            break
                    
                    if valid:
                        corners.append({
                            'point': intersection_point,
                            'planes': [plane1['name'], plane2['name'], plane3['name']]
                        })
                        
                        print(f"  ✅ Corner: [{intersection_point[0]:.3f}, {intersection_point[1]:.3f}, {intersection_point[2]:.3f}]")
                        print(f"     From: {plane1['name']}, {plane2['name']}, {plane3['name']}")
                        
                except np.linalg.LinAlgError:
                    continue
    
    return corners

def calculate_precise_corners():
    """Main function to calculate precise corner points"""
    
    print("🎯 CALCULATING PRECISE CORNERS FROM CLIP INTERSECTIONS")
    print("=" * 60)
    
    # Get all clip planes
    clip_planes = get_all_clip_planes()
    
    if len(clip_planes) < 3:
        print(f"❌ Need at least 3 clip planes, found {len(clip_planes)}")
        return None
    
    # Find intersection lines
    intersection_lines = find_line_intersections(clip_planes)
    
    # Find corner points
    corners = find_corner_points(clip_planes, intersection_lines)
    
    if not corners:
        print("❌ No valid corners found!")
        return None
    
    # Sort corners and add center
    corner_points = [c['point'] for c in corners]
    
    # Get Y bounds for hover height
    y_coords = [p[1] for p in corner_points]
    y_min, y_max = min(y_coords), max(y_coords)
    hover_height = y_max + (y_max - y_min) * 0.05
    
    # Convert to hover positions
    hover_corners = []
    for point in corner_points:
        hover_corners.append([point[0], hover_height, point[2]])
    
    # Add center
    center_x = np.mean([c[0] for c in hover_corners])
    center_z = np.mean([c[2] for c in hover_corners])
    hover_corners.append([center_x, hover_height, center_z])
    
    # Generate names
    corner_names = [f"Corner-{i+1}" for i in range(len(corner_points))] + ["Center"]
    
    print(f"\n🎯 PRECISE CORNERS ({len(corner_points)} found):")
    print("=" * 60)
    for name, corner in zip(corner_names, hover_corners):
        print(f"{name}: X={corner[0]:.3f}, Y={corner[1]:.3f}, Z={corner[2]:.3f}")
    print("=" * 60)
    
    return {
        'corners': hover_corners,
        'names': corner_names,
        'y_min': y_min,
        'y_max': y_max,
        'hover_height': hover_height
    }

def update_rover_with_precise_corners():
    """Update rover demo with precisely calculated corners"""
    
    corner_info = calculate_precise_corners()
    
    if not corner_info:
        print("❌ Could not calculate precise corners!")
        return False
    
    # Store globally for testing
    globals()['test_corners'] = corner_info['corners']
    globals()['test_corner_names'] = corner_info['names']
    globals()['test_corner_index'] = 0
    
    print("✅ Precise corners calculated and ready for testing!")
    print("Call move_to_next_corner() to test them")
    
    return True

# Initialize
print("🎯 Precise Clip Intersection Calculator Loaded!")
print("=" * 50)
print("USAGE:")
print("1. calculate_precise_corners() - Calculate exact intersections")
print("2. update_rover_with_precise_corners() - Apply to rover")
print("3. Use move_to_next_corner() to test")
print("=" * 50)