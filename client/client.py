import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import json
import os
import cv2
import numpy as np
from PIL import Image, ImageTk

# Import module panels
from client_modules.connection_panel import ConnectionPanel
from client_modules.controls_panel import ControlsPanel
from client_modules.camera_panel import CameraPanel
from client_modules.console_panel import ConsolePanel
from client_modules.sensor_panel import SensorPanel
from client_modules.sensor_tab import SensorTabPanel
from client_modules.settings_panel import SettingsPanel
from client_modules.model_info_panel import AprilTagPanel

class RoverControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rover Remote Control")
        self.root.geometry("1280x720")
        
        # Config file path
        self.config_file = "./client/rover_config.json"
        
        # Stream variables
        self.stream_active = False
        self.capture = None
        
        # MQTT variables
        self.mqtt_client = None
        self.mqtt_connected = False
        self.MQTT_PORT = 1883
        self.TOPIC_SEND = "laptop_to_pi"
        self.TOPIC_RECEIVE = "pi_to_laptop"
        
        # Camera variables
        self.CAMERA_PORT = 7123
        self.CAMERA_REFRESH_RATE = 10  # milliseconds
        
        # Sensor variables
        self.SENSOR_REFRESH_RATE = 100  # milliseconds
        self.accel_data = [0, 0, 0]
        self.gyro_data = [0, 0, 0]
        self.temp_data = 0
        self.humiture_data = {"temperature_c": 0, "humidity": 0}
        self.spectral_data = {"violet": 0, "blue": 0, "green": 0, "yellow": 0, "orange": 0, "red": 0}
        
        # AprilTag data
        self.detected_tags = []
        self.apriltag_enabled = True
        self.APRILTAG_REFRESH_RATE = 500  # milliseconds
        
        # Load settings if available
        self.load_config()
        
        # Main horizontal paned window for resizable left and right sections
        main_paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left Frame (Connection & Controls)
        left_frame = tk.Frame(main_paned_window, width=250)
        main_paned_window.add(left_frame, minsize=325)
        
        # Initialize panels on left side
        self.connection_panel = ConnectionPanel(left_frame, self)
        self.controls_panel = ControlsPanel(left_frame, self)
        
        # Right Frame (Camera, 3D Model, and Info)
        right_frame = tk.Frame(main_paned_window)
        main_paned_window.add(right_frame, minsize=400)
        
        # Vertical paned window for tab control and model/info panels
        right_paned_window = tk.PanedWindow(right_frame, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        right_paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Tab Control (Top Right: Camera, Settings, Console, Sensors)
        tab_control = ttk.Notebook(right_paned_window)
        right_paned_window.add(tab_control, height=480, sticky=tk.NSEW)
        
        # Create tabs
        camera_tab = tk.Frame(tab_control)
        settings_tab = tk.Frame(tab_control)
        console_tab = tk.Frame(tab_control)
        sensor_tab = tk.Frame(tab_control)
        
        tab_control.add(camera_tab, text="Camera")
        tab_control.add(settings_tab, text="Settings")
        tab_control.add(console_tab, text="Console")
        tab_control.add(sensor_tab, text="Sensors")
        
        # Initialize panel modules for each tab
        self.camera_panel = CameraPanel(camera_tab, self)
        self.settings_panel = SettingsPanel(settings_tab, self)
        self.console_panel = ConsolePanel(console_tab, self)
        self.sensor_tab_panel = SensorTabPanel(sensor_tab, self)
        
        # Bottom right panel for april tag and sensor info
        bottom_frame = tk.Frame(right_paned_window)
        right_paned_window.add(bottom_frame, height=150, sticky=tk.NSEW)
        
        # Horizontal paned window for april tag info and sensor panels
        bottom_paned_window = tk.PanedWindow(bottom_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        bottom_paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Initialize april tag panel
        tag_frame = tk.Frame(bottom_paned_window)
        bottom_paned_window.add(tag_frame, width=400)
        self.april_tag_panel = AprilTagPanel(tag_frame, self)
        
        # Initialize sensor panel for compact display
        sensor_frame = tk.Frame(bottom_paned_window)
        bottom_paned_window.add(sensor_frame, width=300)
        self.sensor_panel = SensorPanel(sensor_frame, self)
        
        # Start the april tag update cycle
        self.update_april_tag_display()
        
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                # Load ports
                self.MQTT_PORT = config.get('mqtt_port', 1883)
                self.CAMERA_PORT = config.get('camera_port', 7123)
                
                # Load refresh rates
                self.CAMERA_REFRESH_RATE = config.get('camera_refresh_rate', 10)
                self.SENSOR_REFRESH_RATE = config.get('sensor_refresh_rate', 100)
                self.APRILTAG_REFRESH_RATE = config.get('apriltag_refresh_rate', 500)
                
                self.log_to_console(f"Configuration loaded from {self.config_file}")
            else:
                # Create default config if it doesn't exist
                default_config = {
                    'mqtt_port': 1883,
                    'camera_port': 7123,
                    'camera_refresh_rate': 10,
                    'sensor_refresh_rate': 100,
                    'apriltag_refresh_rate': 500,
                    'key_bindings': {
                        "Forward": "w",
                        "Backward": "s",
                        "Left": "a",
                        "Right": "d",
                        "Spectral": "e",
                        "Humiture": "q",
                        "Stop": "x"
                    }
                }
                
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                
                self.log_to_console(f"Created default configuration in {self.config_file}")
        except Exception as e:
            print(f"Error loading configuration: {e}")
            self.log_to_console(f"Error loading configuration: {e}")
    
    def update_april_tag_display(self):
        """Update the April Tag display with currently detected tags"""
        if hasattr(self, 'camera_panel'):
            # Get current tags from camera panel
            tags = self.camera_panel.current_tags
            
            # Update the panel if available
            if hasattr(self, 'april_tag_panel'):
                self.april_tag_panel.update_tags_display(tags)
        
        # Schedule the next update
        self.root.after(self.APRILTAG_REFRESH_RATE, self.update_april_tag_display)
        
    def toggle_connection(self):
        """Toggle connection status"""
        if not self.stream_active:
            # Start connection
            if self.connect_mqtt():
                self.stream_active = True
                self.connection_panel.connect_button.config(text="Disconnect")
                self.controls_panel.update_control_buttons(True)
            else:
                # Connection failed
                self.log_to_console("Failed to establish connection")
                return
        else:
            # Stop connection
            self.disconnect_mqtt()
            
            # Stop camera if running
            if self.capture and self.capture.isOpened():
                self.camera_panel.stop_camera()
                
            self.stream_active = False
            self.connection_panel.connect_button.config(text="Connect")
            self.controls_panel.update_control_buttons(False)
        
        # Update camera buttons based on connection state
        self.update_camera_buttons()
    
    def update_camera_buttons(self):
        """Update camera button states based on connection status"""
        if self.stream_active:
            # Connection active, enable start camera button
            self.camera_panel.start_camera_btn.config(state=tk.NORMAL)
            self.camera_panel.stop_camera_btn.config(state=tk.DISABLED)
        else:
            # Connection inactive, disable both camera buttons
            self.camera_panel.start_camera_btn.config(state=tk.DISABLED)
            self.camera_panel.stop_camera_btn.config(state=tk.DISABLED)
    
    def key_press_handler(self, button_name):
        """Handle keyboard press events by simulating button presses"""
        if self.mqtt_connected:
            # Flash the corresponding button to give visual feedback
            button = self.controls_panel.control_buttons[button_name]
            original_bg = button.cget("background")
            button.config(background="yellow")
            self.root.after(100, lambda: button.config(background=original_bg))
            
            # Send the command associated with the key
            command = self.controls_panel.control_commands[button_name]
            self.send_command(command)
    
    def on_mqtt_message(self, client, userdata, msg):
        """Callback function for received MQTT messages"""
        message = msg.payload.decode()
        
        try:
            # Try to parse as JSON (for sensor data)
            data = json.loads(message)
            if "type" in data and data["type"] == "sensor_data":
                # Extract sensor values
                self.accel_data = data.get("accelerometer", [0, 0, 0])
                self.gyro_data = data.get("gyroscope", [0, 0, 0])
                self.temp_data = data.get("temperature", 0)
                
                # Update displays in both panels with proper refresh rate
                self.root.after(0, lambda: self.update_sensor_displays())
                
                # No need to log these high-frequency messages to console
                return
            elif "type" in data and data["type"] == "humiture_data":
                self.humiture_data = data.get("data", {"temperature_c": 0, "humidity": 0})
                self.root.after(0, lambda: self.update_humiture_display())
                return # Don't log to console
            elif "type" in data and data["type"] == "spectral_data":
                self.spectral_data = data.get("data", {})
                self.root.after(0, lambda: self.update_spectral_display())
                return # Don't log to console
        except json.JSONDecodeError:
            # Regular text message, log to console
            pass
            
        self.log_to_console(f"Pi: {message}")
    
    def update_sensor_displays(self):
        """Update all sensor displays with new values"""
        # Update the compact panel
        self.sensor_panel.update_sensor_displays(
            self.accel_data, self.gyro_data, self.temp_data)
        
        # Update the detailed sensor tab
        self.sensor_tab_panel.update_display(
            self.accel_data, self.gyro_data, self.temp_data)

    def update_humiture_display(self):
        """Update humiture sensor displays with new values"""
        self.sensor_panel.update_humiture_display(
            self.humiture_data.get("temperature_c", 0),
            self.humiture_data.get("humidity", 0)
        )

    def update_spectral_display(self):
        """Update spectral sensor displays with new values"""
        self.sensor_tab_panel.update_spectral_display(self.spectral_data)
    
    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for when the client connects to the MQTT broker"""
        if rc == 0:
            self.mqtt_connected = True
            self.log_to_console("Connected to MQTT broker")
            client.subscribe(self.TOPIC_RECEIVE)
        else:
            self.mqtt_connected = False
            self.log_to_console(f"Failed to connect to MQTT broker with code {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the MQTT broker"""
        self.mqtt_connected = False
        self.log_to_console("Disconnected from MQTT broker")
    
    def connect_mqtt(self):
        """Connect to the MQTT broker"""
        ip_address = self.connection_panel.ip_entry.get()
        if not ip_address:
            return False
        
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            
            self.log_to_console(f"Connecting to MQTT broker at {ip_address}:{self.MQTT_PORT}")
            self.mqtt_client.connect(ip_address, self.MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            self.log_to_console(f"MQTT connection error: {e}")
            return False
    
    def disconnect_mqtt(self):
        """Disconnect from the MQTT broker"""
        if self.mqtt_client and self.mqtt_connected:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None
    
    def log_to_console(self, message):
        """Add a message to the console with timestamp"""
        if hasattr(self, 'console_panel') and self.console_panel:
            self.console_panel.log_message(message)
        else:
            print(message)  # Fallback in case console_panel is not ready
    
    def send_command(self, command):
        """Send a command via MQTT to the Raspberry Pi"""
        if self.mqtt_client and self.mqtt_connected:
            self.mqtt_client.publish(self.TOPIC_SEND, command)
            self.log_to_console(f"Sent: {command}")
        else:
            self.log_to_console("Cannot send command: Not connected to MQTT broker")
    
    def get_apriltag_data(self):
        """Get the current AprilTag detection data"""
        if hasattr(self, 'camera_panel') and self.camera_panel:
            return self.camera_panel.current_tags
        return []
    
    def send_apriltag_data(self):
        """Send the current AprilTag data to the Pi via MQTT"""
        if not self.mqtt_connected:
            return
            
        tags = self.get_apriltag_data()
        if not tags:
            return
            
        # Format tag data for sending
        tag_data = []
        for tag in tags:
            tag_info = {
                "id": tag.tag_id,
                "center": tag.center.tolist(),
                "corners": tag.corners.tolist(),
            }
            
            # Add pose information if available
            if hasattr(tag, 'pose_t') and hasattr(tag, 'pose_R'):
                tag_info["distance"] = float(np.linalg.norm(tag.pose_t))
                tag_info["translation"] = tag.pose_t.tolist()
                tag_info["rotation"] = tag.pose_R.tolist()
                
            tag_data.append(tag_info)
            
        # Create a message with all tag data
        message = {
            "type": "apriltag_data",
            "tags": tag_data
        }
        
        # Send as JSON
        self.mqtt_client.publish(self.TOPIC_SEND, json.dumps(message))
        self.log_to_console(f"Sent AprilTag data: {len(tag_data)} tags")

if __name__ == "__main__":
    root = tk.Tk()
    app = RoverControlApp(root)
    root.mainloop()