import cv2
import numpy as np
from lib.apriltag_detector import AprilTagDetector
import argparse

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Test AprilTag detection")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera index (default: 0)")
    parser.add_argument("--url", type=str, default=None,
                        help="MJPEG stream URL (overrides camera index)")
    parser.add_argument("--tag-size", type=float, default=0.15,
                        help="AprilTag size in meters (default: 0.15)")
    parser.add_argument("--resolution", type=str, default="640x480",
                        help="Camera resolution (default: 640x480)")
    args = parser.parse_args()

    # Parse resolution
    width, height = map(int, args.resolution.split('x'))
    
    # Initialize the AprilTag detector
    detector = AprilTagDetector()
    
    # Set camera parameters based on resolution
    detector.set_camera_params(
        fx=width * 0.8,  # approximate focal length
        fy=width * 0.8,  # approximate focal length
        cx=width / 2,    # center x
        cy=height / 2,   # center y
        tag_size=args.tag_size
    )
    
    # Initialize video capture from camera or URL
    if args.url:
        print(f"Opening MJPEG stream: {args.url}")
        cap = cv2.VideoCapture(args.url)
    else:
        print(f"Opening camera index: {args.camera}")
        cap = cv2.VideoCapture(args.camera)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    if not cap.isOpened():
        print("Error: Could not open video source")
        return

    print("Press 'q' to quit")
    print("Press 's' to save a snapshot with detections")
    
    frame_count = 0
    saved_count = 0
    
    while True:
        # Read frame
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        
        # Detect AprilTags in the frame
        tags = detector.detect(frame)
        
        # Draw detections on the frame
        frame_with_tags = detector.draw_tags(frame.copy(), tags)
        
        # Display tag count in the corner
        cv2.putText(frame_with_tags, f"Tags: {len(tags)}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Display the resulting frame
        cv2.imshow('AprilTag Detection Test', frame_with_tags)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Save frame with detections
            filename = f"apriltag_detection_{saved_count}.jpg"
            cv2.imwrite(filename, frame_with_tags)
            print(f"Saved detection to {filename}")
            saved_count += 1
            
        # Print tag info every 30 frames
        if frame_count % 30 == 0 and tags:
            print(f"Detected {len(tags)} tags:")
            for i, tag in enumerate(tags):
                distance = np.linalg.norm(tag.pose_t) if hasattr(tag, 'pose_t') else "unknown"
                print(f"  Tag {i+1}: ID={tag.tag_id}, Distance={distance:.2f}m")
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()