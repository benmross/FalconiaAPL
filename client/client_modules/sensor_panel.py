import tkinter as tk
from tkinter import ttk

class SensorPanel:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.LabelFrame(parent, text="Sensor Data", padx=5, pady=5)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a grid layout for sensor data
        sensor_grid = tk.Frame(self.frame)
        sensor_grid.pack(fill=tk.BOTH, expand=True)
        
        # Accelerometer labels
        tk.Label(sensor_grid, text="Accelerometer:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.accel_labels = []
        for i, axis in enumerate(['X', 'Y', 'Z']):
            tk.Label(sensor_grid, text=f"{axis}:").grid(row=i+1, column=0, sticky="e", padx=5, pady=2)
            label = tk.Label(sensor_grid, text="0.00 m/s²", width=10)
            label.grid(row=i+1, column=1, sticky="w", padx=5, pady=2)
            self.accel_labels.append(label)
        
        # Gyroscope labels
        tk.Label(sensor_grid, text="Gyroscope:", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.gyro_labels = []
        for i, axis in enumerate(['X', 'Y', 'Z']):
            tk.Label(sensor_grid, text=f"{axis}:").grid(row=i+1, column=2, sticky="e", padx=5, pady=2)
            label = tk.Label(sensor_grid, text="0.00 rad/s", width=10)
            label.grid(row=i+1, column=3, sticky="w", padx=5, pady=2)
            self.gyro_labels.append(label)
            
        # Temperature label
        tk.Label(sensor_grid, text="MPU Temp:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.temp_label = tk.Label(sensor_grid, text="0.00 °C", width=10)
        self.temp_label.grid(row=4, column=1, sticky="w", padx=5, pady=2)

        # Humidity label
        tk.Label(sensor_grid, text="Humidity:", font=("Arial", 10, "bold")).grid(row=4, column=2, sticky="w", padx=5, pady=2)
        self.humidity_label = tk.Label(sensor_grid, text="0.00 %", width=10)
        self.humidity_label.grid(row=4, column=3, sticky="w", padx=5, pady=2)

        # DHT11 Temperature label
        tk.Label(sensor_grid, text="DHT11 Temp:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="w", padx=5, pady=2)
        self.dht11_temp_label = tk.Label(sensor_grid, text="0.00 °C", width=10)
        self.dht11_temp_label.grid(row=5, column=1, sticky="w", padx=5, pady=2)
    
    def update_sensor_displays(self, accel, gyro, temp):
        """Update all sensor displays with new values"""
        # Update the compact display in the bottom right
        for i, value in enumerate(accel):
            self.accel_labels[i].config(text=f"{value:.2f} m/s²")
        
        for i, value in enumerate(gyro):
            self.gyro_labels[i].config(text=f"{value:.2f} rad/s")
        
        self.temp_label.config(text=f"{temp:.2f} °C")

    def update_humiture_display(self, temp, humidity):
        """Update humiture sensor displays with new values"""
        self.dht11_temp_label.config(text=f"{temp:.2f} °C")
        self.humidity_label.config(text=f"{humidity:.2f} %")
