import RPi.GPIO as GPIO
import time

buttonPin = 26
ledPin = 21
GPIO.setmode(GPIO.BCM)

GPIO.setup(ledPin, GPIO.OUT)
ledState = GPIO.LOW
GPIO.output(ledPin, ledState)

GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    while True:
        if GPIO.input(buttonPin) == GPIO.LOW:
            ledState = GPIO.HIGH
        else:
            ledState = GPIO.LOW
        GPIO.output(ledPin, ledState)
except KeyboardInterrupt:
    GPIO.cleanup()
