#!/bin/bash
# FalconiaAPL VR Demo Mode - Uses simulated rover data
# Run this when you don't have access to the ceiling camera

echo "Starting FalconiaAPL VR Demo System..."

# Configuration
PARAVIEW_PATH="/home/benmross/paraview-build/build/bin/paraview"

# Variables to track background processes
MOCK_PID=""
BRIDGE_PID=""
MOSQUITTO_STARTED=false

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down VR demo system..."
    
    # Kill background processes if they exist
    if [ ! -z "$MOCK_PID" ]; then
        echo "Stopping mock rover simulation..."
        kill $MOCK_PID 2>/dev/null
        wait $MOCK_PID 2>/dev/null
    fi
    
    if [ ! -z "$BRIDGE_PID" ]; then
        echo "Stopping ParaView bridge..."
        kill $BRIDGE_PID 2>/dev/null
        wait $BRIDGE_PID 2>/dev/null
    fi
    
    # Stop mosquitto if we started it
    if [ "$MOSQUITTO_STARTED" = true ]; then
        echo "Stopping MQTT broker..."
        pkill mosquitto 2>/dev/null
    fi
    
    echo "✅ VR demo system stopped."
    exit 0
}

# Set up signal handler for graceful shutdown
trap cleanup SIGINT SIGTERM

# Start MQTT broker if not running
if ! pgrep -x "mosquitto" > /dev/null; then
    echo "Starting MQTT broker..."
    mosquitto -d
    MOSQUITTO_STARTED=true
    sleep 2
fi

# Change to paraview integration directory
cd client/paraview_integration

# Start mock rover simulation (circular pattern)
echo "Starting mock rover simulation..."
python test_pipeline.py --test full --duration 300 &
MOCK_PID=$!
sleep 2

# Start ParaView bridge
echo "Starting ParaView bridge..."
python paraview_bridge.py --config config/paraview_config.json &
BRIDGE_PID=$!
sleep 2

# Launch ParaView
echo "Launching ParaView..."
echo "Load your 3D scan, then Tools → Manage Plugins → XRInterface → Load"
echo "Then View → XR Actions → Start XR"
echo "Press Ctrl+C to stop all processes gracefully"
echo ""

# Run ParaView (this will block until ParaView exits)
$PARAVIEW_PATH

# Cleanup on normal exit (ParaView closed normally)
cleanup