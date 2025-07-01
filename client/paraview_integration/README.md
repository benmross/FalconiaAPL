# Live Rover Tracking in ParaView

This system provides real-time rover position tracking and visualization in ParaView using ceiling-mounted AprilTag detection.

## Overview

The system consists of four main components:

1. **Ceiling Tracker** (`ceiling_tracker.py`) - Detects AprilTags from ceiling-mounted camera
2. **Coordinate Transform** (`coordinate_transform.py`) - Maps camera coordinates to world coordinates  
3. **Calibration Tools** (`calibration_tools.py`) - Interactive calibration utilities
4. **ParaView Bridge** (`paraview_bridge.py`) - Displays live rover position in ParaView

## Quick Start

### 1. Install Dependencies

```bash
pip install opencv-python pupil-apriltags paho-mqtt numpy scipy
# For ParaView integration:
pip install paraview  # or use system ParaView with Python support
```

### 2. Hardware Setup

- Mount Raspberry Pi with camera on ceiling overlooking rover area
- Attach AprilTag (tag36h11 family) to top of rover
- Ensure network connectivity between ceiling Pi, control computer, and ParaView workstation

### 3. Calibration

#### Camera Calibration (Optional)
```bash
# Capture checkerboard images for camera calibration
python calibration_tools.py --mode camera --images /path/to/checkerboard/images
```

#### Coordinate Mapping Calibration
```bash
# Interactive calibration using known reference points
python calibration_tools.py --mode coordinate --stream http://CEILING_PI_IP:7123/stream.mjpg

# OR using AprilTags at known positions
python calibration_tools.py --mode apriltag --stream http://CEILING_PI_IP:7123/stream.mjpg
```

### 4. Running the System

#### Start Ceiling Tracker (on ceiling Pi)
```bash
python ceiling_tracker.py --config config/ceiling_camera_config.json
```

#### Start ParaView Bridge (on visualization computer)
```bash
python paraview_bridge.py --config config/paraview_config.json
```

#### Load Your ParaView Scene
1. Open ParaView and load your exoplanet mockup data
2. Save the state file
3. Update `paraview_config.json` with the path to your state file

## Configuration

### Ceiling Camera Configuration (`config/ceiling_camera_config.json`)

```json
{
  "camera_url": "http://192.168.1.100:7123/stream.mjpg",
  "mqtt_broker": "localhost",
  "mqtt_topic": "rover/position",
  "target_tag_id": null,
  "ceiling_height": 2.5,
  "tag_size": 0.15,
  "detection_rate": 30,
  "coordinate_transform": {
    "enabled": true,
    "scale_x": 1.0,
    "scale_y": 1.0,
    "offset_x": 0.0,
    "offset_y": 0.0,
    "rotation": 0.0
  }
}
```

### ParaView Configuration (`config/paraview_config.json`)

```json
{
  "mqtt_broker": "localhost",
  "mqtt_topic": "rover/position",
  "paraview_file": "/path/to/your/exoplanet_scene.pvsm",
  "rover_marker": {
    "size": 0.05,
    "color": [1.0, 0.0, 0.0],
    "opacity": 1.0
  },
  "trail": {
    "enabled": true,
    "max_points": 100,
    "color": [1.0, 0.5, 0.0]
  },
  "coordinate_offset": [0.0, 0.0, 0.0],
  "coordinate_scale": [1.0, 1.0, 1.0]
}
```

## Calibration Process

### Manual Coordinate Mapping
1. Run calibration tool: `python calibration_tools.py --mode coordinate`
2. Click on 4+ reference points in the camera view
3. Enter corresponding world coordinates for each point
4. Press 'c' to calculate homography transformation
5. Press 's' to save calibration

### AprilTag-Based Calibration  
1. Place AprilTags at known positions in the rover area
2. Run: `python calibration_tools.py --mode apriltag`
3. Position tags are automatically detected and mapped
4. More accurate than manual calibration

## Testing

### Test Individual Components
```bash
# Test coordinate transformation
python test_pipeline.py --test transform

# Test MQTT communication  
python test_pipeline.py --test mqtt
```

### Test Complete Pipeline
```bash
# Run mock rover simulation
python test_pipeline.py --test full --duration 60
```

This will start a simulated rover moving in patterns and publishing position data via MQTT.

## Troubleshooting

### No AprilTag Detection
- Check camera focus and lighting
- Verify AprilTag is tag36h11 family
- Adjust `tag_size` parameter to match physical tag size
- Check camera calibration parameters

### Coordinate Mapping Issues
- Ensure at least 4 reference points for calibration
- Use reference points that span the full rover workspace
- Check for lens distortion - perform camera calibration first
- Validate calibration with known test positions

### MQTT Connection Problems
- Verify MQTT broker is running (`mosquitto` or similar)
- Check network connectivity between components
- Ensure consistent MQTT topic names across all components
- Check firewall settings

### ParaView Integration Issues
- Ensure ParaView has Python support enabled
- Check ParaView Python path includes required modules
- Try simulation mode first: `python paraview_bridge.py --sim-mode`
- Verify ParaView state file path is correct

## Architecture Details

### Data Flow
1. Ceiling camera captures video stream
2. AprilTag detector finds rover tags in each frame
3. Coordinate transformer maps camera pixels to world coordinates
4. Position data published via MQTT
5. ParaView bridge receives position updates
6. Red dot marker updated in ParaView scene

### Coordinate Systems
- **Camera coordinates**: Pixel positions in camera image
- **World coordinates**: Physical positions in rover workspace (meters)
- **ParaView coordinates**: Scene coordinates (may require offset/scaling)

### Position Filtering
- Exponential smoothing filter reduces position jitter
- Configurable filter strength via `position_filter_alpha`
- Timeout handling for temporary tag occlusion

## Performance Optimization

- **Detection Rate**: 30Hz typically sufficient, reduce if CPU limited
- **Position Filtering**: Increase alpha for more responsive tracking
- **Trail Length**: Reduce `max_points` for better performance
- **Network**: Use wired connection for consistent MQTT delivery

## File Structure

```
paraview_integration/
├── ceiling_tracker.py          # Main tracking service
├── coordinate_transform.py     # Coordinate mapping utilities
├── calibration_tools.py        # Interactive calibration
├── paraview_bridge.py          # ParaView visualization
├── test_pipeline.py            # Testing utilities
└── README.md                   # This file

config/
├── ceiling_camera_config.json  # Ceiling tracker settings
├── paraview_config.json        # ParaView bridge settings
├── coordinate_mapping.json     # Calibration data
└── test_config.json            # Test configuration
```

## Advanced Usage

### Multiple Rovers
- Use different `target_tag_id` values for each rover
- Run separate ceiling tracker instances
- Configure multiple markers in ParaView bridge

### High-Precision Tracking
- Perform camera calibration with checkerboard pattern
- Use more reference points for coordinate mapping
- Enable distortion correction in coordinate transform
- Reduce position filter alpha for more responsive tracking

### Custom Movement Patterns
- Modify `test_pipeline.py` for custom rover simulation
- Add new movement patterns in `MockRoverTracker.update_position()`
- Use for testing specific rover behaviors

## Support

For issues or questions:
1. Check troubleshooting section above
2. Verify all dependencies are installed correctly  
3. Test individual components before running full pipeline
4. Check log output for specific error messages