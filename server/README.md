# Rover Server

## Overview
The server component runs on a Raspberry Pi attached to the rover and is responsible for:
- Motor control and propulsion
- Sensor data collection and processing
- Maintaining wireless communication with the client
- Running autonomous navigation algorithms
- Processing and responding to commands from the client

## Hardware Components
- Raspberry Pi (3B+ or 4 recommended)
- Motor controller board
- Brushless motors and ESCs for propulsion
- IMU (MPU6050) for orientation data
- Optional ultrasonic sensors for obstacle avoidance
- LiPo battery for power supply
- Voltage regulator for Raspberry Pi power

## Software Architecture

### Main Components
- **main.py**: Entry point for the server application
- **motor_controller.py**: Handles PWM signals to control motors
- **sensor_handler.py**: Processes data from IMU and other sensors
- **communication.py**: Manages WebSocket connection with clients
- **navigation.py**: Implements navigation algorithms
- **config.py**: Contains configuration parameters for the system

### Libraries and Dependencies
- **pigpio**: For precise PWM control
- **smbus**: For I2C communication with sensors
- **websockets**: For real-time communication with the client
- **numpy**: For mathematical operations
- **RPi.GPIO**: For GPIO pin control

## Installation

### Automatic Installation
Run the following command on your Raspberry Pi:
```bash
curl -sSL https://raw.githubusercontent.com/yourusername/Rover/main/install_server.sh | bash
```

### Manual Installation

1. Update your Raspberry Pi:
```bash
sudo apt update
sudo apt upgrade -y
```

2. Install required system packages:
```bash
sudo apt install -y python3-pip python3-dev python3-smbus i2c-tools git pigpio python3-pigpio
```

3. Enable I2C and other required interfaces:
```bash
sudo raspi-config nonint do_i2c 0
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

4. Clone the repository:
```bash
git clone https://github.com/yourusername/Rover.git
cd Rover/server
```

5. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

## Configuration

Configuration parameters are stored in `config.py`. Key parameters include:
- Motor pin assignments
- PWM frequency settings
- PID control parameters
- Communication settings
- Sensor calibration values

## Usage

### Starting the Server
```bash
python3 main.py
```

### Automatic Start on Boot
To configure the server to start automatically when the Raspberry Pi boots:

1. Create a systemd service:
```bash
sudo nano /etc/systemd/system/rover.service
```

2. Add the following content:
```
[Unit]
Description=Rover Control Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/Rover/server/main.py
WorkingDirectory=/home/pi/Rover/server
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl enable rover.service
sudo systemctl start rover.service
```

## Troubleshooting

### Motor Control Issues
- Check connections between the Raspberry Pi and motor controller
- Verify that the pigpio daemon is running: `sudo systemctl status pigpiod`
- Ensure proper voltage is supplied to the motors

### Communication Problems
- Check that the client and server are on the same network
- Verify that no firewall is blocking the communication port
- Restart the WebSocket server

### Sensor Issues
- Run `i2cdetect -y 1` to verify that sensors are properly connected
- Check sensor calibration in the configuration file
- Ensure proper power supply to the sensors

## Development and Extending

### Adding New Sensors
1. Create a new handler in the `sensors` directory
2. Implement the sensor reading logic
3. Register the sensor in the main sensor handler

### Modifying Control Algorithms
Navigation algorithms are defined in `navigation.py`. Key areas for customization:
- PID control parameters
- Path planning algorithms
- Obstacle avoidance logic
