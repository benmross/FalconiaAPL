#!/usr/bin/env python3
"""
Get 3D Model Bounds for Rover Scaling
Run this in ParaView after loading your Falconia model
"""

from paraview.simple import *

def get_model_bounds():
    """Get the bounds of the currently loaded 3D model"""
    
    # Get all sources in the pipeline
    sources = GetSources()
    
    if not sources:
        print("❌ No models loaded! Load your Falconia 3D scan first.")
        return None
        
    print("📊 Found these data sources:")
    for name, source in sources.items():
        print(f"  - {name}")
    
    # Get the first/main source (your 3D model)
    main_source = list(sources.values())[0]
    
    # Get bounds: [xmin, xmax, ymin, ymax, zmin, zmax]
    bounds = main_source.GetDataInformation().GetBounds()
    
    print("\n🌍 MODEL BOUNDS:")
    print("=" * 40)
    print(f"X: {bounds[0]:.3f} to {bounds[1]:.3f} (width: {bounds[1]-bounds[0]:.3f})")
    print(f"Y: {bounds[2]:.3f} to {bounds[3]:.3f} (height: {bounds[3]-bounds[2]:.3f})")
    print(f"Z: {bounds[4]:.3f} to {bounds[5]:.3f} (depth: {bounds[5]-bounds[4]:.3f})")
    print("=" * 40)
    
    # Calculate center and scale
    center = [
        (bounds[0] + bounds[1]) / 2,
        (bounds[2] + bounds[3]) / 2,
        (bounds[4] + bounds[5]) / 2
    ]
    
    scale = [
        bounds[1] - bounds[0],  # X width
        bounds[3] - bounds[2],  # Y height  
        bounds[5] - bounds[4]   # Z depth
    ]
    
    print(f"\n📍 MODEL CENTER: [{center[0]:.3f}, {center[1]:.3f}, {center[2]:.3f}]")
    print(f"📏 MODEL SCALE: [{scale[0]:.3f}, {scale[1]:.3f}, {scale[2]:.3f}]")
    
    return {
        'bounds': bounds,
        'center': center,
        'scale': scale
    }

def get_rover_transform_settings():
    """Get the settings needed for rover coordinate transformation"""
    
    model_info = get_model_bounds()
    if not model_info:
        return None
        
    bounds = model_info['bounds']
    center = model_info['center']
    scale = model_info['scale']
    
    # Calculate transform settings for rover
    # Rover coordinates are typically 0-2 in X, 0-1.5 in Y
    rover_bounds = [0, 2.0, 0, 1.5]  # [xmin, xmax, ymin, ymax]
    
    # Calculate offset and scale to map rover coords to model coords
    x_offset = bounds[0] - rover_bounds[0] * scale[0] / (rover_bounds[1] - rover_bounds[0])
    y_offset = bounds[2] - rover_bounds[2] * scale[1] / (rover_bounds[3] - rover_bounds[2])
    z_offset = bounds[4] + scale[2] * 0.1  # Hover slightly above model
    
    x_scale = scale[0] / (rover_bounds[1] - rover_bounds[0])
    y_scale = scale[1] / (rover_bounds[3] - rover_bounds[2])
    z_scale = scale[2] * 0.1  # Scale Z to 10% of model height
    
    transform_settings = {
        'coordinate_offset': [x_offset, y_offset, z_offset],
        'coordinate_scale': [x_scale, y_scale, z_scale]
    }
    
    print("\n🎯 ROVER TRANSFORM SETTINGS:")
    print("=" * 40)
    print("Add these to your rover script:")
    print(f"coordinate_offset = {transform_settings['coordinate_offset']}")
    print(f"coordinate_scale = {transform_settings['coordinate_scale']}")
    print("=" * 40)
    
    return transform_settings

def show_corner_points():
    """Show the 8 corner points of the model"""
    
    model_info = get_model_bounds()
    if not model_info:
        return
        
    bounds = model_info['bounds']
    
    print("\n📍 MODEL CORNER POINTS:")
    print("=" * 40)
    corners = [
        [bounds[0], bounds[2], bounds[4]],  # min x, min y, min z
        [bounds[1], bounds[2], bounds[4]],  # max x, min y, min z
        [bounds[0], bounds[3], bounds[4]],  # min x, max y, min z
        [bounds[1], bounds[3], bounds[4]],  # max x, max y, min z
        [bounds[0], bounds[2], bounds[5]],  # min x, min y, max z
        [bounds[1], bounds[2], bounds[5]],  # max x, min y, max z
        [bounds[0], bounds[3], bounds[5]],  # min x, max y, max z
        [bounds[1], bounds[3], bounds[5]],  # max x, max y, max z
    ]
    
    for i, corner in enumerate(corners):
        print(f"Corner {i+1}: [{corner[0]:.3f}, {corner[1]:.3f}, {corner[2]:.3f}]")
    print("=" * 40)

# Main function to run
def analyze_model():
    """Complete analysis of the 3D model for rover scaling"""
    print("🔍 ANALYZING 3D MODEL FOR ROVER SCALING")
    print("=" * 50)
    
    get_model_bounds()
    show_corner_points()
    transform_settings = get_rover_transform_settings()
    
    print("\n✅ ANALYSIS COMPLETE!")
    print("Copy the coordinate_offset and coordinate_scale values above")
    print("and use them in your rover demo script.")
    
    return transform_settings

# Auto-run
print("📐 Model Bounds Analyzer Loaded!")
print("USAGE:")
print("1. Make sure your Falconia 3D model is loaded")
print("2. Run: analyze_model()")
print("3. Copy the coordinate settings to your rover script")