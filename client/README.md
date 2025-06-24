# Rover Client

## Overview
The client application provides a user-friendly interface for controlling and monitoring the Rover platform. It communicates with the Raspberry Pi server via WebSocket, allowing real-time control and data visualization.

## Features
- Real-time control of the rover using intuitive controls
- Live telemetry display showing orientation, altitude, and battery status
- Video streaming from the rover's camera (if equipped)
- Autonomous navigation command interface
- Connection status monitoring
- Configuration options for control sensitivity and behavior

## Software Architecture

### Main Components
- **index.html**: Main entry point for the web application
- **js/main.js**: Core client application logic
- **js/controller.js**: Handles user input for rover control
- **js/communication.js**: Manages WebSocket communication with the server
- **js/telemetry.js**: Processes and displays sensor data
- **css/styles.css**: Styling for the user interface

### Libraries and Dependencies
- **Bootstrap**: For responsive UI components
- **Chart.js**: For real-time data visualization
- **Socket.io-client**: For WebSocket communication
- **Three.js**: For 3D visualization of rover orientation
- **gamepad.js**: For optional gamepad controller support

## Installation

### Automatic Installation
Run the following command on your computer:
```bash
curl -sSL https://raw.githubusercontent.com/yourusername/Rover/main/install_client.sh | bash
```

### Manual Installation

#### Prerequisites
- Node.js (v14.0.0 or higher)
- npm (v6.0.0 or higher)

#### Steps
1. Clone the repository:
```bash
git clone https://github.com/yourusername/Rover.git
cd Rover/client
```

2. Install dependencies:
```bash
npm install
```

3. Build the client application:
```bash
npm run build
```

4. Start the development server:
```bash
npm start
```

## Usage

### Connecting to the Rover
1. Ensure the rover server is running on the Raspberry Pi
2. Open the client application in a web browser
3. Enter the IP address of the Raspberry Pi in the connection dialog
4. Click "Connect" to establish a connection

### Control Interface

#### Keyboard Controls
- **W/S**: Forward/Backward thrust
- **A/D**: Left/Right rotation
- **Q/E**: Left/Right lateral movement
- **R/F**: Ascend/Descend
- **Space**: Emergency stop (halts all motors)
- **T**: Toggle autonomous mode
- **C**: Calibrate sensors

#### Touch Controls
- Use the virtual joysticks for directional control
- Buttons for special functions are located at the bottom of the screen

### Telemetry Display
The telemetry panel shows:
- Current orientation (pitch, roll, yaw)
- Altitude (if altitude sensor is equipped)
- Battery voltage and estimated remaining time
- Motor power levels
- Connection status and latency

### Settings
Click the gear icon to access settings:
- Control sensitivity adjustment
- Display preferences
- Connection parameters
- Video streaming quality (if applicable)

## Development and Customization

### Building from Source
```bash
npm run build
```

### Running in Development Mode
```bash
npm run dev
```

### Adding New Features
The client application is structured using a modular approach:

1. To add new control modes:
   - Extend the Controller class in `controller.js`
   - Register the new control mode in the UI

2. To add new telemetry displays:
   - Create a new visualization component
   - Subscribe to the relevant data streams in `telemetry.js`

3. To modify the communication protocol:
   - Update the message handlers in `communication.js`
   - Ensure corresponding changes are made in the server code

### Testing
Run the test suite with:
```bash
npm test
```

## Troubleshooting

### Connection Issues
- Ensure the Raspberry Pi and client device are on the same network
- Check that the correct IP address and port are being used
- Verify that the server is running on the Raspberry Pi

### Control Problems
- Check that the browser supports all required features
- Try refreshing the page to reset the WebSocket connection
- Ensure that no other clients are simultaneously controlling the rover

### Display Issues
- Make sure your browser is updated to the latest version
- Try disabling browser extensions that might interfere with WebGL or Canvas
- Adjust the display settings to reduce CPU/GPU load if performance is poor
