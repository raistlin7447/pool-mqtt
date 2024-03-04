import json
import time

import paho.mqtt.client as mqtt
import pypentair
import serial

ROOT_TOPIC = "pool-droid"
MQTT_BROKER_HOST = "homeassistant.local"
MQTT_BROKER_USER = "mqtt"
MQTT_BROKER_PASS = "letmein"

PUMP_PORT = "/dev/ttyUSB0"


def get_pump_connection():
    serial_con = serial.Serial(
        port=PUMP_PORT,
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1
    )
    return pypentair.Pump(pypentair.ADDRESSES["INTELLIFLO_PUMP_1"], serial_con)


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")

    # The # is a wild card meeting all topics that start with the text before it
    client.subscribe(f"{ROOT_TOPIC}/pump/mode")


def on_message(client, userdata, msg):
    print(f"{msg.topic} {msg.payload}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

# Set the will message, when the Raspberry Pi is powered off, or the network is interrupted abnormally, it will send
# the will message to other clients
client.will_set(f"{ROOT_TOPIC}/status", "offline")

client.username_pw_set(MQTT_BROKER_USER, MQTT_BROKER_PASS)
client.connect(MQTT_BROKER_HOST)
client.loop_start()

status_message = client.publish(f"{ROOT_TOPIC}/status", "online", qos=1)
status_message.wait_for_publish()

while True:
    pump_status = get_pump_connection().status
    client.publish(f"{ROOT_TOPIC}/pump/status", json.dumps(pump_status), qos=1, retain=True)
    time.sleep(1)
