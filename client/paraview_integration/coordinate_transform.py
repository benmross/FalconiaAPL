#!/usr/bin/env python3
"""
Coordinate Transformation System for Rover Tracking

This module provides coordinate transformation utilities to convert
camera pixel coordinates to world coordinates in the exoplanet mockup.
"""

import numpy as np
import json
import cv2
from typing import Tuple, List, Optional, Dict, Any

class CoordinateTransform:
    """Handles coordinate transformations from camera space to world space"""
    
    def __init__(self):
        self.homography_matrix = None
        self.inverse_homography = None
        self.camera_matrix = None
        self.dist_coeffs = None
        self.reference_points = []
        self.world_points = []
        self.calibrated = False
        
    def set_camera_intrinsics(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray):
        """Set camera intrinsic parameters for distortion correction"""
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        
    def add_reference_point(self, pixel_coords: Tuple[float, float], 
                          world_coords: Tuple[float, float]):
        """Add a reference point for coordinate mapping calibration"""
        self.reference_points.append(pixel_coords)
        self.world_points.append(world_coords)
        
    def clear_reference_points(self):
        """Clear all reference points"""
        self.reference_points = []
        self.world_points = []
        self.calibrated = False
        
    def calibrate_homography(self) -> bool:
        """Calculate homography matrix from reference points"""
        if len(self.reference_points) < 4:
            print("Error: Need at least 4 reference points for homography calibration")
            return False
            
        # Convert to numpy arrays
        src_points = np.array(self.reference_points, dtype=np.float32)
        dst_points = np.array(self.world_points, dtype=np.float32)
        
        # Calculate homography matrix
        self.homography_matrix, mask = cv2.findHomography(
            src_points, dst_points, cv2.RANSAC, 5.0
        )
        
        if self.homography_matrix is None:
            print("Error: Failed to calculate homography matrix")
            return False
            
        # Calculate inverse homography for reverse transformation
        self.inverse_homography = np.linalg.inv(self.homography_matrix)
        self.calibrated = True
        
        print(f"Homography calibration successful with {len(self.reference_points)} points")
        return True
        
    def pixel_to_world(self, pixel_coords: Tuple[float, float]) -> Tuple[float, float]:
        """Transform pixel coordinates to world coordinates"""
        if not self.calibrated:
            raise RuntimeError("Coordinate transform not calibrated")
            
        # Convert to homogeneous coordinates
        pixel_point = np.array([pixel_coords[0], pixel_coords[1], 1.0], dtype=np.float32)
        
        # Apply homography transformation
        world_point = self.homography_matrix @ pixel_point
        
        # Convert back from homogeneous coordinates
        if world_point[2] == 0:
            raise ValueError("Invalid transformation result")
            
        return (world_point[0] / world_point[2], world_point[1] / world_point[2])
        
    def world_to_pixel(self, world_coords: Tuple[float, float]) -> Tuple[float, float]:
        """Transform world coordinates to pixel coordinates"""
        if not self.calibrated:
            raise RuntimeError("Coordinate transform not calibrated")
            
        # Convert to homogeneous coordinates
        world_point = np.array([world_coords[0], world_coords[1], 1.0], dtype=np.float32)
        
        # Apply inverse homography transformation
        pixel_point = self.inverse_homography @ world_point
        
        # Convert back from homogeneous coordinates
        if pixel_point[2] == 0:
            raise ValueError("Invalid transformation result")
            
        return (pixel_point[0] / pixel_point[2], pixel_point[1] / pixel_point[2])
        
    def undistort_point(self, pixel_coords: Tuple[float, float]) -> Tuple[float, float]:
        """Remove camera distortion from pixel coordinates"""
        if self.camera_matrix is None or self.dist_coeffs is None:
            return pixel_coords
            
        # Convert to format expected by OpenCV
        point = np.array([[pixel_coords]], dtype=np.float32)
        
        # Undistort the point
        undistorted = cv2.undistortPoints(
            point, self.camera_matrix, self.dist_coeffs, P=self.camera_matrix
        )
        
        return (undistorted[0][0][0], undistorted[0][0][1])
        
    def transform_with_distortion_correction(self, pixel_coords: Tuple[float, float]) -> Tuple[float, float]:
        """Complete transformation with distortion correction"""
        # First remove distortion
        undistorted_coords = self.undistort_point(pixel_coords)
        
        # Then apply coordinate transformation
        return self.pixel_to_world(undistorted_coords)
        
    def calculate_transformation_error(self) -> float:
        """Calculate RMS error of the current transformation"""
        if not self.calibrated or not self.reference_points:
            return float('inf')
            
        total_error = 0.0
        for pixel_pt, world_pt in zip(self.reference_points, self.world_points):
            transformed = self.pixel_to_world(pixel_pt)
            error = np.sqrt(
                (transformed[0] - world_pt[0])**2 + 
                (transformed[1] - world_pt[1])**2
            )
            total_error += error**2
            
        return np.sqrt(total_error / len(self.reference_points))
        
    def save_calibration(self, filepath: str):
        """Save calibration data to JSON file"""
        calibration_data = {
            "homography_matrix": self.homography_matrix.tolist() if self.homography_matrix is not None else None,
            "camera_matrix": self.camera_matrix.tolist() if self.camera_matrix is not None else None,
            "dist_coeffs": self.dist_coeffs.tolist() if self.dist_coeffs is not None else None,
            "reference_points": self.reference_points,
            "world_points": self.world_points,
            "calibrated": self.calibrated,
            "rms_error": self.calculate_transformation_error() if self.calibrated else None
        }
        
        with open(filepath, 'w') as f:
            json.dump(calibration_data, f, indent=2)
            
        print(f"Calibration data saved to {filepath}")
        
    def load_calibration(self, filepath: str) -> bool:
        """Load calibration data from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            if data.get("homography_matrix"):
                self.homography_matrix = np.array(data["homography_matrix"], dtype=np.float32)
                self.inverse_homography = np.linalg.inv(self.homography_matrix)
                
            if data.get("camera_matrix"):
                self.camera_matrix = np.array(data["camera_matrix"], dtype=np.float32)
                
            if data.get("dist_coeffs"):
                self.dist_coeffs = np.array(data["dist_coeffs"], dtype=np.float32)
                
            self.reference_points = data.get("reference_points", [])
            self.world_points = data.get("world_points", [])
            self.calibrated = data.get("calibrated", False)
            
            print(f"Calibration data loaded from {filepath}")
            if self.calibrated:
                rms_error = self.calculate_transformation_error()
                print(f"Transformation RMS error: {rms_error:.4f}")
                
            return True
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading calibration file: {e}")
            return False
            
    def get_calibration_info(self) -> Dict[str, Any]:
        """Get information about current calibration state"""
        return {
            "calibrated": self.calibrated,
            "reference_points_count": len(self.reference_points),
            "has_camera_intrinsics": self.camera_matrix is not None,
            "rms_error": self.calculate_transformation_error() if self.calibrated else None,
            "homography_matrix": self.homography_matrix.tolist() if self.homography_matrix is not None else None
        }

class AdaptiveCoordinateTransform(CoordinateTransform):
    """Extended coordinate transform with adaptive calibration capabilities"""
    
    def __init__(self, max_reference_points: int = 20):
        super().__init__()
        self.max_reference_points = max_reference_points
        self.point_weights = []
        self.confidence_threshold = 0.8
        
    def add_weighted_reference_point(self, pixel_coords: Tuple[float, float], 
                                   world_coords: Tuple[float, float], 
                                   confidence: float = 1.0):
        """Add a reference point with confidence weighting"""
        if confidence < self.confidence_threshold:
            return
            
        self.reference_points.append(pixel_coords)
        self.world_points.append(world_coords)
        self.point_weights.append(confidence)
        
        # Remove oldest points if we exceed maximum
        if len(self.reference_points) > self.max_reference_points:
            self.reference_points.pop(0)
            self.world_points.pop(0)
            self.point_weights.pop(0)
            
    def calibrate_weighted_homography(self) -> bool:
        """Calculate homography with weighted reference points"""
        if len(self.reference_points) < 4:
            return False
            
        # Use higher confidence points more heavily
        weights = np.array(self.point_weights)
        weights = weights / np.sum(weights)  # Normalize
        
        src_points = np.array(self.reference_points, dtype=np.float32)
        dst_points = np.array(self.world_points, dtype=np.float32)
        
        # For weighted homography, repeat points based on weights
        weighted_src = []
        weighted_dst = []
        
        for i, (src, dst, weight) in enumerate(zip(src_points, dst_points, weights)):
            # Add point multiple times based on weight
            repeat_count = max(1, int(weight * 10))
            for _ in range(repeat_count):
                weighted_src.append(src)
                weighted_dst.append(dst)
                
        weighted_src = np.array(weighted_src, dtype=np.float32)
        weighted_dst = np.array(weighted_dst, dtype=np.float32)
        
        self.homography_matrix, mask = cv2.findHomography(
            weighted_src, weighted_dst, cv2.RANSAC, 5.0
        )
        
        if self.homography_matrix is None:
            return False
            
        self.inverse_homography = np.linalg.inv(self.homography_matrix)
        self.calibrated = True
        
        return True
        
    def update_calibration_online(self, pixel_coords: Tuple[float, float],
                                world_coords: Tuple[float, float],
                                confidence: float = 1.0):
        """Update calibration with new reference point online"""
        self.add_weighted_reference_point(pixel_coords, world_coords, confidence)
        
        if len(self.reference_points) >= 4:
            return self.calibrate_weighted_homography()
            
        return False

def create_grid_calibration_points(image_width: int, image_height: int,
                                 world_width: float, world_height: float,
                                 grid_size: int = 3) -> Tuple[List[Tuple[float, float]], 
                                                            List[Tuple[float, float]]]:
    """Create a grid of calibration points for initial setup"""
    pixel_points = []
    world_points = []
    
    for i in range(grid_size):
        for j in range(grid_size):
            # Pixel coordinates (with some margin from edges)
            margin_x = image_width * 0.1
            margin_y = image_height * 0.1
            
            px = margin_x + (image_width - 2 * margin_x) * i / (grid_size - 1)
            py = margin_y + (image_height - 2 * margin_y) * j / (grid_size - 1)
            
            # World coordinates
            wx = world_width * i / (grid_size - 1)
            wy = world_height * j / (grid_size - 1)
            
            pixel_points.append((px, py))
            world_points.append((wx, wy))
            
    return pixel_points, world_points