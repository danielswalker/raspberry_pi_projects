import RPi.GPIO as GPIO
import time

buttonPin = 26
ledPin = 21
GPIO.setmode(GPIO.BCM)

GPIO.setup(ledPin, GPIO.OUT)
ledState = GPIO.LOW
GPIO.output(ledPin, ledState)

GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

counter = 0
lastTime = 0.
lastState = None
shortestCountableInterval = 0.15
def respondToButtonTransition(channel):
    global counter
    global lastTime
    global lastState
    thisTime = time.time()
    if GPIO.input(buttonPin) == GPIO.LOW:
        ledState = GPIO.HIGH
    else:
        ledState = GPIO.LOW
    GPIO.output(ledPin, ledState)

    # first time - depending on where in bounce, could be high or low
    if lastState is None:
        if ledState:
            lastTime = thisTime
            counter += 1
            print(counter)
    elif ledState != lastState:
        if thisTime > lastTime + shortestCountableInterval:
            lastTime = thisTime
            if ledState:
                counter += 1
                print(counter)
    lastState = ledState

GPIO.add_event_detect(buttonPin, GPIO.BOTH, callback=respondToButtonTransition)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
