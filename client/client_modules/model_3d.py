"""
This module provides 3D visualization for the rover using matplotlib.
It displays the rover's orientation based on sensor data from the MPU6050.
Highly laggy, since python threading isn't ACTUALLY multithreaded, so this module is disabled for now.
"""
import numpy as np
import time
import math
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import tkinter as tk

class RoverVisualizer:
    """A class that creates and updates a 3D visualization of the rover using matplotlib."""
    
    def __init__(self, tk_frame, size=(300, 250)):
        """
        Initialize the 3D visualization in a Tkinter frame.
        
        Parameters:
            tk_frame (tkinter.Frame): The Tkinter frame to embed the visualization in
            size (tuple): The width and height of the visualization
        """
        self.tk_frame = tk_frame
        self.frame_width, self.frame_height = size
        
        # Store sensor data
        self.sensor_data = {
            'accel': [0, 0, 0],
            'gyro': [0, 0, 0],
            'orientation': [0, 0, 0]  # Roll, pitch, yaw in radians
        }
        
        # Complementary filter coefficient
        self.alpha = 0.98
        self.prev_time = time.time()
        
        # Create matplotlib figure and 3D axes for the visualization
        self.fig = Figure(figsize=(self.frame_width/100, self.frame_height/100), dpi=100)
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Create a canvas to display the figure
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tk_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configure the 3D plot
        self.ax.set_xlim(-3, 3)
        self.ax.set_ylim(-3, 3)
        self.ax.set_zlim(-3, 3)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_title('Rover Orientation')
        
        # Equal aspect ratio
        self.ax.set_box_aspect([1, 1, 1])
        
        # Initialize the vector arrows for acceleration and gyro
        self.accel_arrow = None
        self.gyro_arrows = [None, None, None]
        
        # Store the rover parts for rotation
        self.rover_parts = []
        
        # Data smoothing buffers
        self.accel_buffer = [[0, 0, 0] for _ in range(5)]
        self.gyro_buffer = [[0, 0, 0] for _ in range(5)]
        
        # Initialize 3D rover model
        self.create_rover_model()
        
        # Create coordinate axes
        self.create_axes()
        
        # Make initial quiver plots for vectors
        self.accel_arrow = self.ax.quiver(0, 0, 0, 0, 0, 0, color='red', label='Accel')
        self.gyro_arrows[0] = self.ax.quiver(0, 0, 0, 0, 0, 0, color='blue', label='Gyro X')
        self.gyro_arrows[1] = self.ax.quiver(0, 0, 0, 0, 0, 0, color='green', label='Gyro Y')
        self.gyro_arrows[2] = self.ax.quiver(0, 0, 0, 0, 0, 0, color='purple', label='Gyro Z')
        
        # Add legend
        self.ax.legend(loc='upper right')
        
        # Draw the initial view
        self.canvas.draw()
    
    def create_axes(self):
        """Create coordinate axes for reference."""
        origin = [0, 0, 0]
        axis_length = 2
        
        # X-axis (red)
        self.ax.quiver(origin[0], origin[1], origin[2], 
                      axis_length, 0, 0, color='red', alpha=0.5, arrow_length_ratio=0.1)
        
        # Y-axis (green)
        self.ax.quiver(origin[0], origin[1], origin[2], 
                      0, axis_length, 0, color='green', alpha=0.5, arrow_length_ratio=0.1)
        
        # Z-axis (blue)
        self.ax.quiver(origin[0], origin[1], origin[2], 
                      0, 0, axis_length, color='blue', alpha=0.5, arrow_length_ratio=0.1)
    
    def create_rover_model(self):
        """Create a simplified 3D model of the rover."""
        # Create the rover body (ellipsoid)
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 10)
        
        # Ellipsoid parameters
        a = 2.0  # Length (x-axis)
        b = 0.8  # Width (y-axis)
        c = 0.8  # Height (z-axis)
        
        # Generate ellipsoid points
        x = a * np.outer(np.cos(u), np.sin(v))
        y = b * np.outer(np.sin(u), np.sin(v))
        z = c * np.outer(np.ones_like(u), np.cos(v))
        
        # Plot rover body
        self.rover_body = self.ax.plot_surface(x, y, z, color='cyan', alpha=0.7)
        self.rover_parts.append(self.rover_body)
        
        # Create gondola (cuboid) under the rover
        gondola_length, gondola_width, gondola_height = 0.8, 0.3, 0.2
        x_g = np.array([
            -gondola_length/2, gondola_length/2, gondola_length/2, -gondola_length/2,
            -gondola_length/2, gondola_length/2, gondola_length/2, -gondola_length/2
        ])
        y_g = np.array([
            -gondola_width/2, -gondola_width/2, gondola_width/2, gondola_width/2,
            -gondola_width/2, -gondola_width/2, gondola_width/2, gondola_width/2
        ])
        z_g = np.array([
            -0.9, -0.9, -0.9, -0.9,
            -0.9-gondola_height, -0.9-gondola_height, -0.9-gondola_height, -0.9-gondola_height
        ])
        
        # Define the vertices of the gondola
        vertices = [list(zip(x_g, y_g, z_g))]
        
        # Define the faces of the cuboid
        faces = [
            [vertices[0][0], vertices[0][1], vertices[0][2], vertices[0][3]],
            [vertices[0][4], vertices[0][5], vertices[0][6], vertices[0][7]],
            [vertices[0][0], vertices[0][3], vertices[0][7], vertices[0][4]],
            [vertices[0][1], vertices[0][2], vertices[0][6], vertices[0][5]],
            [vertices[0][0], vertices[0][1], vertices[0][5], vertices[0][4]],
            [vertices[0][3], vertices[0][2], vertices[0][6], vertices[0][7]]
        ]
        
        # Create the polygon collection
        self.gondola = Poly3DCollection(faces, alpha=1.0, color='gray')
        self.ax.add_collection3d(self.gondola)
        self.rover_parts.append(self.gondola)
        
        # Create fins for visual interest
        # Right fin
        x_fin_r = np.array([1.5, 0.5, 1.0])
        y_fin_r = np.array([0, 0, 0])
        z_fin_r = np.array([0.5, 0.5, 1.0])
        
        fin_r_vertices = [list(zip(x_fin_r, y_fin_r, z_fin_r))]
        fin_r_faces = [[fin_r_vertices[0][0], fin_r_vertices[0][1], fin_r_vertices[0][2]]]
        
        self.fin_right = Poly3DCollection(fin_r_faces, alpha=0.7, color='cyan')
        self.ax.add_collection3d(self.fin_right)
        self.rover_parts.append(self.fin_right)
        
        # Left fin
        x_fin_l = np.array([1.5, 0.5, 1.0])
        y_fin_l = np.array([0, 0, 0])
        z_fin_l = np.array([-0.5, -0.5, -1.0])
        
        fin_l_vertices = [list(zip(x_fin_l, y_fin_l, z_fin_l))]
        fin_l_faces = [[fin_l_vertices[0][0], fin_l_vertices[0][1], fin_l_vertices[0][2]]]
        
        self.fin_left = Poly3DCollection(fin_l_faces, alpha=0.7, color='cyan')
        self.ax.add_collection3d(self.fin_left)
        self.rover_parts.append(self.fin_left)
    
    def update_data(self, accel, gyro):
        """
        Update sensor data and calculate orientation.
        
        Parameters:
            accel (list): Accelerometer data [x, y, z]
            gyro (list): Gyroscope data [x, y, z]
        """
        # Apply smoothing using a simple moving average
        self.accel_buffer.append(accel)
        self.gyro_buffer.append(gyro)
        
        if len(self.accel_buffer) > 5:
            self.accel_buffer.pop(0)
        if len(self.gyro_buffer) > 5:
            self.gyro_buffer.pop(0)
            
        # Calculate smoothed values
        smoothed_accel = [sum(values) / len(values) for values in zip(*self.accel_buffer)]
        smoothed_gyro = [sum(values) / len(values) for values in zip(*self.gyro_buffer)]
        
        # Store raw sensor data
        self.sensor_data['accel'] = smoothed_accel
        self.sensor_data['gyro'] = smoothed_gyro
        
        # Calculate orientation using complementary filter
        current_time = time.time()
        dt = current_time - self.prev_time
        self.prev_time = current_time
        
        # Convert gyro data from deg/s to rad/s
        gyro_rad = [g * np.pi / 180 for g in smoothed_gyro]
        
        # Calculate angles from accelerometer (roll and pitch)
        accel_norm = np.linalg.norm(smoothed_accel)
        if accel_norm > 0:  # Avoid division by zero
            accel_normalized = [a / accel_norm for a in smoothed_accel]
            
            roll_acc = np.arctan2(accel_normalized[1], accel_normalized[2])
            pitch_acc = np.arctan2(-accel_normalized[0], np.sqrt(accel_normalized[1]**2 + accel_normalized[2]**2))
            
            # We can't determine yaw from accelerometer
            yaw_acc = self.sensor_data['orientation'][2]
        else:
            roll_acc, pitch_acc, yaw_acc = self.sensor_data['orientation']
        
        # Integrate gyro data
        roll = self.alpha * (self.sensor_data['orientation'][0] + gyro_rad[0] * dt) + (1 - self.alpha) * roll_acc
        pitch = self.alpha * (self.sensor_data['orientation'][1] + gyro_rad[1] * dt) + (1 - self.alpha) * pitch_acc
        yaw = self.sensor_data['orientation'][2] + gyro_rad[2] * dt
        
        # Update orientation
        self.sensor_data['orientation'] = [roll, pitch, yaw]
        
        # Update visualization
        self.update_visualization()
    
    def update_visualization(self):
        """Update the 3D visualization based on the latest sensor data."""
        # Clear previous vectors
        if self.accel_arrow:
            self.accel_arrow.remove()
        for arrow in self.gyro_arrows:
            if arrow:
                arrow.remove()
        
        # Get orientation and sensor data
        roll, pitch, yaw = self.sensor_data['orientation']
        accel = self.sensor_data['accel']
        gyro = self.sensor_data['gyro']
        
        # Clear the axis to redraw the rover with new orientation
        self.ax.cla()
        
        # Reset axes properties
        self.ax.set_xlim(-3, 3)
        self.ax.set_ylim(-3, 3)
        self.ax.set_zlim(-3, 3)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_title('Rover Orientation')
        
        # Equal aspect ratio
        self.ax.set_box_aspect([1, 1, 1])
        
        # Recreate the axes
        self.create_axes()
        
        # Recreate the rover model with updated orientation
        self.create_rotated_rover_model(roll, pitch, yaw)
        
        # Create acceleration vector
        accel_scale = 0.2  # Scale factor for visualization
        self.accel_arrow = self.ax.quiver(0, 0, 0, 
                                        accel[0] * accel_scale,
                                        accel[1] * accel_scale, 
                                        accel[2] * accel_scale,
                                        color='red', label='Accel')
        
        # Create gyro vectors
        gyro_scale = 0.05  # Scale factor for visualization
        self.gyro_arrows[0] = self.ax.quiver(0, 0, 0, 
                                         gyro[0] * gyro_scale, 0, 0,
                                         color='blue', label='Gyro X')
        self.gyro_arrows[1] = self.ax.quiver(0, 0, 0, 
                                         0, gyro[1] * gyro_scale, 0,
                                         color='green', label='Gyro Y')
        self.gyro_arrows[2] = self.ax.quiver(0, 0, 0, 
                                         0, 0, gyro[2] * gyro_scale,
                                         color='purple', label='Gyro Z')
        
        # Add legend
        self.ax.legend(loc='upper right', fontsize='small')
        
        # Redraw the canvas
        self.canvas.draw()
    
    def create_rotated_rover_model(self, roll, pitch, yaw):
        """Create the rover model with the specified orientation."""
        # Calculate rotation matrix
        # First rotate around Z (yaw)
        cos_yaw = np.cos(yaw)
        sin_yaw = np.sin(yaw)
        R_z = np.array([
            [cos_yaw, -sin_yaw, 0],
            [sin_yaw, cos_yaw, 0],
            [0, 0, 1]
        ])
        
        # Then rotate around Y (pitch)
        cos_pitch = np.cos(pitch)
        sin_pitch = np.sin(pitch)
        R_y = np.array([
            [cos_pitch, 0, sin_pitch],
            [0, 1, 0],
            [-sin_pitch, 0, cos_pitch]
        ])
        
        # Then rotate around X (roll)
        cos_roll = np.cos(roll)
        sin_roll = np.sin(roll)
        R_x = np.array([
            [1, 0, 0],
            [0, cos_roll, -sin_roll],
            [0, sin_roll, cos_roll]
        ])
        
        # Combined rotation matrix (ZYX order)
        R = np.dot(R_z, np.dot(R_y, R_x))
        
        # Create the rover body (ellipsoid)
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 10)
        
        # Ellipsoid parameters
        a = 2.0  # Length (x-axis)
        b = 0.8  # Width (y-axis)
        c = 0.8  # Height (z-axis)
        
        # Generate ellipsoid points
        x = a * np.outer(np.cos(u), np.sin(v))
        y = b * np.outer(np.sin(u), np.sin(v))
        z = c * np.outer(np.ones_like(u), np.cos(v))
        
        # Apply rotation to each point
        x_rot = np.zeros_like(x)
        y_rot = np.zeros_like(y)
        z_rot = np.zeros_like(z)
        
        for i in range(x.shape[0]):
            for j in range(x.shape[1]):
                point = np.array([x[i,j], y[i,j], z[i,j]])
                rotated = np.dot(R, point)
                x_rot[i,j] = rotated[0]
                y_rot[i,j] = rotated[1]
                z_rot[i,j] = rotated[2]
        
        # Plot rover body
        self.rover_body = self.ax.plot_surface(x_rot, y_rot, z_rot, color='cyan', alpha=0.7)
        
        # Create gondola (cuboid) under the rover
        gondola_length, gondola_width, gondola_height = 0.8, 0.3, 0.2
        x_g = np.array([
            -gondola_length/2, gondola_length/2, gondola_length/2, -gondola_length/2,
            -gondola_length/2, gondola_length/2, gondola_length/2, -gondola_length/2
        ])
        y_g = np.array([
            -gondola_width/2, -gondola_width/2, gondola_width/2, gondola_width/2,
            -gondola_width/2, -gondola_width/2, gondola_width/2, gondola_width/2
        ])
        z_g = np.array([
            -0.9, -0.9, -0.9, -0.9,
            -0.9-gondola_height, -0.9-gondola_height, -0.9-gondola_height, -0.9-gondola_height
        ])
        
        # Apply rotation to each gondola point
        x_g_rot = np.zeros_like(x_g)
        y_g_rot = np.zeros_like(y_g)
        z_g_rot = np.zeros_like(z_g)
        
        for i in range(len(x_g)):
            point = np.array([x_g[i], y_g[i], z_g[i]])
            rotated = np.dot(R, point)
            x_g_rot[i] = rotated[0]
            y_g_rot[i] = rotated[1]
            z_g_rot[i] = rotated[2]
        
        # Define the vertices of the gondola
        vertices = [list(zip(x_g_rot, y_g_rot, z_g_rot))]
        
        # Define the faces of the cuboid
        faces = [
            [vertices[0][0], vertices[0][1], vertices[0][2], vertices[0][3]],
            [vertices[0][4], vertices[0][5], vertices[0][6], vertices[0][7]],
            [vertices[0][0], vertices[0][3], vertices[0][7], vertices[0][4]],
            [vertices[0][1], vertices[0][2], vertices[0][6], vertices[0][5]],
            [vertices[0][0], vertices[0][1], vertices[0][5], vertices[0][4]],
            [vertices[0][3], vertices[0][2], vertices[0][6], vertices[0][7]]
        ]
        
        # Create the polygon collection
        self.gondola = Poly3DCollection(faces, alpha=1.0, color='gray')
        self.ax.add_collection3d(self.gondola)
        
        # Create fins for visual interest
        # Right fin
        x_fin_r = np.array([1.5, 0.5, 1.0])
        y_fin_r = np.array([0, 0, 0])
        z_fin_r = np.array([0.5, 0.5, 1.0])
        
        # Apply rotation to right fin
        x_fin_r_rot = np.zeros_like(x_fin_r)
        y_fin_r_rot = np.zeros_like(y_fin_r)
        z_fin_r_rot = np.zeros_like(z_fin_r)
        
        for i in range(len(x_fin_r)):
            point = np.array([x_fin_r[i], y_fin_r[i], z_fin_r[i]])
            rotated = np.dot(R, point)
            x_fin_r_rot[i] = rotated[0]
            y_fin_r_rot[i] = rotated[1]
            z_fin_r_rot[i] = rotated[2]
        
        fin_r_vertices = [list(zip(x_fin_r_rot, y_fin_r_rot, z_fin_r_rot))]
        fin_r_faces = [[fin_r_vertices[0][0], fin_r_vertices[0][1], fin_r_vertices[0][2]]]
        
        self.fin_right = Poly3DCollection(fin_r_faces, alpha=0.7, color='cyan')
        self.ax.add_collection3d(self.fin_right)
        
        # Left fin
        x_fin_l = np.array([1.5, 0.5, 1.0])
        y_fin_l = np.array([0, 0, 0])
        z_fin_l = np.array([-0.5, -0.5, -1.0])
        
        # Apply rotation to left fin
        x_fin_l_rot = np.zeros_like(x_fin_l)
        y_fin_l_rot = np.zeros_like(y_fin_l)
        z_fin_l_rot = np.zeros_like(z_fin_l)
        
        for i in range(len(x_fin_l)):
            point = np.array([x_fin_l[i], y_fin_l[i], z_fin_l[i]])
            rotated = np.dot(R, point)
            x_fin_l_rot[i] = rotated[0]
            y_fin_l_rot[i] = rotated[1]
            z_fin_l_rot[i] = rotated[2]
        
        fin_l_vertices = [list(zip(x_fin_l_rot, y_fin_l_rot, z_fin_l_rot))]
        fin_l_faces = [[fin_l_vertices[0][0], fin_l_vertices[0][1], fin_l_vertices[0][2]]]
        
        self.fin_left = Poly3DCollection(fin_l_faces, alpha=0.7, color='cyan')
        self.ax.add_collection3d(self.fin_left)
    
    def stop(self):
        """Clean up resources when stopping the visualization."""
        # Close the matplotlib figure to free resources
        plt.close(self.fig)