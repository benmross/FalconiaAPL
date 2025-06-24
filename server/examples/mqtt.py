import paho.mqtt.client as mqtt

BROKER = "localhost"  # Use "localhost" if the broker is on the Pi, or replace with Pi's IP
PORT = 1883
TOPIC_SEND = "pi_to_laptop"
TOPIC_RECEIVE = "laptop_to_pi"

def on_message(client, userdata, msg):
    print(f"Laptop: {msg.payload.decode()}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  # Updated for MQTT v5 compatibility
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.subscribe(TOPIC_RECEIVE)
client.loop_start()

print("Type a message to send to Laptop:")
while True:
    message = input("> ")
    client.publish(TOPIC_SEND, message)
