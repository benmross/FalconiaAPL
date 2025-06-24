import tkinter as tk
import cv2
from PIL import Image, ImageTk
import numpy as np
import sys
import os

# Add lib directory to path so we can import our custom modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.apriltag_detector import AprilTagDetector

class CameraPanel:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Camera Control Buttons
        camera_controls = tk.Frame(self.frame)
        camera_controls.pack(fill=tk.X)
        
        self.start_camera_btn = tk.Button(camera_controls, text="Start Camera", command=self.start_camera)
        self.start_camera_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.stop_camera_btn = tk.Button(camera_controls, text="Stop Camera", command=self.stop_camera, state=tk.DISABLED)
        self.stop_camera_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # AprilTag Detection Toggle
        self.apriltag_enabled = tk.BooleanVar(value=True)
        self.apriltag_cb = tk.Checkbutton(camera_controls, text="Detect AprilTags", 
                                          variable=self.apriltag_enabled)
        self.apriltag_cb.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Tag Size Setting
        tag_size_frame = tk.Frame(camera_controls)
        tag_size_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Label(tag_size_frame, text="Tag Size (m):").pack(side=tk.LEFT)
        self.tag_size_var = tk.DoubleVar(value=0.15)
        self.tag_size_entry = tk.Entry(tag_size_frame, textvariable=self.tag_size_var, width=5)
        self.tag_size_entry.pack(side=tk.LEFT)
        
        # Camera Stream Display
        self.camera_label = tk.Label(self.frame, bg="black", text="Camera Off", fg="white")
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        # Initialize AprilTag detector
        self.tag_detector = AprilTagDetector()
        
        # Current detection results (for external access)
        self.current_tags = []
    
    def start_camera(self):
        """Start the camera stream to save bandwidth"""
        if not self.app.stream_active:
            return
            
        ip_address = self.app.connection_panel.ip_entry.get()
        if not ip_address:
            return
        
        # Start stream using configurable camera port
        stream_url = f'http://{ip_address}:{self.app.CAMERA_PORT}/stream.mjpg'
        self.start_stream(stream_url)
        
        # Update button states
        self.start_camera_btn.config(state=tk.DISABLED)
        self.stop_camera_btn.config(state=tk.NORMAL)
    
    def stop_camera(self):
        """Stop the camera stream to save bandwidth"""
        self.stop_stream()
        
        # Update button states if still connected
        if self.app.stream_active:
            self.start_camera_btn.config(state=tk.NORMAL)
            self.stop_camera_btn.config(state=tk.DISABLED)
    
    def start_stream(self, url):
        """Start the MJPEG stream"""
        try:
            self.app.capture = cv2.VideoCapture(url)
            if not self.app.capture.isOpened():
                self.camera_label.config(text="Failed to connect to stream", fg="white")
                return
            
            # Set camera parameters based on the actual frame size
            ret, test_frame = self.app.capture.read()
            #test_frame = cv2.resize(test_frame, (224, 224))
            if ret:
                height, width = test_frame.shape[:2]
                self.tag_detector.set_camera_params(
                    fx=width * 0.8,  # approximate focal length
                    fy=width * 0.8,  # approximate focal length
                    cx=width / 2,    # center x
                    cy=height / 2,   # center y
                    tag_size=self.tag_size_var.get()  # tag size in meters
                )
                self.app.log_to_console(f"Camera initialized: {width}x{height}")
                
            self.camera_label.config(text="")
            self.update_frame()
        except Exception as e:
            self.camera_label.config(text=f"Error: {str(e)}", fg="white")
    
    def stop_stream(self):
        """Stop the MJPEG stream"""
        if self.app.capture and self.app.capture.isOpened():
            self.app.capture.release()
            self.app.capture = None
        self.camera_label.config(image=None, text="Camera Off", fg="white")
    
    def detect_and_draw_apriltags(self, frame):
        """Detect AprilTags in the frame and draw info"""
        if not self.apriltag_enabled.get():
            return frame, []
        
        # Update tag size from UI input
        self.tag_detector.camera_params['tag_size'] = self.tag_size_var.get()
        
        # Detect tags
        tags = self.tag_detector.detect(frame)
        
        # Draw tags on frame
        frame = self.tag_detector.draw_tags(frame, tags)
        
        # Store the current tags for potential external use
        self.current_tags = tags
        
        # Print tag info to console (if tags detected)
        if tags and len(tags) > 0:
            tag_info = []
            for tag in tags:
                distance = np.linalg.norm(tag.pose_t) if hasattr(tag, 'pose_t') else "unknown"
                tag_info.append(f"Tag ID: {tag.tag_id}, Distance: {distance}")
            
            tag_summary = ", ".join(tag_info)
            # Only log if we have new detections (to avoid spamming)
            self.app.log_to_console(f"AprilTag(s) detected: {tag_summary}")
        
        return frame, tags
    
    def update_frame(self):
        """Update the camera frame"""
        if self.app.capture and self.app.capture.isOpened():
            ret, frame = self.app.capture.read()
            if ret:
                # Process and display the frame
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect and visualize AprilTags
                frame, _ = self.detect_and_draw_apriltags(frame)
                
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image=image)
                
                self.camera_label.config(image=photo)
                self.camera_label.image = photo  # Keep reference to prevent garbage collection
            
                # Schedule the next update using the configurable refresh rate
                self.app.root.after(self.app.CAMERA_REFRESH_RATE, self.update_frame)
            else:
                # If frame read failed, stop the stream
                self.stop_stream()
                if self.app.stream_active:
                    self.start_camera_btn.config(state=tk.NORMAL)
                    self.stop_camera_btn.config(state=tk.DISABLED)
