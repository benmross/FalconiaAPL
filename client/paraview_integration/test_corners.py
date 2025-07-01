#!/usr/bin/env python3
"""
Test if corner calibration file exists and is readable
"""

import json
import os

def test_corner_file():
    """Test if falconia_corners.json exists and is readable"""
    
    script_dir = "/home/benmross/Documents/Projects/FalconiaAPL/client/paraview_integration"
    corner_paths = [
        'falconia_corners.json',  # Current directory
        os.path.join(script_dir, 'falconia_corners.json'),  # Script directory  
        os.path.expanduser('~/falconia_corners.json')  # Home directory
    ]
    
    print("🔍 Testing corner calibration file...")
    print("=" * 40)
    
    for i, path in enumerate(corner_paths, 1):
        print(f"{i}. Testing: {path}")
        
        if os.path.exists(path):
            print(f"   ✅ File exists")
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                print(f"   ✅ JSON is valid")
                
                if 'corners' in data:
                    print(f"   ✅ Has corners data")
                    corners = data['corners']
                    for name, corner in corners.items():
                        print(f"      {name}: {corner['pixel']}")
                else:
                    print(f"   ❌ No corners data found")
                    
            except Exception as e:
                print(f"   ❌ Error reading file: {e}")
        else:
            print(f"   ❌ File does not exist")
        print()
    
    # Check current working directory
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script directory: {script_dir}")

if __name__ == "__main__":
    test_corner_file()