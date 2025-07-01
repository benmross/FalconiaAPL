#!/bin/bash
# FalconiaAPL Presentation Demo - Desktop mode first, then try VR
echo "Starting FalconiaAPL Presentation Demo..."

# Configuration
PARAVIEW_PATH="/home/benmross/paraview-build/build/bin/paraview"

# Variables to track background processes
MOCK_PID=""
MOSQUITTO_STARTED=false

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down presentation demo..."
    
    # Kill background processes if they exist
    if [ ! -z "$MOCK_PID" ]; then
        echo "Stopping mock rover simulation..."
        kill $MOCK_PID 2>/dev/null
        wait $MOCK_PID 2>/dev/null
    fi
    
    # Stop mosquitto if we started it
    if [ "$MOSQUITTO_STARTED" = true ]; then
        echo "Stopping MQTT broker..."
        pkill mosquitto 2>/dev/null
    fi
    
    echo "✅ Presentation demo stopped."
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

# Start mock rover simulation
echo "Starting mock rover simulation..."
python test_pipeline.py --test full --duration 600 &
MOCK_PID=$!
sleep 2

echo "========================================"
echo "🌍 FALCONIA ROVER DEMO SETUP"
echo "========================================"
echo "1. ParaView will open shortly"
echo "2. LOAD YOUR FALCONIA 3D SCAN FIRST"
echo "3. In ParaView Python Shell (View → Python Shell):"
echo "   exec(open('/home/benmross/Documents/Projects/FalconiaAPL/client/paraview_integration/clean_rover_demo.py').read())"
echo "4. Run: start_demo()" 
echo "5. Run: while auto_update(): pass"
echo "6. You'll see red rover moving over Falconia with orange trail"
echo ""
echo "🎯 FOR VR (after loading model):"
echo "   Tools → Manage Plugins → XRInterface → Load"
echo "   View → XR Actions → Start XR"
echo ""
echo "Mock rover running circular pattern for 10 minutes"
echo "Press Ctrl+C to stop everything"
echo "========================================"

# Launch ParaView in safe mode (no immediate XR)
echo "Press Ctrl+C to stop all processes gracefully"
echo ""

# Run ParaView (this will block until ParaView exits)
$PARAVIEW_PATH

# Cleanup on normal exit (ParaView closed normally)
cleanup