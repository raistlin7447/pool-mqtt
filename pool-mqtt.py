import json
import time
from typing import Tuple

import paho.mqtt.client as mqtt
import pypentair
import serial

try:
    from w1thermsensor import W1ThermSensor, Unit
except:
    pass


ROOT_TOPIC = "pool-droid"
MQTT_BROKER_HOST = "homeassistant.local"
MQTT_BROKER_USER = "mqtt"
MQTT_BROKER_PASS = "letmein"

PUMP_PORT = "/dev/ttyUSB0"

W1_THERM_ADDRESS = "012057fccfca"

DEVICE = {
    "hw_version": "Raspberry Pi 4 Model B Rev 1.2",
    "identifiers": "pool-droid_1",
    "name": "Pool Droid"
}


def send_homeassistant_configs(client: mqtt.Client):
    ha_autodiscover_base = "homeassistant"

    pool_pump_power_config = {
        "name": "Pool Pump Power",
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
        "name": "Pool Pump Speed",
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

    pool_cab_temp_config = {
        "name": "Pool Cabinet Temp",
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


def get_temps(digits: int = 1) -> Tuple[float, float]:
    sensor = W1ThermSensor(sensor_id=W1_THERM_ADDRESS)
    temp_c, temp_f = sensor.get_temperatures([Unit.DEGREES_C, Unit.DEGREES_F])
    return round(temp_c, digits), round(temp_f, digits)


def get_temp_c(digits: int = 1) -> float:
    return get_temps(digits=digits)[0]


def get_temp_f(digits: int = 1) -> float:
    return get_temps(digits=digits)[1]


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")

    # The # is a wild card meeting all topics that start with the text before it
    client.subscribe(f"{ROOT_TOPIC}/set/#")


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

send_homeassistant_configs(client)

while True:
    pump_status = get_pump_connection().status
    status_msg = client.publish(f"{ROOT_TOPIC}/status", "online", qos=1)
    status_msg.wait_for_publish(1)

    pump_msg = client.publish(f"{ROOT_TOPIC}/pump/status", json.dumps(pump_status), qos=1, retain=True)
    pump_msg.wait_for_publish(1)

    temp_msg = client.publish(f"{ROOT_TOPIC}/cabinet/temperature", get_temp_f(), qos=1, retain=True)
    temp_msg.wait_for_publish(1)

    time.sleep(1)
