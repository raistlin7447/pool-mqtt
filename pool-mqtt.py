import json
import time

import paho.mqtt.client as mqtt

from utils import format_pump_status, get_temp_f, get_pump_connection, PUMP_MODE_MAP_NAME

ROOT_TOPIC = "pool-droid"
MQTT_BROKER_HOST = "homeassistant.local"
MQTT_BROKER_USER = "mqtt"
MQTT_BROKER_PASS = "letmein"


DEVICE = {
    "hw_version": "Raspberry Pi 4 Model B Rev 1.2",
    "identifiers": "pool-droid_1",
    "name": "Pool"
}


def send_homeassistant_configs(client: mqtt.Client):
    ha_autodiscover_base = "homeassistant"

    pool_pump_power_config = {
        "name": "Pump Power",
        "unique_id": "pool_pump_power",
        "availability_topic": f"{ROOT_TOPIC}/status",
        "state_topic": f"{ROOT_TOPIC}/pump/status",
        "device_class": "power",
        "unit_of_measurement": "W",
        "value_template": "{{ value_json.watts }}",
        "device": DEVICE
    }
    msg = client.publish(f"{ha_autodiscover_base}/sensor/pool_pump_power/config", json.dumps(pool_pump_power_config), retain=True)
    msg.wait_for_publish(1)

    pool_pump_speed_config = {
        "name": "Pump Speed",
        "unique_id": "pool_pump_speed",
        "availability_topic": f"{ROOT_TOPIC}/status",
        "command_topic": f"{ROOT_TOPIC}/set/pump/speed",
        "state_topic": f"{ROOT_TOPIC}/pump/status",
        "unit_of_measurement": "RPM",
        "icon": "mdi:pump",
        "min": 0,
        "max": 3000,
        "step": 50,
        "value_template": "{{ value_json.rpm }}",
        "device": DEVICE
    }
    msg = client.publish(f"{ha_autodiscover_base}/number/pool_pump_speed/config", json.dumps(pool_pump_speed_config), retain=True)
    msg.wait_for_publish(1)

    pool_pump_speed_mode_config = {
        "name": "Pump Speed Mode",
        "unique_id": "pool_pump_speed_mode",
        "availability_topic": f"{ROOT_TOPIC}/status",
        "command_topic": f"{ROOT_TOPIC}/set/pump/speed_mode",
        "state_topic": f"{ROOT_TOPIC}/pump/status",
        "unit_of_measurement": "RPM",
        "icon": "mdi:pump",
        "value_template": "{{ value_json.mode }}",
        "options": PUMP_MODE_MAP_NAME.keys(),
        "device": DEVICE
    }
    msg = client.publish(f"{ha_autodiscover_base}/select/pool_pump_speed_mode/config", json.dumps(pool_pump_speed_mode_config), retain=True)
    msg.wait_for_publish(1)

    pool_cab_temp_config = {
        "name": "Cabinet Temp",
        "unique_id": "pool_cabinet_temp",
        "availability_topic": f"{ROOT_TOPIC}/status",
        "state_topic": f"{ROOT_TOPIC}/cabinet/temperature",
        "device_class": "temperature",
        "unit_of_measurement": "°F",
        "value_template": "{{ value }}",
        "device": DEVICE
    }
    msg = client.publish(f"{ha_autodiscover_base}/sensor/pool_cabinet_temp/config", json.dumps(pool_cab_temp_config), retain=True)
    msg.wait_for_publish(1)


pump = get_pump_connection()


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}", flush=True)

    # The # is a wild card meeting all topics that start with the text before it
    client.subscribe(f"{ROOT_TOPIC}/set/#")


def on_message(client, userdata, msg):
    print(f"{msg.topic} {msg.payload}", flush=True)

    if msg.topic == f"{ROOT_TOPIC}/set/pump/speed":
        pump.trpm = int(msg.payload)
        print(f"Set pump speed to {msg.payload}", flush=True)

    if msg.topic == f"{ROOT_TOPIC}/set/pump/mode":
        mode = PUMP_MODE_MAP_NAME[msg.payload]
        if mode <= 8:
            speed_str = f"SPEED_{mode:d}"
        if mode == 13:
            speed_str = f"QUICK_CLEAN"
        #pump.running_speed = speed_str
        print(f"Set pump speed to {speed_str}", flush=True)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

# Set the will message, when the Raspberry Pi is powered off, or the network is interrupted abnormally, it will send
# the will message to other clients
client.will_set(f"{ROOT_TOPIC}/status", "offline")

client.username_pw_set(MQTT_BROKER_USER, MQTT_BROKER_PASS)
client.connect(MQTT_BROKER_HOST)
client.loop_start()

send_homeassistant_configs(client)

while True:
    status_msg = client.publish(f"{ROOT_TOPIC}/status", "online", qos=1)
    status_msg.wait_for_publish(1)

    pump_status = format_pump_status(pump.status)
    pump_msg = client.publish(f"{ROOT_TOPIC}/pump/status", json.dumps(pump_status), qos=1, retain=True)
    pump_msg.wait_for_publish(1)

    temp_msg = client.publish(f"{ROOT_TOPIC}/cabinet/temperature", get_temp_f(), qos=1, retain=True)
    temp_msg.wait_for_publish(1)

    time.sleep(1)
