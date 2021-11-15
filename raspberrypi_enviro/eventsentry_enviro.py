#!/usr/bin/env python3

########################################
# These values can be adjusted and only
# affect the LCD display

thresholdTemp = 80

fontSize = 17
lcdColorBackground = (0, 170, 170)
lcdColorTempHigh = (255, 0, 0)
########################################

import ST7735
import socket
import sys
import logging
import time

from bme280 import BME280
from PIL import Image, ImageDraw, ImageFont
from fonts.ttf import RobotoMedium as UserFont

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

# Get IP address
def getIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# Get temperature, adjusted for CPU heat
def get_cpu_temperature():
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp = f.read()
        temp = int(temp) / 1000.0
        temp = temp * 9.0/5.0+32
    return temp

# Display text on LCD
def lcdShowText(x, y, bgColor, text):
    draw.rectangle((0, 0, 160, 80), bgColor)
    draw.text((x, y), text, font=font, fill=text_colour)
    disp.display(img)

# Tuning factor for compensation. Decrease this number to adjust the
# temperature down, and increase to adjust up
factor = 2.25

cpu_temps = [get_cpu_temperature()] * 5

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

logging.info("""eventsentry_enviro.py - Prints and stores temperature, humidity and light readings from sensor

Press Ctrl+C to exit!
""")

# Get hostname and IP
hostName = socket.gethostname()
hostIP = getIP()

# ######################################
# Create LCD class instance & initialize
disp = ST7735.ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
)
disp.begin()
WIDTH = disp.width
HEIGHT = disp.height

# Display EventSentry logo
image = Image.open('eventsentry_enviro.gif')
frame = 0

while True:
    try:
        image.seek(frame)
        disp.display(image.resize((WIDTH, HEIGHT)))
        frame += 1
        time.sleep(0.05)

    except EOFError:
        break

time.sleep(2)

img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

font = ImageFont.truetype(UserFont, fontSize)
text_colour = (255, 255, 255)

message = hostName + "\n" + hostIP

size_x, size_y = draw.textsize(message, font)

# Display host name and IP address
lcdShowText(0, 0, lcdColorBackground, message)

time.sleep(2)
# ######################################

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

    # Display stats on LCD
    lcdBackground = lcdColorBackground
    message = "{}\nTemp: {:.1f}F\nHumidity: {:.1f}%\nLight: {:.1f}lux".format(time.strftime('%H:%M:%S'), temperature_adj, humidity, lux)
    if temperature_adj >= thresholdTemp:
        lcdBackground = lcdColorTempHigh
    lcdShowText(0, 0, lcdBackground, message)

    with open('/tmp/es_temperature.txt', 'w') as f:
        f.write("{:.0f}".format(temperature_adj))
    with open('/tmp/es_humidity.txt', 'w') as f:
        f.write("{:.0f}".format(humidity))
    with open('/tmp/es_light.txt', 'w') as f:
        f.write("{:.0f}".format(lux))
    with open('/tmp/es_proximity.txt', 'w') as f:
        f.write("{:.0f}".format(proximity))

    time.sleep(2)
