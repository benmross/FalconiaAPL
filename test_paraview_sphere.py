#!/usr/bin/env python3
"""
Simple test script to create a large red sphere in ParaView.
Tests basic ParaView Python integration.
"""

try:
    from paraview.simple import *
    print("ParaView modules imported successfully")
except ImportError as e:
    print(f"Error importing ParaView: {e}")
    print("Make sure PYTHONPATH includes ParaView's site-packages directory")
    exit(1)

def create_red_sphere():
    """Create a large red sphere in ParaView"""
    
    # Create a sphere source
    sphere = Sphere()
    sphere.Radius = 2.0  # Large sphere
    sphere.Center = [0.0, 0.0, 0.0]
    sphere.ThetaResolution = 32
    sphere.PhiResolution = 32
    
    print(f"Created sphere with radius {sphere.Radius}")
    
    # Get active view (create one if none exists)
    renderView = GetActiveViewOrCreate('RenderView')
    
    # Create representation/display
    sphereDisplay = Show(sphere, renderView)
    
    # Set color to red
    sphereDisplay.DiffuseColor = [1.0, 0.0, 0.0]  # RGB red
    sphereDisplay.Representation = 'Surface'
    
    print("Set sphere color to red")
    
    # Reset camera to fit the sphere
    renderView.ResetCamera()
    
    # Render the view
    Render()
    
    print("Rendered sphere in ParaView")
    print("You should now see a large red sphere in your ParaView window")
    
    return sphere, sphereDisplay

if __name__ == "__main__":
    print("Testing ParaView integration...")
    print("Creating a large red sphere...")
    
    try:
        sphere, display = create_red_sphere()
        print("SUCCESS: Red sphere created and displayed in ParaView!")
        
        # Keep the script running briefly
        import time
        print("Waiting 2 seconds...")
        time.sleep(2)
        
    except Exception as e:
        print(f"ERROR: Failed to create sphere: {e}")
        import traceback
        traceback.print_exc()