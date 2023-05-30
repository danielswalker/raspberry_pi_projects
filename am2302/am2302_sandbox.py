import RPi.GPIO as GPIO
import time

sensorPin = 19 
sendStartTimeMs = 5.
initTimeMs = 15.
MS_TO_S = 1. / 1000.
GPIO.setmode(GPIO.BCM)

# set up as output in high state
pinState = GPIO.HIGH
GPIO.setup(sensorPin, GPIO.OUT, initial=pinState)
time.sleep(initTimeMs * MS_TO_S)

# pull line low long enough to signal the start
pinState = GPIO.LOW
GPIO.output(sensorPin, pinState)
time.sleep(sendStartTimeMs * MS_TO_S)

transitionBuffer = []
def respondToTransition(channel):
    # global transitionBuffer
    thisTime = time.time()
    print("something on channel {}".format(channel))
    #if GPIO.input(sensorPin) == GPIO.LOW:
    #    print("low!")
    #else:
    #    print("high!")
    transitionBuffer.append(thisTime)

def bitArrayToInt(bits):
    val = 0
    for bit in bits:
        val <<= 1
        val |= bit
    return val

def decodeTDeltasUs(tDeltasUs):

    # each pulse has a 50 us low, followed by high of 25 us for 0, 50 us for 1
    bits = [tDeltaUs > 100 for tDeltaUs in tDeltasUs]

    # the first pulse is the start signal from sensor, ignore
    bits.pop(0)

    RH_INDEX_RANGE = [0, 16]
    TEMP_INDEX_RANGE = [17, 32]
    TEMP_SIGN_BIT = 16
    AM2302_SCALE_FACTOR = 1. / 10.
    relativeHumidity = bitArrayToInt(bits[RH_INDEX_RANGE[0]:RH_INDEX_RANGE[1]]) * AM2302_SCALE_FACTOR
    temperatureF = bitArrayToInt(bits[TEMP_INDEX_RANGE[0]:TEMP_INDEX_RANGE[1]]) * AM2302_SCALE_FACTOR * 9. / 5. + 32.
    if bits[TEMP_SIGN_BIT]:
        temperatureF = -temperatureF
    return temperatureF, relativeHumidity

# configure as an input with pull up resistor; after 20-40 us sensor will pull low
GPIO.setup(sensorPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
pinState = GPIO.input(sensorPin)
tStart = time.time()
try:
    while time.time() - tStart < 2.:
        if GPIO.input(sensorPin) != pinState:
            pinState = not pinState
            if pinState == GPIO.LOW:
                transitionBuffer.append(time.time())
except KeyboardInterrupt:
    GPIO.cleanup()
tDeltasUs = [round((t - s) * 1e6) for s, t in zip(transitionBuffer, transitionBuffer[1:])]
# print(tDeltasUs)
# print(len(transitionBuffer))
temperatureF, relativeHumidity = decodeTDeltasUs(tDeltasUs)
print("T: {}F, RH: {}%".format(temperatureF, round(relativeHumidity, 1)))
# TODO - add checksum verification, buffer length checks
# TODO - I don't want this blocking; need to figure out why I can't get the event detection callback

#GPIO.add_event_detect(sensorPin, GPIO.FALLING, callback=respondToTransition)
#GPIO.add_event_callback(sensorPin, respondToTransition)
#print("added event detection")
#
#try:
#    while True:
#        time.sleep(1)
#except KeyboardInterrupt:
#    GPIO.cleanup()
#    print(transitionBuffer)
# time.sleep(2.)
# respondToTransition(sensorPin)
# print(transitionBuffer)
# GPIO.cleanup()

# GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# 
# counter = 0
# lastTime = 0.
# lastState = None
# shortestCountableInterval = 0.15
# def respondToButtonTransition(channel):
#     global counter
#     global lastTime
#     global lastState
#     thisTime = time.time()
#     if GPIO.input(buttonPin) == GPIO.LOW:
#         ledState = GPIO.HIGH
#     else:
#         ledState = GPIO.LOW
#     GPIO.output(ledPin, ledState)
# 
#     # first time - depending on where in bounce, could be high or low
#     if lastState is None:
#         if ledState:
#             lastTime = thisTime
#             counter += 1
#             print(counter)
#     elif ledState != lastState:
#         if thisTime > lastTime + shortestCountableInterval:
#             lastTime = thisTime
#             if ledState:
#                 counter += 1
#                 print(counter)
#     lastState = ledState
# 
# GPIO.add_event_detect(buttonPin, GPIO.BOTH, callback=respondToButtonTransition)
# 
# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     GPIO.cleanup()
