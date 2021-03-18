########################################################################
# Raspberry Pi Greenhouse Controller
# The basic concept is to monitor the greenhouse environment
# Air temperature, humidity, barometric pressure with the BME280 sensor
# and to monitor soil moisture in various beds in the green house
# (up to x soil moisture monitors, x = number of Analog Inputs available)
# Arduino Analog Inputs will be used, Arduino is running StandardFirmata script
# Pi is interfacing to Arduino via pyFirmata
# There will be fans and watering systems that will be activated if 
# thresholds are met.
# The system will interface with IoT site, initially Cayenne, to upload data for graphing
# and to allow for manually turning on fans or water
# There is also a local display on the Pi (for now the SSD1306)
#
# authored: tom wil farley 06Mar2021
# version: 0.0.3
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
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# pyfirmata is used to interface with an Arduino running the StandardFirmata image
import pyfirmata
# bme280lib module for temperature, humidity, pressure sensor
import bme280lib


# MQTT module for Cayenne interface
import paho.mqtt.client as mqtt

#MQTT Cayenne setup - you will need your own username, password and clientid
#To setup a Cayenne account go to https://mydevices.com/cayenne/signup/
username = "791abc40-5e97-11eb-b767-3f1a8f1211ba"
password = "d3c274038c9da86fc8a69bb59603d9622004a908"
clientid = "91da8630-7dcc-11eb-b767-3f1a8f1211ba"
mqttc=mqtt.Client(client_id = clientid)
mqttc.username_pw_set(username, password = password)
mqttc.connect("mqtt.mydevices.com", port=1883, keepalive=60)
mqttc.loop_start()

#set MQTT topics (we are not setting topics for everything)
topic_bme_temp = "v1/" + username + "/things/" + clientid + "/data/1"
topic_bme_hum = "v1/" + username + "/things/" + clientid + "/data/2"
topic_bme_pressure = "v1/" + username + "/things/" + clientid + "/data/3"
topic_soil_moisture = "v1/" + username + "/things/" + clientid + "/data/4"

# determine the soil moisture sensors range for sand and mud
# replace the values below with the recorded values
sand = 0.51
mud = 0.26

# Initialize Arduino communications
def init_firmata():
  arduino = pyfirmata.Arduino('/dev/ttyACM0')
  print("Communication Successfully started")
  it = pyfirmata.util.Iterator(arduino)
  it.start()
  #configure analog input, A0, for reading moisture sensor
  global soilmoisture
  soilmoisture = arduino.analog[0]
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
  
# definition of the main() routine
def main():

  #initialize arduino communication
  init_firmata()
  #init_ssd1306 display
  init_ssd1306()  
  padding = -2
  top = padding
  bottom = height-padding
  x = 0
  # data refresh rate
  refreshTime = 15

  # this loop will run until ctrl-c is pressed
  while True:
    # setup oled display
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    disp.clear()
    disp.display()
    # get the current datetime
    # Converting datetime object to string
    dateTimeObj = datetime.now()
    timestampStr = dateTimeObj.strftime("%d-%b-%Y %H:%M:%S")
    print('Current Time  : ', timestampStr)
    # read the BME280 data
    tempC,pressure,humidity = bme280lib.readBME280All()
    # print BME280 data to terminal
    print("Temperature   : ", round(tempC,2), "C")
    print("Pressure      : ", round(pressure,2), "hPa")
    print("Humidity      : ", round(humidity,2), "%")
    # Read and display soil moisture sensor
    sm = soilmoisture.read()
    smp = round((sand - float(sm)),2)*(100/(sand - mud))
    qsm = qualitySoilMoisture(smp) 
    print("Soil Moisture : ", smp, "%")
    print("Analog Raw    : ", sm)
    print("Quality       : ", qsm)

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

    #publishing data to Cayenne (we are not publishing everything)
    mqttc.publish (topic_bme_temp, payload = tempC, retain = True)
    mqttc.publish (topic_bme_hum, payload = humidity, retain = True)
    mqttc.publish (topic_bme_pressure, payload = pressure, retain = True)
    mqttc.publish (topic_soil_moisture, payload = smp, retain = True)

    time.sleep(refreshTime)
    
    # setup oled display
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    disp.clear()
    disp.display()
    
    # Write text to oled display.
    draw.text((x+4, top+4),       "Forging Our Futures" ,  font=font, fill=255)
    draw.text((x, top+16),       "Soil Moisture : " + str(smp) + "%",  font=font, fill=255)
    draw.text((x, top+28),       "Analog Raw    : " + str(sm),  font=font, fill=255)
    draw.text((x, top+40),       "Quality       : " + qsm,  font=font, fill=255)
    draw.text((x+4, top+56),     timestampStr, font=font, fill=255)
    #draw.text((x+12, top+56),     "the Future Forge", font=font, fill=255)

    # Display image and wait for a couple of seconds before reading again.
    disp.image(image)
    disp.display()

    time.sleep(refreshTime)

if __name__=="__main__":
   main()


