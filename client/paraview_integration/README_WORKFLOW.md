# Falconia Rover Tracking Workflow

Simple 4-step workflow to track rover movement over your 3D Falconia model.

## Prerequisites

```bash
pip install opencv-python pupil-apriltags paho-mqtt
```

## Step 1: Calibrate Corners

Place AprilTags 0-3 on the corners of your physical Falconia model:
- **Tag 0**: Back-Left corner
- **Tag 1**: Back-Right corner  
- **Tag 2**: Front-Right corner
- **Tag 3**: Front-Left corner

Run calibration:
```bash
cd /home/benmross/Documents/Projects/FalconiaAPL/client/paraview_integration
python calibrate_corners.py [camera_url]
```

Press SPACE to capture each tag, ESC when done. Creates `falconia_corners.json`.

## Step 2: Open ParaView

1. Launch ParaView
2. Load your Falconia 3D model (STL/OBJ file)
3. Apply clips if needed (should see Clip1-Clip6 in pipeline)

## Step 3: Load Rover Tracking

In ParaView's Python shell:
```python
exec(open('/home/benmross/Documents/Projects/FalconiaAPL/client/paraview_integration/falconia_rover.py').read())
setup_rover_tracking()
```

## Step 4: Track Rover

Place AprilTag 4 on your rover, then repeatedly run:
```python
update_position()
```

### Manual Control
```python
# Test camera detection
test_camera()

# Set specific position
set_rover_position(0.5, 0.2, 1.0)

# Test corners
test_corners()

# Cleanup when done
cleanup()
```

## Files Created

- `calibrate_corners.py` - Corner calibration script
- `falconia_rover.py` - ParaView rover tracking script  
- `falconia_corners.json` - Corner calibration data (auto-generated)

## Usage Tips

- **Camera URL**: Default is `http://192.168.1.100:7123/stream.mjpg`
- **Rover Tag**: Uses AprilTag ID 4 for rover detection
- **Model Bounds**: Calibrated to X=±1.25, Z=±1.8, Y=0.2 hover height
- **Update Frequency**: Call `update_position()` as often as needed
- **No Loops**: ParaView can't update during long Python loops, so use manual calls

## Troubleshooting

- **No corners found**: Check AprilTag placement and lighting
- **Rover not moving**: Verify tag 42 is visible and `falconia_corners.json` exists
- **Camera issues**: Check camera URL and network connectivity
- **MQTT errors**: Ensure MQTT broker is running on localhost:1883