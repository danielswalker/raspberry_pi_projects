import RPi.GPIO as GPIO
import time

ledPin = 21
GPIO.setmode(GPIO.BCM)

GPIO.setup(ledPin, GPIO.OUT)
ledState = GPIO.LOW
GPIO.output(ledPin, ledState)

try:
    while True:
        ledState = not ledState
        GPIO.output(ledPin, ledState)
        time.sleep(0.5)
except KeyboardInterrupt:
    GPIO.cleanup()
