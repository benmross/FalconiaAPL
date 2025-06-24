import paho.mqtt.client as mqtt

BROKER = "172.20.10.2"  # Use the Pi's IP if "raspberrypi.local" doesn't work
PORT = 1883
TOPIC_SEND = "laptop_to_pi"
TOPIC_RECEIVE = "pi_to_laptop"

def on_message(client, userdata, msg):
    print(f"Pi: {msg.payload.decode()}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  # Updated for MQTT v5 compatibility
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.subscribe(TOPIC_RECEIVE)
client.loop_start()

print("Type a message to send to Raspberry Pi:")
while True:
    message = input("> ")
    client.publish(TOPIC_SEND, message)
