#!/usr/bin/env python3
"""
Simple ParaView Rover Test - Run in ParaView Python Shell
Creates a moving sphere to test basic functionality
"""

from paraview.simple import *
import threading
import time
import math

# Global variables
rover_source = None
rover_rep = None
running = False
update_thread = None

def create_rover():
    """Create a simple moving rover sphere"""
    global rover_source, rover_rep
    
    # Create sphere
    rover_source = Sphere()
    rover_source.Radius = 0.1
    rover_source.Center = [0, 0, 0]
    
    # Show in current view
    rover_rep = Show(rover_source)
    rover_rep.DiffuseColor = [1.0, 0.0, 0.0]  # Red
    
    # Render
    Render()
    print("Red rover sphere created!")

def update_position():
    """Update rover position in a circle"""
    global rover_source, running
    
    t = 0
    while running:
        # Circular motion
        x = math.cos(t) * 0.5
        y = math.sin(t) * 0.5
        z = 0.1
        
        rover_source.Center = [x, y, z]
        Render()
        
        t += 0.1
        time.sleep(0.1)

def start_movement():
    """Start the rover movement"""
    global running, update_thread
    
    running = True
    update_thread = threading.Thread(target=update_position)
    update_thread.daemon = True
    update_thread.start()
    print("Rover movement started!")

def stop_movement():
    """Stop the rover movement"""
    global running
    running = False
    print("Rover movement stopped!")

def test_rover():
    """Complete test - create and start moving rover"""
    create_rover()
    start_movement()
    print("Test rover active! Call stop_movement() to stop.")

# Run the test
test_rover()