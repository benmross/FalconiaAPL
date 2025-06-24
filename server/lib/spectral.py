import time
import board
from adafruit_as726x import AS726x_I2C


# Initialize I2C bus and sensor
sensor = None
try:
    i2c = board.I2C()
    sensor = AS726x_I2C(i2c)
    sensor.conversion_mode = sensor.MODE_2
    
    # Set driver LED current to 100mA.
    # The user's example code used `100`, which is not a valid enum value.
    # Using the correct enum for 100mA from the library.
    sensor.driver_led_current = 100
    
    sensor.driver_led = False
    print("Spectral sensor initialized.")
    print(f"LED enabled: {sensor.driver_led}")
    print(f"LED current: {sensor.driver_led_current}")

except Exception as e:
    print(f"Failed to initialize spectral sensor: {e}", "error")
    sensor = None # Ensure sensor is None if initialization fails

def collect():
    """
    Takes a snapshot of the spectral data.
    Turns on the driver LED, waits for data, reads sensor values,
    and then turns off the LED.
    Returns a dictionary with the spectral data.
    """
    if not sensor:
        print("Spectral sensor not initialized.", "error")
        return None

    try:
        sensor.driver_led = True
        time.sleep(1)  # Allow sensor to stabilize

        # Wait for data to be ready
        while not sensor.data_ready:
            time.sleep(0.1)

        data = {
            "violet": sensor.violet,
            "blue": sensor.blue,
            "green": sensor.green,
            "yellow": sensor.yellow,
            "orange": sensor.orange,
            "red": sensor.red,
        }
        
        print(f"Spectral data collected: {data}")

        time.sleep(0.25)
        sensor.driver_led = False
        
        return data
    except Exception as e:
        print(f"Error collecting spectral data: {e}", "error")
        # Ensure LED is off in case of error
        try:
            sensor.driver_led = False
        except:
            pass
        return None

if __name__ == '__main__':
    # This is an example of how to use the library
    if sensor:
        # In a real application, you would import this module
        # and call spectral.collect()
        while True:
            print("Collecting spectral data...")
            spectral_data = collect()
            if spectral_data:
                print("Spectral Data:")
                # Sort by wavelength for better readability (V,B,G,Y,O,R)
                sorted_keys = ["violet", "blue", "green", "yellow", "orange", "red"]
                for key in sorted_keys:
                    value = spectral_data[key]
                    print(f"  {key.capitalize()}: {value}")
            else:
                print("Failed to collect data.")
            
            print("\nWaiting for 2 seconds before next reading...")
            time.sleep(2)
    else:
        print("Sensor not initialized. Please check connections and logs.")
