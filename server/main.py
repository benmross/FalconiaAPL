from time import sleep
import paho.mqtt.client as mqtt
import json
import threading
import io
import logging
import socketserver
from http import server
from threading import Condition
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from lib import accelerometer as mpu, log, drivetrain, spectral, humiture
from libcamera import Transform
"""
Notes:
Custom libraries are located at ./lib/ and can be viewed as documentation
Max polling rate for Gyroscope/Accelerometer (MPU6050) is 500Hz
"""

# MQTT configuration
BROKER = "localhost"  # Use localhost for the MQTT broker on the Pi
PORT = 1883
TOPIC_SEND = "pi_to_laptop"
TOPIC_RECEIVE = "laptop_to_pi"
mqtt_client = None
running = True

# Camera streaming configuration
CAMERA_PORT = 7123

# HTML page for camera streaming
PAGE = """\
<html>
<head>
</head>
<body>
<img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_camera_server():
    """Initialize and start the camera streaming server in a separate thread"""
    global output, picam2
    
    try:
        log.log("Starting camera server...")
        picam2 = Picamera2()
        picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}, transform=Transform(hflip=1, vflip=1)))
        output = StreamingOutput()
        picam2.start_recording(JpegEncoder(), FileOutput(output))
        
        address = ('', CAMERA_PORT)
        server = StreamingServer(address, StreamingHandler)
        
        # Start server in a thread
        camera_thread = threading.Thread(target=server.serve_forever)
        camera_thread.daemon = True
        camera_thread.start()
        
        log.log(f"Camera server started on port {CAMERA_PORT}")
        return True
    except Exception as e:
        log.log(f"Error starting camera server: {e}")
        return False


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when MQTT client connects"""
    if rc == 0:
        log.log("Connected to MQTT broker")
        client.subscribe(TOPIC_RECEIVE)
    else:
        log.log(f"Failed to connect to MQTT broker with code {rc}")


def on_message(client, userdata, msg):
    """Handle commands from the laptop client"""
    command = msg.payload.decode()
    log.log(f"Received command: {command}")
    
    if command == "calibrate":
        # Perform calibration
        mpu.calibrate()
        client.publish(TOPIC_SEND, "Calibration complete")
    elif command == "spectral":
        # Collect spectral data
        spec_data = spectral.collect()
        if spec_data:
            # Create data packet
            data_packet = {
                "type": "spectral_data",
                "data": spec_data
            }
            # Send data via MQTT
            client.publish(TOPIC_SEND, json.dumps(data_packet))
        else:
            client.publish(TOPIC_SEND, "Failed to collect spectral data")
    elif command == "humiture":
        # Control code for down movement
        dht11_data = humiture.collect()
        if dht11_data:
            # Create data packet
            data_packet = {
                "type": "humiture_data",
                "data": dht11_data
            }
            # Send data via MQTT
            client.publish(TOPIC_SEND, json.dumps(data_packet))
        else:
            client.publish(TOPIC_SEND, "Failed to collect humiture data")
    elif command == "left":
        # Control code for left movement
        drivetrain.left()
        client.publish(TOPIC_SEND, "Moving left")
    elif command == "right":
        # Control code for right movement
        drivetrain.right()
        client.publish(TOPIC_SEND, "Moving right")
    elif command == "forward":
        # Control code for forward movement
        drivetrain.forward()
        client.publish(TOPIC_SEND, "Moving forward")
    elif command == "backward":
        # Control code for backward movement
        drivetrain.backward()
        client.publish(TOPIC_SEND, "Moving backward")
    elif command == "stop":
        # Stop all movements
        drivetrain.stop()
        client.publish(TOPIC_SEND, "Stopped all movement")
    else:
        client.publish(TOPIC_SEND, f"Unknown command: {command}")


def start_mqtt():
    """Start the MQTT client"""
    global mqtt_client
    
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_message = on_message
    mqtt_client.on_connect = on_connect
    
    try:
        mqtt_client.connect(BROKER, PORT, 60)
        mqtt_client.loop_start()
        return True
    except Exception as e:
        log.log(f"MQTT connection error: {e}")
        return False


def send_sensor_data():
    """Send sensor data via MQTT in a loop"""
    global mqtt_client, running
    
    while running:
        try:
            # Get sensor readings
            accel = mpu.getAcceleration()
            gyro = mpu.getGyro()
            temp = mpu.getTemp()
            
            # Create data packet
            sensor_data = {
                "type": "sensor_data",
                "accelerometer": accel,
                "gyroscope": gyro,
                "temperature": temp
            }
            
            # Send data via MQTT
            if mqtt_client:
                mqtt_client.publish(TOPIC_SEND, json.dumps(sensor_data))
            
            # Log locally (optional)
            log.log(accel)
            
            # Sleep for polling rate (adjust as needed)
            sleep(0.1)  # 10Hz - balanced between responsiveness and bandwidth
            
        except Exception as e:
            log.log(f"Error sending sensor data: {e}")
            sleep(1)  # Wait before retrying


def cleanup():
    """Clean up resources"""
    global mqtt_client, running, picam2
    
    running = False
    
    # Stop MQTT
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    
    # Stop camera
    try:
        picam2.stop_recording()
    except:
        pass
    
    # Clean up GPIO
    try:
        GPIO.cleanup()
    except:
        pass


def main():
    """Main function"""
    try:
        # Calibrate MPU6050 if needed
        # mpu.calibrate()  # Uncomment to calibrate on startup
        
        # Start camera streaming server
        if start_camera_server():
            log.log("Camera server started successfully")
        else:
            log.log("Warning: Failed to start camera server")
        
        # Start MQTT client
        if start_mqtt():
            log.log("MQTT started successfully")
            
            # Start sensor data thread
            sensor_thread = threading.Thread(target=send_sensor_data)
            sensor_thread.daemon = True
            sensor_thread.start()
            
            log.log("Server running. Press Ctrl+C to exit.")
            
            # Keep the main thread alive
            while True:
                sleep(1)
                
    except KeyboardInterrupt:
        log.log("Server stopping...")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
