########################################################################
# # Raspberry Pi Greenhouse Controller
# The basic concept is to monitor the greenhouse environment
# Air temperature, humidity, barometric pressure with the BME280 sensor
# and to monitor soil moisture in various beds in the green house
# (up to x soil moisture monitors, x = number of Analog Inputs available)
# Arduino Analog Inputs will be used, Arduino is running StandardFirmata script
# Pi is interfacing to Arduino via pyFirmata
# There will be fans and watering systems that will be activated if 
# thresholds are met.
# The system will interface with IoT site to upload data for graphing
# and to allow for manually turning on fans or water
# There is also a local display on the Pi (for now the SSD1306)
#
# authored: tom wil farley 12Jan2021
# version: 0.0.1
########################################################################

# General Python modules to import
import time
import subprocess

# Importing Adrafruit modules for GPIO and SSD1306 OLED display
# The adafruit libraries must be cloned from Adafruit repositories
# and installed as part of circuitPython 
# example, it is suggested to check the internetmachine for current repos
# sudo apt-get update
# sudo apt-get install build-essential python-pip python-dev python-smbus git
# git clone https://github.com/adafruit/Adafruit_Python_GPIO.git
# cd Adafruit_Python_GPIO
# sudo python3 setup.py install
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# pyfirmata is used to interface with an Arduino running the StandardFirmata image
import pyfirmata
# import the bme280lib.py module
import bme280lib

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

  # this loop will run until ctrl-c is pressed
  while True:
    # read the BME280 data
    temperature,pressure,humidity = bme280lib.readBME280All()
    # print BME280 data to terminal
    print("Temperature   : ", round(temperature,2), "C")
    print("Pressure      : ", round(pressure,2), "hPa")
    print("Humidity      : ", round(humidity,2), "%")

    # Write text to oled display.
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    disp.clear()
    disp.display()

    draw.text((x+4, top+4),       "Forging Our Futures" ,  font=font, fill=255)
    draw.text((x, top+16),       "Temperature : " + str(round(temperature,1)) + "C",  font=font, fill=255)
    draw.text((x, top+28),       "Humidity : " + str(round(humidity,1)) + "%",  font=font, fill=255)
    draw.text((x, top+40),       "Pressure : " + str(round(pressure,1)) + "hPa",  font=font, fill=255)
    draw.text((x+12, top+56),     "the Future Forge", font=font, fill=255)

    # Display image and wait for a couple of seconds before reading again.
    disp.image(image)
    disp.display()
    time.sleep(2)
    
    # Read and display soil moisture sensor
    sm = soilmoisture.read()
    smp = round((sand - float(sm)),2)*(100/(sand - mud))
    print("Soil Moisture : ", smp, "%")
    print("Analog Raw    : ", sm)
    # Write text to oled display.
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    disp.clear()
    disp.display()

    draw.text((x+4, top+4),       "Forging Our Futures" ,  font=font, fill=255)
    draw.text((x, top+28),       "Soil Moisture : " + str(smp) + "%",  font=font, fill=255)
    draw.text((x, top+40),       "Analog Raw    : " + str(sm),  font=font, fill=255)
    draw.text((x+12, top+56),     "the Future Forge", font=font, fill=255)

    # Display image and wait for a couple of seconds before reading again.
    disp.image(image)
    disp.display()
    time.sleep(2)

if __name__=="__main__":
   main()


