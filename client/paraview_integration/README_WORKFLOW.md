# Falconia High-Performance Rover Tracking

Fast background service + ParaView workflow for real-time rover tracking over 3D Falconia model.

## Prerequisites

```bash
pip install opencv-python pupil-apriltags paho-mqtt
```

## Step 1: Calibrate Corners

Click on the 4 corners of your physical Falconia model in the camera stream:

Run calibration:
```bash
cd /home/benmross/Documents/Projects/FalconiaAPL/client/paraview_integration
python calibrate_corners.py [camera_url]
```

Click on corners in this order:
1. **Top-Left** corner (-X, -Z in ParaView)
2. **Top-Right** corner (+X, -Z in ParaView)  
3. **Bottom-Right** corner (+X, +Z in ParaView)
4. **Bottom-Left** corner (-X, +Z in ParaView)

Creates `falconia_corners.json` automatically when all 4 corners are clicked.

## Step 2: Open ParaView

1. Launch ParaView
2. Load your Falconia 3D model (STL/OBJ file)
3. Apply clips if needed (should see Clip1-Clip6 in pipeline)

## Step 3: Start Background Service

Start the rover tracking service (runs continuously):
```bash
./start_rover_service.sh
```

This service:
- Detects AprilTag 4 at 20Hz
- Transforms coordinates automatically  
- Publishes to MQTT `rover/position`

## Step 4: Fast ParaView Tracking

In ParaView's Python shell:
```python
exec(open('falconia_rover_fast.py').read())
setup_fast_tracking()
```

## Step 5: Update Rover (Super Fast!)

```python
update_position()  # Instant updates from MQTT!
```

### Manual Control
```python
# Check connection status
show_status()

# Set specific position  
set_rover_position(0.5, 0.2, 1.0)

# Cleanup when done
cleanup()
```

## Files in Clean Workflow

- `calibrate_corners.py` - Click-based corner calibration
- `rover_tracker_service.py` - Background AprilTag detection service
- `falconia_rover_fast.py` - Fast ParaView MQTT-only script
- `start_rover_service.sh` - Service startup script
- `falconia_corners.json` - Corner calibration data (auto-generated)

## Usage Tips

- **Camera URL**: Default is `http://192.168.1.100:7123/stream.mjpg`
- **Rover Tag**: Uses AprilTag ID 4 for rover detection  
- **Corner Calibration**: Manual clicking (no AprilTags needed for corners)
- **Model Bounds**: Calibrated to X=±1.25, Z=±1.8, Y=0.2 hover height
- **Update Frequency**: Call `update_position()` as often as needed
- **No Loops**: ParaView can't update during long Python loops, so use manual calls

## Troubleshooting

- **No corners found**: Check AprilTag placement and lighting
- **Rover not moving**: Verify tag 42 is visible and `falconia_corners.json` exists
- **Camera issues**: Check camera URL and network connectivity
- **MQTT errors**: Ensure MQTT broker is running on localhost:1883