from datetime import datetime
from typing import Tuple

import pypentair
import serial

try:
    from w1thermsensor import W1ThermSensor, Unit
except:
    pass

PUMP_PORT = "/dev/ttyUSB0"
W1_THERM_ADDRESS = "012057fccfca"


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


PUMP_MODE_MAP = {
    1: "Speed 1",
    2: "Speed 2",
    3: "Speed 3",
    4: "Speed 4",
    5: "Speed 5",
    6: "Speed 6",
    7: "Speed 7",
    8: "Speed 8",
    9: "Manual",
    13: "Quick Clean",
}

PUMP_MODE_MAP_NAME = {v: k for k, v in PUMP_MODE_MAP.items()}


def format_pump_status(status):
    run = status['run']
    if run == 10:
        status['run'] = "Running"
    elif run == 4:
        status['run'] = "Off"
    else:
        status['run'] = f"Unknown value {run}"

    status['mode'] = PUMP_MODE_MAP[status['mode']]

    timer_m = status['timer'][0]
    timer_s = status['timer'][1]
    if timer_m or timer_s:
        timer_m_str = f"{timer_m} hour" if timer_m == 1 else f"{timer_m} hours"
        timer_s_str = f"{timer_s} minute" if timer_s == 1 else f"{timer_s} minutes"
        status['timer'] = f"{timer_m_str} {timer_s_str}"
    else:
        status['timer'] = "No Active Timer"

    time_h = status['time'][0]
    time_m = status['time'][1]
    status['time'] = datetime.strptime(f"{time_h}:{time_m}", "%H:%M").strftime("%I:%M %p")
    return status
