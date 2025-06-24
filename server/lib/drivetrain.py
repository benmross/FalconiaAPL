import RPi.GPIO as GPIO
import time
#import board
#import busio
#from adafruit_motorkit import MotorKit

#kit = MotorKit(address=0x50)
#kit = MotorKit()
print("MotorKit setup complete")


# Set the GPIO mode and pins for motor control
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

def forward():
        
        print("forwards")
def backward():
        
        print("backwards")
def left():
        
        print("left")
def right():
       
        print("right")
def up():
        
        print("up")
def down():
        
        print("down")
def stop():

        print("stop")
