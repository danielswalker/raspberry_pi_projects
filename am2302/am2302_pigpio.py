import pigpio
import time

sensorPin = 19
sendStartTimeMs = 1.5
initTimeMs = 0.5
MS_TO_S = 1.0 / 1000.0
transitionBufferUs = []

pi = pigpio.pi()
if not pi.connected:
    exit()


def respondToTransition(channel, level, tickUs):
    global transitionBufferUs
    transitionBufferUs.append(tickUs)


def bitArrayToInt(bits):
    val = 0
    for bit in bits:
        val <<= 1
        val |= bit
    return val


def decodeTDeltasUs(tDeltasUs):
    if len(tDeltasUs) == 0:
        print("Didn't get any data from sensor.")
        raise AssertionError
    elif len(tDeltasUs) != 41:
        print(
            "Only received {} of 40 bits from sensor, try again.".format(
                len(tDeltasUs) - 1
            )
        )
        raise AssertionError

    # each pulse has a 50us low, followed by high of ~25us for 0, 75us for 1
    bits = [tDeltaUs > 100 for tDeltaUs in tDeltasUs]

    # the first pulse is the start signal from sensor, ignore
    bits.pop(0)

    RH_INDEX_RANGE = [0, 16]
    TEMP_SIGN_BIT = 16
    TEMP_INDEX_RANGE = [17, 32]
    CHECKSUM_INDEX_RANGE = [32, 41]
    AM2302_SCALE_FACTOR = 1.0 / 10.0

    relativeHumidityBytes = bitArrayToInt(bits[RH_INDEX_RANGE[0] : RH_INDEX_RANGE[1]])
    temperatureBytes = bitArrayToInt(bits[TEMP_INDEX_RANGE[0] : TEMP_INDEX_RANGE[1]])
    checksumByte = bitArrayToInt(
        bits[CHECKSUM_INDEX_RANGE[0] : CHECKSUM_INDEX_RANGE[1]]
    )
    if bits[TEMP_SIGN_BIT]:
        signBit = 1
    else:
        signBit = 0

    # add top byte & bottom bytes of RH, top byte (w sign bit) and bottom byte of temp
    mySum = (
        ((relativeHumidityBytes & 0xFF00) >> 8)
        + (relativeHumidityBytes & 0xFF)
        + (signBit << 7)
        + ((temperatureBytes & 0xFF00) >> 8)
        + (temperatureBytes & 0xFF)
    ) & 0xFF

    try:
        assert checksumByte == mySum
    except AssertionError:
        print(
            "Failed checksum verification {} != {}".format(
                bin(mySum), bin(checksumByte)
            )
        )
        raise

    relativeHumidity = relativeHumidityBytes * AM2302_SCALE_FACTOR
    temperatureF = temperatureBytes * AM2302_SCALE_FACTOR * 9.0 / 5.0 + 32.0
    if bits[TEMP_SIGN_BIT]:
        temperatureF = -temperatureF
    return temperatureF, relativeHumidity


# set up as output in high state
pi.set_pull_up_down(sensorPin, pigpio.PUD_UP)
pi.write(sensorPin, 1)
pi.set_mode(sensorPin, pigpio.OUTPUT)
time.sleep(initTimeMs * MS_TO_S)

# set output low & wait
pi.write(sensorPin, 0)
time.sleep(sendStartTimeMs * MS_TO_S)

# switch to input and set up callback - don't set high first; I've noticed when
# DHT22 pulls down the first time we end up with some ~1.5 V dwell - must be a
# voltage divider between the GPIO positive and the DHT22 pulling down
pi.set_mode(sensorPin, pigpio.INPUT)
pi.set_pull_up_down(sensorPin, pigpio.PUD_UP)
callback = pi.callback(sensorPin, pigpio.FALLING_EDGE, respondToTransition)

try:
    time.sleep(2.0)
except KeyboardInterrupt:
    pi.set_mode(sensorPin, pigpio.INPUT)
    pi.stop()
    exit()

tDeltasUs = [t - s for s, t in zip(transitionBufferUs, transitionBufferUs[1:])]
try:
    temperatureF, relativeHumidity = decodeTDeltasUs(tDeltasUs)
except AssertionError:
    pi.set_mode(sensorPin, pigpio.INPUT)
    pi.stop()
    raise
print("T: {}F, RH: {}%".format(round(temperatureF, 2), round(relativeHumidity, 1)))
pi.set_mode(sensorPin, pigpio.INPUT)
pi.stop()
