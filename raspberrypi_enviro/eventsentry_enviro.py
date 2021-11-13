#!/usr/bin/env python3

import time
from bme280 import BME280

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

import logging

def get_cpu_temperature():
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp = f.read()
        temp = int(temp) / 1000.0
        temp = temp * 9.0/5.0+32
    return temp

# Tuning factor for compensation. Decrease this number to adjust the
# temperature down, and increase to adjust up
factor = 2.25

cpu_temps = [get_cpu_temperature()] * 5

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

logging.info("""eventsentry.py - Prints and stores temperature, humidity and light readings from sensor

Press Ctrl+C to exit!

""")

bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)

last_proximity_alert = 0
last_proximity = 0

while True:
    timeNow = int(time.time())

    temperature = bme280.get_temperature() * 9.0/5.0+32
    temperature_cpu = get_cpu_temperature()
    cpu_temps = cpu_temps[1:] + [temperature_cpu]
    temperature_cpu_avg = sum(cpu_temps) / len(cpu_temps)
    
    temperature_adj = temperature - ((temperature_cpu_avg - temperature) / factor)
    pressure = bme280.get_pressure()
    humidity = bme280.get_humidity()
    lux = ltr559.get_lux()
    proximity = ltr559.get_proximity()
    proximity_raw = proximity

    if proximity > 1:
        last_proximity_alert = int(time.time())
        if proximity > last_proximity:
            last_proximity = proximity

    if last_proximity_alert > (timeNow - 60):
        proximity = last_proximity
    else:
        last_proximity_alert = 0
        last_proximity = 0

    logging.info("""
Temperature: {:05.2f} F
Pressure: {:05.2f} hPa
Relative humidity: {:05.2f} %
Light: {:05.2f} Lux
Proximity: {:05.2f} Unfiltered: {:05.2f}
""".format(temperature_adj, pressure, humidity, lux, proximity, proximity_raw))

    with open('/tmp/es_temperature.txt', 'w') as f:
        f.write("{:.0f}".format(temperature_adj))
    with open('/tmp/es_humidity.txt', 'w') as f:
        f.write("{:.0f}".format(humidity))
    with open('/tmp/es_light.txt', 'w') as f:
        f.write("{:.0f}".format(lux))
    with open('/tmp/es_proximity.txt', 'w') as f:
        f.write("{:.0f}".format(proximity))

    time.sleep(2)
