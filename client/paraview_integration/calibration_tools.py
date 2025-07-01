#!/usr/bin/env python3
"""
Calibration Tools for Rover Tracking System

This module provides interactive calibration tools for camera intrinsics
and coordinate mapping between camera and world coordinates.
"""

import cv2
import numpy as np
import json
import os
import sys
import argparse
from typing import List, Tuple, Optional
import glob

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.apriltag_detector import AprilTagDetector
from paraview_integration.coordinate_transform import CoordinateTransform

class CameraCalibrator:
    """Interactive camera calibration tool"""
    
    def __init__(self):
        self.camera_matrix = None
        self.dist_coeffs = None
        self.rvecs = None
        self.tvecs = None
        self.calibration_error = None
        
    def calibrate_camera_from_checkerboard(self, 
                                         image_paths: List[str],
                                         checkerboard_size: Tuple[int, int] = (7, 5),
                                         square_size: float = 0.025) -> bool:
        """
        Calibrate camera using checkerboard images
        
        Args:
            image_paths: List of paths to calibration images
            checkerboard_size: Number of internal corners (width, height)
            square_size: Size of checkerboard squares in meters
        """
        # Prepare object points
        objp = np.zeros((checkerboard_size[0] * checkerboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:checkerboard_size[0], 0:checkerboard_size[1]].T.reshape(-1, 2)
        objp *= square_size
        
        # Arrays to store object points and image points
        objpoints = []  # 3d points in real world space
        imgpoints = []  # 2d points in image plane
        
        print(f"Processing {len(image_paths)} calibration images...")
        
        for i, img_path in enumerate(image_paths):
            img = cv2.imread(img_path)
            if img is None:
                print(f"Warning: Could not load image {img_path}")
                continue
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Find checkerboard corners
            ret, corners = cv2.findChessboardCorners(gray, checkerboard_size, None)
            
            if ret:
                objpoints.append(objp)
                
                # Refine corner positions
                corners2 = cv2.cornerSubPix(
                    gray, corners, (11, 11), (-1, -1),
                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                )
                imgpoints.append(corners2)
                
                print(f"  ✓ Image {i+1}/{len(image_paths)}: Found corners")
            else:
                print(f"  ✗ Image {i+1}/{len(image_paths)}: No corners found")
        
        if len(objpoints) < 5:
            print("Error: Need at least 5 valid calibration images")
            return False
            
        print(f"Calibrating camera with {len(objpoints)} valid images...")
        
        # Calibrate camera
        ret, self.camera_matrix, self.dist_coeffs, self.rvecs, self.tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, gray.shape[::-1], None, None
        )
        
        if ret:
            # Calculate reprojection error
            mean_error = 0
            for i in range(len(objpoints)):
                imgpoints2, _ = cv2.projectPoints(
                    objpoints[i], self.rvecs[i], self.tvecs[i], 
                    self.camera_matrix, self.dist_coeffs
                )
                error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
                mean_error += error
                
            self.calibration_error = mean_error / len(objpoints)
            print(f"Camera calibration successful!")
            print(f"  Reprojection error: {self.calibration_error:.4f} pixels")
            print(f"  Camera matrix:\n{self.camera_matrix}")
            print(f"  Distortion coefficients: {self.dist_coeffs.flatten()}")
            
            return True
        else:
            print("Camera calibration failed")
            return False
            
    def save_calibration(self, filepath: str):
        """Save camera calibration to file"""
        if self.camera_matrix is None:
            print("Error: No calibration data to save")
            return
            
        calibration_data = {
            "camera_matrix": self.camera_matrix.tolist(),
            "dist_coeffs": self.dist_coeffs.tolist(),
            "calibration_error": self.calibration_error,
            "image_size": [int(self.camera_matrix[0, 2] * 2), int(self.camera_matrix[1, 2] * 2)]
        }
        
        with open(filepath, 'w') as f:
            json.dump(calibration_data, f, indent=2)
            
        print(f"Camera calibration saved to {filepath}")
        
    def load_calibration(self, filepath: str) -> bool:
        """Load camera calibration from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            self.camera_matrix = np.array(data["camera_matrix"], dtype=np.float32)
            self.dist_coeffs = np.array(data["dist_coeffs"], dtype=np.float32)
            self.calibration_error = data.get("calibration_error", 0.0)
            
            print(f"Camera calibration loaded from {filepath}")
            print(f"  Reprojection error: {self.calibration_error:.4f} pixels")
            
            return True
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading calibration file: {e}")
            return False

class CoordinateCalibrator:
    """Interactive coordinate mapping calibration tool"""
    
    def __init__(self):
        self.transform = CoordinateTransform()
        self.detector = AprilTagDetector()
        self.reference_points = []
        self.current_image = None
        self.selected_pixel = None
        self.window_name = "Coordinate Calibration"
        
    def mouse_callback(self, event, x, y, flags, param):
        """Mouse callback for selecting points"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.selected_pixel = (x, y)
            # Draw crosshair at selected point
            if self.current_image is not None:
                img_copy = self.current_image.copy()
                cv2.drawMarker(img_copy, (x, y), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
                cv2.imshow(self.window_name, img_copy)
                print(f"Selected pixel: ({x}, {y})")
                
    def calibrate_from_stream(self, stream_url: str, known_points: List[Tuple[float, float]] = None):
        """
        Interactive calibration from live stream
        
        Args:
            stream_url: URL of MJPEG stream or camera index
            known_points: List of known world coordinates for reference
        """
        if known_points is None:
            known_points = [
                (0.0, 0.0),    # Bottom-left corner
                (1.0, 0.0),    # Bottom-right corner
                (1.0, 1.0),    # Top-right corner
                (0.0, 1.0),    # Top-left corner
            ]
            
        try:
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                print(f"Error: Could not open stream {stream_url}")
                return False
                
            cv2.namedWindow(self.window_name)
            cv2.setMouseCallback(self.window_name, self.mouse_callback)
            
            print("Coordinate Calibration Tool")
            print("=" * 50)
            print("Instructions:")
            print("1. Click on reference points in the image")
            print("2. Enter world coordinates when prompted")
            print("3. Press 'c' to calibrate after adding points")
            print("4. Press 's' to save calibration")
            print("5. Press 'q' to quit")
            print("6. Press 'r' to reset points")
            print()
            
            point_index = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to capture frame")
                    break
                    
                self.current_image = frame.copy()
                
                # Draw existing reference points
                for i, (pixel, world) in enumerate(self.reference_points):
                    cv2.drawMarker(frame, (int(pixel[0]), int(pixel[1])), 
                                 (255, 0, 0), cv2.MARKER_CROSS, 20, 2)
                    cv2.putText(frame, f"P{i+1}", 
                              (int(pixel[0]) + 10, int(pixel[1]) - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
                # Show current instruction
                if point_index < len(known_points):
                    world_pt = known_points[point_index]
                    instruction = f"Click on point at world coordinates ({world_pt[0]}, {world_pt[1]})"
                    cv2.putText(frame, instruction, (10, 30),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                cv2.imshow(self.window_name, frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.reference_points = []
                    point_index = 0
                    print("Reference points reset")
                elif key == ord('c'):
                    if self.calibrate_transform():
                        print("Calibration successful!")
                    else:
                        print("Calibration failed!")
                elif key == ord('s'):
                    self.save_calibration()
                elif key == ord(' ') and self.selected_pixel:
                    # Add current selected point
                    if point_index < len(known_points):
                        world_coords = known_points[point_index]
                        self.reference_points.append((self.selected_pixel, world_coords))
                        print(f"Added point {point_index + 1}: pixel {self.selected_pixel} -> world {world_coords}")
                        point_index += 1
                        self.selected_pixel = None
                        
                        if point_index >= len(known_points):
                            print("All reference points added. Press 'c' to calibrate.")
                    else:
                        print("All reference points already added")
                        
            cap.release()
            cv2.destroyAllWindows()
            
            return len(self.reference_points) >= 4
            
        except Exception as e:
            print(f"Error during calibration: {e}")
            return False
            
    def calibrate_from_apriltags(self, stream_url: str, tag_positions: dict):
        """
        Calibrate using AprilTags at known positions
        
        Args:
            stream_url: URL of MJPEG stream or camera index
            tag_positions: Dict mapping tag IDs to world coordinates
        """
        try:
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                print(f"Error: Could not open stream {stream_url}")
                return False
                
            print("AprilTag Calibration Tool")
            print("=" * 50)
            print("Place AprilTags at the following positions:")
            for tag_id, pos in tag_positions.items():
                print(f"  Tag {tag_id}: ({pos[0]}, {pos[1]})")
            print()
            print("Press 'c' to capture current detections")
            print("Press 'q' to quit")
            print("Press 'r' to reset captured points")
            
            cv2.namedWindow(self.window_name)
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Detect AprilTags
                tags = self.detector.detect(frame)
                
                # Draw detections
                frame_with_tags = self.detector.draw_tags(frame, tags)
                
                # Show detected tags
                detected_tags = [tag.tag_id for tag in tags]
                info_text = f"Detected tags: {detected_tags}"
                cv2.putText(frame_with_tags, info_text, (10, 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Show reference points
                for i, (pixel, world) in enumerate(self.reference_points):
                    cv2.drawMarker(frame_with_tags, (int(pixel[0]), int(pixel[1])), 
                                 (255, 0, 0), cv2.MARKER_SQUARE, 10, 2)
                
                cv2.imshow(self.window_name, frame_with_tags)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.reference_points = []
                    print("Reference points reset")
                elif key == ord('c'):
                    # Capture current tag positions
                    for tag in tags:
                        if tag.tag_id in tag_positions:
                            pixel_coords = (tag.center[0], tag.center[1])
                            world_coords = tag_positions[tag.tag_id]
                            self.reference_points.append((pixel_coords, world_coords))
                            print(f"Captured tag {tag.tag_id}: {pixel_coords} -> {world_coords}")
                    
                    if len(self.reference_points) >= 4:
                        if self.calibrate_transform():
                            print("Calibration successful!")
                            break
                        else:
                            print("Calibration failed!")
                            
            cap.release()
            cv2.destroyAllWindows()
            
            return self.transform.calibrated
            
        except Exception as e:
            print(f"Error during AprilTag calibration: {e}")
            return False
            
    def calibrate_transform(self) -> bool:
        """Calibrate the coordinate transformation"""
        if len(self.reference_points) < 4:
            print("Error: Need at least 4 reference points")
            return False
            
        # Clear existing points and add new ones
        self.transform.clear_reference_points()
        for pixel_coords, world_coords in self.reference_points:
            self.transform.add_reference_point(pixel_coords, world_coords)
            
        # Calibrate
        success = self.transform.calibrate_homography()
        
        if success:
            error = self.transform.calculate_transformation_error()
            print(f"Transformation RMS error: {error:.4f} meters")
            
        return success
        
    def save_calibration(self, filepath: str = "config/coordinate_mapping.json"):
        """Save coordinate transformation calibration"""
        if not self.transform.calibrated:
            print("Error: No calibration data to save")
            return
            
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.transform.save_calibration(filepath)
        
    def load_calibration(self, filepath: str = "config/coordinate_mapping.json") -> bool:
        """Load coordinate transformation calibration"""
        return self.transform.load_calibration(filepath)

def main():
    parser = argparse.ArgumentParser(description="Calibration tools for rover tracking")
    parser.add_argument("--mode", choices=["camera", "coordinate", "apriltag"], 
                       required=True, help="Calibration mode")
    parser.add_argument("--stream", default="http://192.168.1.100:7123/stream.mjpg",
                       help="MJPEG stream URL or camera index")
    parser.add_argument("--images", help="Path to calibration images (for camera mode)")
    parser.add_argument("--output", help="Output calibration file path")
    
    args = parser.parse_args()
    
    if args.mode == "camera":
        calibrator = CameraCalibrator()
        
        if args.images:
            # Use provided images
            image_paths = glob.glob(os.path.join(args.images, "*.jpg"))
            image_paths.extend(glob.glob(os.path.join(args.images, "*.png")))
            
            if not image_paths:
                print(f"No images found in {args.images}")
                return 1
                
            if calibrator.calibrate_camera_from_checkerboard(image_paths):
                output_path = args.output or "config/camera_calibration.json"
                calibrator.save_calibration(output_path)
            else:
                return 1
        else:
            print("Error: --images required for camera calibration")
            return 1
            
    elif args.mode == "coordinate":
        calibrator = CoordinateCalibrator()
        
        if calibrator.calibrate_from_stream(args.stream):
            output_path = args.output or "config/coordinate_mapping.json"
            calibrator.save_calibration(output_path)
        else:
            return 1
            
    elif args.mode == "apriltag":
        calibrator = CoordinateCalibrator()
        
        # Define tag positions (customize for your setup)
        tag_positions = {
            0: (0.0, 0.0),    # Bottom-left
            1: (1.0, 0.0),    # Bottom-right
            2: (1.0, 1.0),    # Top-right
            3: (0.0, 1.0),    # Top-left
        }
        
        if calibrator.calibrate_from_apriltags(args.stream, tag_positions):
            output_path = args.output or "config/coordinate_mapping.json"
            calibrator.save_calibration(output_path)
        else:
            return 1
            
    return 0

if __name__ == "__main__":
    exit(main())