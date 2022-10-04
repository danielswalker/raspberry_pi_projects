import RPi.GPIO as GPIO
import time
import grpc
from button_monitoring_pb2 import ButtonActions, ButtonEvent, ButtonPressCount
from button_monitoring_pb2_grpc import ButtonMonitoringStub

channel = grpc.insecure_channel("Walker:50051")
client = ButtonMonitoringStub(channel)

buttonPin = 26
ledPin = 21
GPIO.setmode(GPIO.BCM)

GPIO.setup(ledPin, GPIO.OUT)
ledState = GPIO.LOW
GPIO.output(ledPin, ledState)

GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

counter = 0
def respondToButtonTransition(channel):
    global counter
    thisTime = time.time()
    if GPIO.input(buttonPin) == GPIO.LOW:
        ledState = GPIO.HIGH
        action = ButtonActions.PRESS
    else:
        ledState = GPIO.LOW
        action = ButtonActions.RELEASE
    GPIO.output(ledPin, ledState)
    # call rpc
    event = ButtonEvent(action=action, timeOccurred=thisTime)
    response = client.HandleButtonEvent(event)
    if counter != response.count:
        counter = response.count
        print(counter)

GPIO.add_event_detect(buttonPin, GPIO.BOTH, callback=respondToButtonTransition)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
