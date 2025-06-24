import cv2
import numpy as np
from pupil_apriltags import Detector

class AprilTagDetector:
    def __init__(self):
        # Initialize AprilTag detector with default settings
        self.detector = Detector(
            families="tag36h11",  # Default tag family
            nthreads=1,
            quad_decimate=1.0,
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
            debug=0
        )
        
        # Default camera parameters (can be updated with calibration data)
        # These are placeholder values - for accurate pose estimation, real calibration is needed
        self.camera_params = {
            'fx': 500.0,  # focal length x
            'fy': 500.0,  # focal length y
            'cx': 320.0,  # principal point x
            'cy': 240.0,  # principal point y
            'tag_size': 0.15  # tag size in meters
        }
        
    def set_camera_params(self, fx, fy, cx, cy, tag_size):
        """Update camera parameters for better pose estimation"""
        self.camera_params = {
            'fx': fx,
            'fy': fy,
            'cx': cx,
            'cy': cy,
            'tag_size': tag_size
        }
        
    def detect(self, frame):
        """Detect AprilTags in the frame and return detection info"""
        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        else:
            gray = frame
            
        # Run detection
        tags = self.detector.detect(
            gray, 
            estimate_tag_pose=True,
            camera_params=[
                self.camera_params['fx'], 
                self.camera_params['fy'], 
                self.camera_params['cx'], 
                self.camera_params['cy']
            ],
            tag_size=self.camera_params['tag_size']
        )
        
        return tags
    
    def draw_tags(self, frame, tags):
        """Draw detection results on the frame"""
        for tag in tags:
            # Extract tag information
            tag_id = tag.tag_id
            center = (int(tag.center[0]), int(tag.center[1]))
            corners = tag.corners.astype(int)
            
            # Draw tag outline and ID
            cv2.polylines(frame, [corners], True, (0, 255, 0), 2)
            cv2.putText(frame, f"ID: {tag_id}", (center[0] - 10, center[1] - 10),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Draw orientation if pose information is available
            if hasattr(tag, 'pose_R') and hasattr(tag, 'pose_t'):
                try:
                    # Project the 3D axes onto the image
                    axis_length = self.camera_params['tag_size'] / 2
                    projection_matrix = np.array([
                        [self.camera_params['fx'], 0, self.camera_params['cx']],
                        [0, self.camera_params['fy'], self.camera_params['cy']],
                        [0, 0, 1]
                    ])
                    
                    # Define 3D axes in tag coordinate frame
                    axes_3d = np.array([
                        [axis_length, 0, 0],  # X-axis (red)
                        [0, axis_length, 0],  # Y-axis (green)
                        [0, 0, axis_length]   # Z-axis (blue)
                    ], dtype=np.float32)
                    
                    # Project origin point - ensure proper format for projectPoints
                    origin = np.zeros((1, 3), dtype=np.float32)
                    
                    # Convert rotation and translation to correct types
                    rotation = np.asarray(tag.pose_R, dtype=np.float64)
                    translation = np.asarray(tag.pose_t, dtype=np.float64)
                    
                    # Project origin
                    origin_projection, _ = cv2.projectPoints(
                        origin, rotation, translation, projection_matrix, None
                    )
                    origin_point = tuple(map(int, origin_projection[0][0]))
                    
                    # Project each axis endpoint
                    colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]  # RGB colors for axes
                    for i in range(3):
                        axis_point = np.array([[axes_3d[i][0], axes_3d[i][1], axes_3d[i][2]]], dtype=np.float32)
                        projected_point, _ = cv2.projectPoints(
                            axis_point, rotation, translation, projection_matrix, None
                        )
                        p_point = tuple(map(int, projected_point[0][0]))
                        cv2.line(frame, origin_point, p_point, colors[i], 2)
                    
                    # Add pose information as text
                    rot = np.degrees(cv2.Rodrigues(rotation)[0].flatten())
                    distance = np.linalg.norm(translation)
                    
                    # Display distance and rotation around Y axis (yaw)
                    cv2.putText(frame, f"D: {distance:.2f}m", 
                              (center[0] - 10, center[1] + 15),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                    cv2.putText(frame, f"Y: {rot[1]:.1f}°", 
                              (center[0] - 10, center[1] + 30),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                except Exception as e:
                    # Fall back to simple orientation if 3D projection fails
                    print(f"Warning: Failed to draw 3D axes: {e}")
                    center_to_top = (int((corners[0][0] + corners[3][0]) / 2), 
                                    int((corners[0][1] + corners[3][1]) / 2))
                    cv2.line(frame, center, center_to_top, (255, 0, 0), 2)
            else:
                # Simple orientation indicator when no pose is available
                center_to_top = (int((corners[0][0] + corners[3][0]) / 2), 
                                int((corners[0][1] + corners[3][1]) / 2))
                cv2.line(frame, center, center_to_top, (255, 0, 0), 2)
        
        return frame