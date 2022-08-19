import RPi.GPIO as GPIO
from time import sleep

led_pin = 11
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(led_pin, GPIO.OUT)

ledPWM=GPIO.PWM(led_pin, 500)

base=100
mod=-1

ledPWM.start(base)

while True:
	base+=mod
	ledPWM.ChangeDutyCycle(base)

	if base<=10 or base>=100:
		mod=mod*-1

	sleep(0.02)