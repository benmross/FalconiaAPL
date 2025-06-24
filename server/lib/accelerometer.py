import time
import json
import board
import adafruit_mpu6050

# Initialize MPU6050
i2c = board.I2C()
mpu = adafruit_mpu6050.MPU6050(i2c)

# File to store calibration data
CALIBRATION_FILE = "mpu_calibration.json"

def save_calibration(offsets):
    """ Save calibration offsets to a file. """
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(offsets, f)

def load_calibration():
    """ Load calibration offsets from a file. """
    try:
        with open(CALIBRATION_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"accel": [0, 0, 0], "gyro": [0, 0, 0]}

def calibrate():
    """ Calibrate the sensor and save offsets. """
    samples = 500
    accel_offset = [0, 0, 0]
    gyro_offset = [0, 0, 0]
    
    print("Calibrating sensor, please keep it still...")
    
    for _ in range(samples):
        accel = mpu.acceleration
        gyro = mpu.gyro
        
        for i in range(3):
            accel_offset[i] += accel[i]
            gyro_offset[i] += gyro[i]
        
        time.sleep(0.002)  # Small delay to allow sensor readings to stabilize
    
    # Calculate the average offsets
    accel_offset = [x / samples for x in accel_offset]
    gyro_offset = [x / samples for x in gyro_offset]
    
    # Adjust acceleration to reflect Earth's gravity on Z-axis
    accel_offset[2] += 9.81  # Assuming the sensor is lying flat
    
    offsets = {"accel": accel_offset, "gyro": gyro_offset}
    save_calibration(offsets)
    print("Calibration complete! Offsets saved.")

def getAcceleration():
    """ Get acceleration values with calibration applied. """
    raw_accel = mpu.acceleration
    offsets = load_calibration()["accel"]
    return [raw_accel[i] - offsets[i] for i in range(3)]

def getGyro():
    """ Get gyro values with calibration applied. """
    raw_gyro = mpu.gyro
    offsets = load_calibration()["gyro"]
    return [raw_gyro[i] - offsets[i] for i in range(3)]

def getTemp():
    return mpu.temperature

# Attach calibration method to the MPU6050 object
mpu.calibrate = calibrate
