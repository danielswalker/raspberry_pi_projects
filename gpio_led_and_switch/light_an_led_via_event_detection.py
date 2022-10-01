import RPi.GPIO as GPIO
import time

buttonPin = 26
ledPin = 21
GPIO.setmode(GPIO.BCM)

GPIO.setup(ledPin, GPIO.OUT)
ledState = GPIO.LOW
GPIO.output(ledPin, ledState)

GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def respondToButtonTransition(channel):
        if GPIO.input(buttonPin) == GPIO.LOW:
            ledState = GPIO.HIGH
        else:
            ledState = GPIO.LOW
        GPIO.output(ledPin, ledState)

GPIO.add_event_detect(buttonPin, GPIO.BOTH, callback=respondToButtonTransition)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
