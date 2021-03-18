########################################################################
# Raspberry Pi Greenhouse Controller
# The basic concept is to monitor the greenhouse environment
# Air temperature, humidity, barometric pressure with the BME280 sensor
# and to monitor soil moisture in various beds in the green house
# (up to x soil moisture monitors, x = number of Analog Inputs available)
# Arduino Analog Inputs will be used, Arduino is running StandardFirmata script
# Pi is interfacing to Arduino via pyFirmata
# There will be fans and watering systems that will be activated if 
# thresholds are met and remotely activated.
# The system will interface with IoT site, initially Cayenne, to upload data for graphing
# and to allow for manually turning on fans or water
# There is also a local display on the Pi (for now the SSD1306)
# This version of gardener will use the blynk iot framework for remote monitoring/access
#
# authored: tom wil farley 09Mar2021
# version: 0.0.5
########################################################################

# General Python modules to import
import time
import subprocess
from datetime import datetime
import sys

########################################################################
# Adrafruit modules for GPIO and SSD1306 OLED display
# The adafruit libraries must be cloned from Adafruit repositories
# and installed as part of circuitPython 
# example, it is suggested to check the internetmachine for current repos
# sudo apt-get update
# sudo apt-get install build-essential python-pip python-dev python-smbus git
# git clone https://github.com/adafruit/Adafruit_Python_GPIO.git
# cd Adafruit_Python_GPIO
# sudo python3 setup.py install
########################################################################
import RPi.GPIO as GPIO
#import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# pyfirmata is used to interface with an Arduino running the StandardFirmata image
import pyfirmata
# bme280lib module for temperature, humidity, pressure sensor
import bme280lib

# blynk module for remote access
import blynklib

# counter used to control blynk access
class Counter:
    cycle = 0

# determine the soil moisture sensors range for sand and mud
# assign the values below with the recorded values
sand = 0.51
mud = 0.26
# assign arduino analog pin for capacitive soil moisture sensor
ANALOG_SOIL_MOISTURE_PIN = 0

# initialize blynk authentication and messaging
BLYNK_AUTH = 'I5I1yJvFWvS-UXdibwbLAM2Kk-ahepbd'
blynk = blynklib.Blynk(BLYNK_AUTH, heartbeat=15)

# assign colors, values, and virtual pins for blynk interface
T_CRI_VALUE = 0.0  # 0.0°C
T_CRI_MSG = 'Low TEMP!!!'
T_CRI_COLOR = '#c0392b'

T_COLOR = '#f5b041'
H_COLOR = '#85c1e9'
P_COLOR = '#a2d9ce'
M_COLOR = '#58d68d'
ERR_COLOR = '#444444'

# assign virtual pin #s for temperature, humidity, pressure, and 
# soil moisture, used with blynk for data display
T_VPIN = 7
H_VPIN = 8
P_VPIN = 9
M_VPIN = 10

# assign virtual pin for control of fan(s) and water
F1_VPIN = 3
F2_VPIN = 4
W1_VPIN = 5
W2_VPIN = 6
On = True
Off = False

# the blynk event handler that will be used to read the sensors
# and publish the data/information to the blynk project
# A single vpin is used to trigger the event to read all sensor data
@blynk.handle_event('read V{}'.format(T_VPIN))
def read_sensor_handler(pin):
  padding = -2
  top = padding
  bottom = height-padding
  x = 0    # get the current datetime
  # Converting datetime object to string
  dateTimeObj = datetime.now()
  timestampStr = dateTimeObj.strftime("%d-%b-%Y %H:%M:%S")
  print('Current Time  : ', timestampStr)
  Counter.cycle += 1
  # read the BME280 sensor
  tempC,pressure,humidity = bme280lib.readBME280All()
  # read the soil moisture sensor
  sm = soilmoisture.read()
  # check that values are not False (mean not None)
  if all([tempC,pressure,humidity,sm]):
    # print BME280 data to terminal
    print("Temperature   : ", round(tempC,2), "C")
    print("Pressure      : ", round(pressure,2), "hPa")
    print("Humidity      : ", round(humidity,2), "%")
    # Read and display soil moisture sensor
    smp = round((sand - float(sm)),2)*(100/(sand - mud))
    smq = qualitySoilMoisture(smp) 
    print("Soil Moisture : ", smp, "%")
    print("Analog Raw    : ", sm)
    print("Quality       : ", smq)

    if tempC <= T_CRI_VALUE:
      blynk.set_property(T_VPIN, 'color', T_CRI_COLOR)
      # send notifications not each time but once a minute (6*10 sec)
      if Counter.cycle % 6 == 0:
          blynk.notify(T_CRI_MSG)
          Counter.cycle = 0
    else:
      blynk.set_property(T_VPIN, 'color', T_COLOR)
    blynk.set_property(T_VPIN, 'color', T_COLOR)
    blynk.set_property(H_VPIN, 'color', H_COLOR)
    blynk.set_property(P_VPIN, 'color', P_COLOR)
    blynk.set_property(M_VPIN, 'color', M_COLOR)
    blynk.virtual_write(T_VPIN, round(tempC,1))
    blynk.virtual_write(H_VPIN, round(humidity,1))
    blynk.virtual_write(P_VPIN, round(pressure,1))
    blynk.virtual_write(M_VPIN, round(smp,0))
  else:
    print('[ERROR] reading sensor data')
    blynk.set_property(vpin, 'color', ERR_COLOR)  # show aka 'disabled' that mean we errors on data read
    blynk.set_property(H_VPIN, 'color', ERR_COLOR)
    blynk.set_property(P_VPIN, 'color', ERR_COLOR)
    blynk.set_property(M_VPIN, 'color', ERR_COLOR)

    blynk.virtual_write(T_VPIN, tempC)
    blynk.virtual_write(H_VPIN, humidity)
    blynk.virtual_write(P_VPIN, pressure)
    blynk.virtual_write(M_VPIN, smp)
  if Counter.cycle % 2 == 0:
    # setup oled display
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    disp.clear()
    disp.display()

    # Write text to oled display.
    draw.text((x+4, top+4),      "Forging Our Futures" ,  font=font, fill=255)
    draw.text((x, top+16),       "Temperature : " + str(round(tempC,1)) + "C",  font=font, fill=255)
    draw.text((x, top+28),       "Humidity : " + str(round(humidity,1)) + "%",  font=font, fill=255)
    draw.text((x, top+40),       "Pressure : " + str(round(pressure,1)) + "hPa",  font=font, fill=255)
    draw.text((x+4, top+56),     timestampStr, font=font, fill=255)
    #draw.text((x+12, top+56),     "the Future Forge", font=font, fill=255)

    # Display image and wait for a couple of seconds before reading again.
    disp.image(image)
    disp.display()
  else:
    # setup oled display
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    disp.clear()
    disp.display()
    
    # Write text to oled display.
    draw.text((x+4, top+4),       "Forging Our Futures" ,  font=font, fill=255)
    draw.text((x, top+16),       "Soil Moisture : " + str(smp) + "%",  font=font, fill=255)
    draw.text((x, top+28),       "Analog Raw    : " + str(sm),  font=font, fill=255)
    draw.text((x, top+40),       "Quality       : " + smq,  font=font, fill=255)
    draw.text((x+4, top+56),     timestampStr, font=font, fill=255)
    #draw.text((x+12, top+56),     "the Future Forge", font=font, fill=255)

    # Display image and wait for a couple of seconds before reading again.
    disp.image(image)
    disp.display()


# register handler for virtual pin for Fan1 write event
@blynk.handle_event('write V{}'.format(F_VPIN))
def fan_handler(pin):
  print(WRITE_EVENT_PRINT_MSG.format(pin))
  if FAN1_STATE == Off:
    GPIO.output(FAN1, GPIO.HIGH)
    FAN1_STATE = On
  else:
    GPIO.output(FAN1, GPIO.LOW)
    FAN1_STATE = Off

     
# Initialize Arduino communications
def init_firmata():
  arduino = pyfirmata.Arduino('/dev/ttyACM0')
  print("Communication Successfully started")
  it = pyfirmata.util.Iterator(arduino)
  it.start()
  #configure analog input, A#, for reading moisture sensor
  global soilmoisture
  soilmoisture = arduino.analog[ANALOG_SOIL_MOISTURE_PIN]
  soilmoisture.enable_reporting()
  # the first read of the sensor returns the NoneType, 'None'
  print(soilmoisture.read())
  time.sleep(1)  

# Initialize the SSD1306 display
def init_ssd1306():
  RST = 0
  global disp
  disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)
  disp.begin()
  disp.clear()
  disp.display()

  global width
  width = disp.width
  global height
  height = disp.height
  global image
  image = Image.new('1', (width, height))
  global draw
  draw = ImageDraw.Draw(image)
  draw.rectangle((0,0,width,height), outline=0, fill=0)

  global font
  font = ImageFont.load_default()
  # print chip info to terminal
  (chip_id, chip_version) = bme280lib.readBME280ID()
  print ("Chip ID     : ", chip_id)
  print ("Version     : ", chip_version)
  
# what is the quality of the soil moisture
def qualitySoilMoisture (smp):
    retVal = ""
    if int(smp) < 40:
        retVal = "dry"
    elif smp >= 40 and smp < 80:
        retVal = "wet"
    else:
        retVal = "mud"
    return retVal

# initialize Fan and water IO
FAN1 = 5
FAN1_STATE = Off
def init_fan():
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(FAN1, GPIO.OUT)
  GPIO.output(FAN1, GPIO.LOW)
  FAN1_STATE = Off
  
# definition of the main() routine
def main():

  #initialize arduino communication
  init_firmata()
  #init_ssd1306 display
  init_ssd1306()  
  #initialize controllers
  init_fan()

  # this loop will run until ctrl-c is pressed
  while True:
    blynk.run()


if __name__=="__main__":
   main()


