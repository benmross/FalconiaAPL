# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FalconiaAPL is a robotics control system consisting of a Raspberry Pi server (rover/robot) and a Python Tkinter client for remote control. The system includes real-time sensor monitoring, camera streaming, AprilTag detection, and ParaView integration for 3D visualization.

## Architecture

### Client-Server Communication
- **Communication Protocol**: MQTT over TCP
- **Default MQTT Port**: 1883
- **Topics**: 
  - `laptop_to_pi` (commands from client to server)
  - `pi_to_laptop` (sensor data and responses from server to client)

### Client Application (`client/`)
- **Main Entry Point**: `client.py` - Tkinter-based GUI application
- **Modular Panels**: Located in `client_modules/` directory
  - `connection_panel.py` - MQTT connection management
  - `controls_panel.py` - Rover movement controls
  - `camera_panel.py` - Video streaming and AprilTag detection
  - `console_panel.py` - Message logging
  - `sensor_panel.py` - Real-time sensor display
  - `settings_panel.py` - Configuration management
- **Libraries**: Custom utilities in `client/lib/`
  - `apriltag_detector.py` - AprilTag detection using pupil-apriltags
  - `log.py` - Logging utilities

### Server Application (`server/`)
- **Main Entry Point**: `main.py` - Raspberry Pi server with camera streaming and MQTT
- **Hardware Libraries**: Located in `server/lib/`
  - `accelerometer.py` - MPU6050 IMU interface
  - `drivetrain.py` - Motor control (placeholder implementation)
  - `spectral.py` - Spectral sensor interface
  - `humiture.py` - DHT11 temperature/humidity sensor
  - `log.py` - File-based logging

### ParaView Integration (`client/paraview_integration/`)
- **Real-time Tracking**: Ceiling-mounted camera system for rover position tracking
- **Key Components**:
  - `ceiling_tracker.py` - AprilTag detection from overhead camera
  - `coordinate_transform.py` - Camera-to-world coordinate mapping
  - `paraview_bridge.py` - Live rover visualization in ParaView
  - `calibration_tools.py` - Interactive calibration utilities

## Common Development Commands

### Running the System
```bash
# Start the server (on Raspberry Pi)
cd server
python3 main.py

# Start the client (on control computer)
cd client
python3 client.py
```

### ParaView Integration
```bash
# Calibrate coordinate mapping
cd client/paraview_integration
python calibration_tools.py --mode coordinate --stream http://PI_IP:7123/stream.mjpg

# Start ceiling tracker
python ceiling_tracker.py --config config/ceiling_camera_config.json

# Start ParaView bridge
python paraview_bridge.py --config config/paraview_config.json
```

### Testing
```bash
# Test individual components
cd client/paraview_integration
python test_pipeline.py --test transform
python test_pipeline.py --test mqtt

# Run full system test
python test_pipeline.py --test full --duration 60
```

## Key Dependencies

### Client Dependencies
- `tkinter` - GUI framework
- `paho-mqtt` - MQTT client
- `opencv-python` - Computer vision and camera handling
- `pupil-apriltags` - AprilTag detection
- `PIL` (Pillow) - Image processing
- `numpy` - Numerical operations

### Server Dependencies
- `paho-mqtt` - MQTT client
- `picamera2` - Raspberry Pi camera interface
- `RPi.GPIO` - GPIO control
- `numpy` - Numerical operations

### ParaView Integration Dependencies
- `opencv-python` - Computer vision
- `pupil-apriltags` - AprilTag detection
- `paho-mqtt` - MQTT communication
- `scipy` - Scientific computing
- `paraview` - 3D visualization

## Configuration Files

### Client Configuration
- `client/rover_config.json` - Main client configuration
- `client/blimp_config.json` - Alternative configuration file
- Configuration includes MQTT ports, camera settings, refresh rates, and key bindings

### Server Configuration
- Hardware settings are primarily in the library files
- Camera streaming on port 7123 by default
- MQTT broker runs locally on the Pi

### ParaView Integration Configuration
- `config/ceiling_camera_config.json` - Ceiling tracker settings
- `config/paraview_config.json` - ParaView bridge configuration  
- `config/coordinate_mapping.json` - Calibration data storage

## Hardware Interfaces

### Sensors (server/lib/)
- **MPU6050**: Accelerometer/gyroscope via I2C
- **DHT11**: Temperature/humidity sensor
- **Spectral Sensor**: Color/light sensing
- **Camera**: Pi Camera via picamera2 library

### Actuators
- **Motor Control**: GPIO-based control (implementation in `drivetrain.py` is currently placeholder)

## Data Formats

### MQTT Message Types
- **Sensor Data**: JSON format with "type": "sensor_data"
- **Humiture Data**: JSON format with "type": "humiture_data"  
- **Spectral Data**: JSON format with "type": "spectral_data"
- **AprilTag Data**: JSON format with "type": "apriltag_data"
- **Commands**: Simple string commands (forward, backward, left, right, stop, etc.)

## Camera Streaming
- **Protocol**: MJPEG over HTTP
- **Default Port**: 7123
- **URL Format**: `http://<PI_IP>:7123/stream.mjpg`
- **Resolution**: 640x480 (configurable in server/main.py)

## AprilTag Detection
- **Tag Family**: tag36h11
- **Libraries**: pupil-apriltags for detection
- **Pose Estimation**: 6DOF pose calculation with camera calibration
- **Applications**: Robot tracking, navigation, ParaView visualization

## Development Notes

- The server drivetrain implementation is currently a placeholder - actual motor control needs to be implemented
- Camera calibration parameters in AprilTag detector are placeholder values
- The system supports multiple rovers through different AprilTag IDs
- All timestamp-based logging uses local time formatting
- GUI panels are modular and can be easily extended or modified