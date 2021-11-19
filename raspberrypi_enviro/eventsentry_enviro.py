#!/usr/bin/env python3

########################################
# These values can be adjusted and only
# affect the LCD display

sensorUpdateInterval = 2
lcdRefreshInterval = 10

thresholdTemp = 80
thresholdHumidity = 10

splashDelaySecs = 3

fontSize = 17
lcdColorText = (255, 255, 255)
lcdColorBackground = (0, 170, 170)
lcdColorRed = (255, 0, 0)
lcdColorOrange = (255, 165, 0)
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
def lcdShowText(x, y, bgColor, text, center):
    draw.rectangle((x, y, WIDTH, HEIGHT), bgColor)

    if center == 1:
        size_x, size_y = draw.textsize(text, font)
        x = WIDTH/2-size_x/2

    draw.text((x, y), text, font=font, fill=lcdColorText)
    disp.display(img)

def lcdShowTime():
    draw.rectangle((0, 0, WIDTH, HEIGHT/4), (82, 82, 82))
    # Calculate text size
    size_x, size_y = draw.textsize(time.strftime('%H:%M:%S'), font)
    x = WIDTH/2-size_x/2
    draw.text((x, 0), time.strftime('%H:%M:%S'), font=font, fill=lcdColorText)
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

time.sleep(splashDelaySecs)

# Show host name and IP address
img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)
font = ImageFont.truetype(UserFont, fontSize)

# Display host name and IP address
lcdShowText(0, 0, lcdColorBackground, hostName + "\n" + hostIP, 0)

time.sleep(splashDelaySecs)
# ######################################

bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)

last_proximity_alert = 0
last_proximity = 0

timeSensorCheck = 0
timeLCDUpdate = 0

while True:
    timeNow = int(time.time())

    if (timeNow - timeSensorCheck) >= sensorUpdateInterval:
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

        timeSensorCheck = int(time.time())

        if proximity > 1:
            last_proximity_alert = int(time.time())
            if proximity > last_proximity:
                last_proximity = proximity

        if last_proximity_alert > (timeNow - 60):
            proximity = last_proximity
        else:
            last_proximity_alert = 0
            last_proximity = 0

        with open('/tmp/es_temperature.txt', 'w') as f:
            f.write("{:.0f}".format(temperature_adj))
        with open('/tmp/es_humidity.txt', 'w') as f:
            f.write("{:.0f}".format(humidity))
        with open('/tmp/es_light.txt', 'w') as f:
            f.write("{:.0f}".format(lux))
        with open('/tmp/es_proximity.txt', 'w') as f:
            f.write("{:.0f}".format(proximity))

        logging.info("""
Temperature: {:05.2f} F
Pressure: {:05.2f} hPa
Relative humidity: {:05.2f} %
Light: {:05.2f} Lux
Proximity: {:05.2f} Unfiltered: {:05.2f}
""".format(temperature_adj, pressure, humidity, lux, proximity, proximity_raw))

        ######### Display stats on LCD #########
        if (timeNow - timeLCDUpdate) >= lcdRefreshInterval:
            lcdBackground = lcdColorBackground

            message = "Temp: {:.1f}F".format(temperature_adj)
            if temperature_adj >= thresholdTemp:
                lcdBackground = lcdColorRed
            lcdShowText(0, (HEIGHT/4)*1, lcdBackground, message, 1)

            message = "Humidity: {:.1f}%".format(humidity)
            if humidity < thresholdHumidity:
                lcdBackground = lcdColorOrange
            else:
                lcdBackground = lcdColorBackground
            lcdShowText(0, (HEIGHT/4)*2, lcdBackground, message, 1)

            message = "Light: {:.1f}lux".format(lux)
            lcdShowText(0, (HEIGHT/4)*3, lcdColorBackground, message, 1)

            timeLCDUpdate = int(time.time())

    lcdShowTime()
    ######### Display stats on LCD #########

    time.sleep(1)
