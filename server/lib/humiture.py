import time
import board
import adafruit_dht

# Initialize the DHT11 sensor
dhtDevice = None
try:
    # The example uses board.D17. We will use the same.
    dhtDevice = adafruit_dht.DHT11(board.D17)
    print("DHT11 sensor initialized on pin D17.")
except NotImplementedError:
    print("Board not supported. DHT11 will not be available.", "warn")
except Exception as e:
    print(f"Failed to initialize DHT11 sensor: {e}", "error")
    dhtDevice = None

def collect():
    """
    Reads temperature and humidity from the DHT11 sensor.
    Handles common runtime errors by retrying.
    Returns a dictionary with temperature in Celsius and Fahrenheit, and humidity.
    """
    if not dhtDevice:
        print("DHT11 sensor not initialized.", "error")
        return None

    try:
        # Attempt to get a reading.
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity

        # DHT11 can sometimes return None.
        if temperature_c is not None and humidity is not None:
            temperature_f = temperature_c * (9 / 5) + 32
            data = {
                "temperature_c": temperature_c,
                "temperature_f": temperature_f,
                "humidity": humidity
            }
            print(f"Humiture data collected: {data}")
            return data
        else:
            print("Failed to get a reading from DHT11 sensor.", "warn")
            return None

    except RuntimeError as error:
        # Errors happen fairly often with DHT's, so we'll just log it.
        print(f"DHT11 sensor reading error: {error.args[0]}", "warn")
        return None
    except Exception as error:
        print(f"An unexpected error occurred with DHT11 sensor: {error}", "error")
        return None

if __name__ == '__main__':
    # This is an example of how to use the library
    if dhtDevice:
        while True:
            print("Collecting humiture data...")
            humiture_data = collect()
            if humiture_data:
                print("Humiture Data:")
                print(
                    "  Temp: {temperature_f:.1f} F / {temperature_c:.1f} C    Humidity: {humidity}% ".format(
                        **humiture_data
                    )
                )
            else:
                print("Failed to collect data. Retrying...")

            print("\nWaiting for 2 seconds before next reading...")
            time.sleep(2.0)
    else:
        print("Sensor not initialized. Please check connections and logs.")
