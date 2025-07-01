#!/bin/bash
# FalconiaAPL VR Tracking System Startup Script

echo "Starting FalconiaAPL VR Tracking System..."

# Configuration
CEILING_PI_IP="192.168.1.100"  # Update with actual IP
PARAVIEW_PATH="/home/benmross/paraview-build/build/bin/paraview"

# Start MQTT broker if not running
if ! pgrep -x "mosquitto" > /dev/null; then
    echo "Starting MQTT broker..."
    mosquitto -d
    sleep 2
fi

# Change to paraview integration directory
cd client/paraview_integration

# Start ceiling tracker
echo "Starting ceiling tracker..."
python ceiling_tracker.py --config config/ceiling_camera_config.json &
TRACKER_PID=$!
sleep 2

# Start ParaView bridge
echo "Starting ParaView bridge..."
python paraview_bridge.py --config config/paraview_config.json &
BRIDGE_PID=$!
sleep 2

# Launch ParaView
echo "Launching ParaView..."
echo "Please load your 3D scan and enable XR Interface plugin"
$PARAVIEW_PATH

# Cleanup on exit
echo "Shutting down..."
kill $TRACKER_PID $BRIDGE_PID 2>/dev/null

echo "VR tracking system stopped."