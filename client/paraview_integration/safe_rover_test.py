#!/usr/bin/env python3
"""
Safe ParaView Rover Test - No threading, manual updates
Run in ParaView Python Shell
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
mqtt_client = None
latest_position = [0, 0, 0.1]

def create_rover():
    """Create a simple rover sphere"""
    global rover_source, rover_rep
    
    # Create sphere
    rover_source = Sphere()
    rover_source.Radius = 0.1
    rover_source.Center = [0, 0, 0.1]
    
    # Show in current view
    rover_rep = Show(rover_source)
    rover_rep.DiffuseColor = [1.0, 0.0, 0.0]  # Red
    rover_rep.Opacity = 1.0
    
    # Render
    Render()
    print("Red rover sphere created at origin!")
    return True

def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    """MQTT connection callback"""
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe("rover/position")
        print("Subscribed to rover/position")
    else:
        print(f"Failed to connect to MQTT, code {rc}")

def on_mqtt_message(client, userdata, msg):
    """Handle MQTT position messages"""
    global latest_position
    try:
        data = json.loads(msg.payload.decode())
        pos = data["position"]
        # Scale and offset the position
        latest_position = [
            pos["x"] * 0.5,  # Scale down
            pos["y"] * 0.5,
            pos["z"] + 0.1   # Lift off ground
        ]
        print(f"New position: {latest_position}")
    except Exception as e:
        print(f"Error parsing MQTT: {e}")

def setup_mqtt():
    """Setup MQTT connection"""
    global mqtt_client
    
    if not MQTT_AVAILABLE:
        print("MQTT not available")
        return False
        
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    
    try:
        mqtt_client.connect("localhost", 1883, 60)
        mqtt_client.loop_start()
        print("MQTT setup complete")
        return True
    except Exception as e:
        print(f"MQTT connection failed: {e}")
        return False

def update_rover_position():
    """Update rover position manually (call this repeatedly)"""
    global rover_source, latest_position
    
    if rover_source is not None:
        rover_source.Center = latest_position
        Render()
        return True
    return False

def start_rover_tracking():
    """Start complete rover tracking system"""
    print("=== Starting Safe Rover Tracking ===")
    
    # Create visual rover
    if not create_rover():
        return False
        
    # Setup MQTT
    if not setup_mqtt():
        print("MQTT failed, will use manual testing")
        
    print("=== Rover tracking active ===")
    print("To update manually: update_rover_position()")
    print("To test movement: test_movement()")
    return True

def test_movement():
    """Test movement without MQTT"""
    global latest_position
    import math
    
    print("Testing manual movement...")
    for i in range(20):
        t = i * 0.3
        latest_position = [
            math.cos(t) * 0.3,
            math.sin(t) * 0.3,
            0.1
        ]
        update_rover_position()
        time.sleep(0.1)
    print("Test movement complete")

def stop_tracking():
    """Stop tracking and cleanup"""
    global mqtt_client
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    print("Tracking stopped")

# Auto-start
print("Safe Rover Tracking loaded.")
print("Call: start_rover_tracking()")
print("Then: update_rover_position() repeatedly to see movement")
print("Or: test_movement() for a demo")