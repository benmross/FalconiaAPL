import tkinter as tk
from tkinter import ttk

class SensorTabPanel:
    def __init__(self, parent, app):
        self.app = app
        
        # Make main frame fill the entire area
        sensor_frame = tk.Frame(parent, padx=5, pady=5)
        sensor_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title - more compact
        title_label = tk.Label(sensor_frame, text="MPU6050 Sensor Data", font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 5))
        
        # Using PanedWindow for resizable dividers
        paned_window = tk.PanedWindow(sensor_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Accelerometer section in first pane
        accel_frame = tk.LabelFrame(paned_window, text="Accelerometer (m/s²)", padx=5, pady=5)
        paned_window.add(accel_frame, width=275)
        
        # Progress bars for accelerometer - more compact
        self.accel_bars = []
        self.accel_val_labels = []
        for i, axis in enumerate(['X', 'Y', 'Z']):
            # Axis label
            tk.Label(accel_frame, text=f"{axis}-axis:", font=("Arial", 10)).grid(row=i, column=0, sticky="w", pady=2)
            
            # Value label
            val_label = tk.Label(accel_frame, text="0.00", font=("Arial", 10), width=6)
            val_label.grid(row=i, column=1, padx=5)
            self.accel_val_labels.append(val_label)
            
            # Progress bar
            bar = ttk.Progressbar(accel_frame, length=150, mode="determinate")
            bar["maximum"] = 20  # Range of -10 to +10 m/s²
            bar["value"] = 10     # Center at 0
            bar.grid(row=i, column=2, padx=2, pady=2)
            self.accel_bars.append(bar)
        
        # Gyroscope section in second pane
        gyro_frame = tk.LabelFrame(paned_window, text="Gyroscope (rad/s)", padx=5, pady=5)
        paned_window.add(gyro_frame, width=275)
        
        # Progress bars for gyroscope - more compact
        self.gyro_bars = []
        self.gyro_val_labels = []
        for i, axis in enumerate(['X', 'Y', 'Z']):
            # Axis label
            tk.Label(gyro_frame, text=f"{axis}-axis:", font=("Arial", 10)).grid(row=i, column=0, sticky="w", pady=2)
            
            # Value label
            val_label = tk.Label(gyro_frame, text="0.00", font=("Arial", 10), width=6)
            val_label.grid(row=i, column=1, padx=5)
            self.gyro_val_labels.append(val_label)
            
            # Progress bar
            bar = ttk.Progressbar(gyro_frame, length=150, mode="determinate")
            bar["maximum"] = 20  # Range of -10 to +10 rad/s
            bar["value"] = 10     # Center at 0
            bar.grid(row=i, column=2, padx=2, pady=2)
            self.gyro_bars.append(bar)
        
        # Temperature section in third pane
        temp_frame = tk.LabelFrame(paned_window, text="Temperature (°C)", padx=5, pady=5)
        paned_window.add(temp_frame, width=275)
        
        tk.Label(temp_frame, text="Temperature:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=2)
        self.temp_val_label = tk.Label(temp_frame, text="0.00", font=("Arial", 10), width=6)
        self.temp_val_label.grid(row=0, column=1, padx=5)
        
        self.temp_bar = ttk.Progressbar(temp_frame, length=150, mode="determinate")
        self.temp_bar["maximum"] = 60  # Temperature range from 0 to 60°C
        self.temp_bar["value"] = 25     # Default room temperature
        self.temp_bar.grid(row=0, column=2, padx=2, pady=2)

        # Spectral sensor section
        spectral_frame = tk.LabelFrame(sensor_frame, text="Spectral Sensor Data", padx=5, pady=5)
        spectral_frame.pack(fill=tk.BOTH, expand=True, pady=(10,0))

        self.spectral_bars = {}
        self.spectral_val_labels = {}
        colors = ["violet", "blue", "green", "yellow", "orange", "red"]
        
        # Create custom styles for progress bars
        style = ttk.Style()

        for i, color in enumerate(colors):
            tk.Label(spectral_frame, text=f"{color.capitalize()}:", font=("Arial", 10)).grid(row=i, column=0, sticky="w", pady=2, padx=20)
            val_label = tk.Label(spectral_frame, text="0.000", font=("Arial", 10), width=12)
            val_label.grid(row=i, column=1, padx=5)
            self.spectral_val_labels[color] = val_label

            # Create a custom style for each color
            style.configure(f"{color}.Horizontal.TProgressbar", background=color)

            bar = ttk.Progressbar(spectral_frame, length=300, mode="determinate", style=f"{color}.Horizontal.TProgressbar")
            bar["maximum"] = 60000  # Max value from sensor
            bar["value"] = 0
            bar.grid(row=i, column=2, padx=2, pady=2)
            self.spectral_bars[color] = bar

    def update_display(self, accel, gyro, temp):
        """Update the detailed sensor tab display with new values"""
        # Update the accelerometer display
        for i, value in enumerate(accel):
            self.accel_val_labels[i].config(text=f"{value:.2f}")
            # Map value to progress bar (center at 10, range -10 to +10)
            bar_value = min(max(value + 10, 0), 20)
            self.accel_bars[i]["value"] = bar_value
        
        # Update the gyroscope display
        for i, value in enumerate(gyro):
            self.gyro_val_labels[i].config(text=f"{value:.2f}")
            # Map value to progress bar (center at 10, range -10 to +10)
            bar_value = min(max(value + 10, 0), 20)
            self.gyro_bars[i]["value"] = bar_value
        
        # Update the temperature display
        self.temp_val_label.config(text=f"{temp:.2f}")
        # Map temperature to range (0 to 60°C)
        bar_value = min(max(temp, 0), 60)
        self.temp_bar["value"] = bar_value

    def update_spectral_display(self, spectral_data):
        """Update the spectral sensor display with new values"""
        for color, value in spectral_data.items():
            if color in self.spectral_val_labels:
                self.spectral_val_labels[color].config(text=f"{value:.3f}")
                self.spectral_bars[color]["value"] = value