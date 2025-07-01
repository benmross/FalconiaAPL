#!/bin/bash
"""
Start Falconia Rover Tracking Background Service
"""

cd "$(dirname "$0")"

echo "🚀 Starting Falconia Rover Tracking Service"
echo "=========================================="
echo "📹 Camera: http://192.168.0.11:7123/stream.mjpg"
echo "📡 MQTT: localhost:1883 → rover/position"
echo "🎯 Looking for AprilTag ID 4"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 rover_tracker_service.py \
    --config falconia_corners.json \
    --mqtt-broker localhost \
    --mqtt-port 1883