import pigpio
import time

sensorPin = 19
sendStartTimeMs = 1.5
initTimeMs = 0.5
MS_TO_S = 1.0 / 1000.0


class PiConnectionError(Exception):
    """Raised when connection to pigpio cannot be established."""

    pass


class AM2302InsufficientDataRecieved(Exception):
    """Raised when too few edges are detected when reading AM2302."""

    pass


class AM2302ChecksumFailed(Exception):
    """Raised when checksum does not match payload from AM2302."""

    pass


class AM2302NoData(Exception):
    """No falling edges are available, likely because sensor hasn't been read."""

    pass


class AM2302Reader:
    def __init__(self):
        self.gpio = None  # gpio control object provided by pigpio
        self.piGpioCallback = None
        self.fallingEdgeTimesUs = []
        self.pulseDurationsUs = []
        self.checksum = None
        self.temperatureF = None
        self.relativeHumidity = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("about to exit")
        self.cleanUpGpio()

    def __del__(self):
        print("about to delete")
        self.cleanUpGpio()

    def connectToPigpio(self):
        """
        Connect AM2302Reader to pigpio daemon.

        Raises:
            PiConnectionError: If a connection to pigpio cannot be established.
        """
        self.gpio = pigpio.pi()
        if not self.gpio.connected:
            raise PiConnectionError("Failed to connect to pigpio")

    def resetForSubsequentReads(self):
        self.fallingEdgeTimesUs = []
        self.pulseDurationsUs = []
        self.checksum = None
        self.temperatureF = None
        self.relativeHumidity = None

    def respondToEdge(self, channel: int, level: bool, tickUs: int):
        """Callback function when an edge event is detected.

        Appends the edge time to an internal buffer.

        Args:
            channel (int): pin number where event was detected
            level (bool): the pin state
            tickUs (int): clock time in microseconds when event was detected
        """
        self.fallingEdgeTimesUs.append(tickUs)

    def cleanUpGpio(self):
        if self.piGpioCallback is not None:
            self.piGpioCallback.cancel()
        if self.connectedToGpio:
            self.gpio.set_mode(sensorPin, pigpio.INPUT)
            self.gpio.stop()

    def readSensor(self):
        # check connection state
        if not self.connectedToGpio:
            self.connectToPigpio()

        # set pin as output in high state
        self.gpio.set_pull_up_down(sensorPin, pigpio.PUD_UP)
        self.gpio.write(sensorPin, 1)
        self.gpio.set_mode(sensorPin, pigpio.OUTPUT)
        time.sleep(initTimeMs * MS_TO_S)

        # set output low & wait
        self.gpio.write(sensorPin, 0)
        time.sleep(sendStartTimeMs * MS_TO_S)

        # switch to input and set up callback - don't set high first; I've noticed when
        # DHT22 pulls down the first time we end up with some ~1.5 V dwell - must be a
        # voltage divider between the GPIO positive and the DHT22 pulling down
        self.gpio.set_mode(sensorPin, pigpio.INPUT)
        self.gpio.set_pull_up_down(sensorPin, pigpio.PUD_UP)
        self.piGpioCallback = self.gpio.callback(
            sensorPin, pigpio.FALLING_EDGE, self.respondToEdge
        )

        try:
            time.sleep(2.0)
        except KeyboardInterrupt:
            self.cleanUpGpio()
            raise
        self.piGpioCallback.cancel()

    def processSensorPayload(self):
        if len(self.fallingEdgeTimesUs) == 0:
            print("Read sensor first")
            raise AM2302NoData

        self.pulseDurationsUs = [
            t - s for s, t in zip(self.fallingEdgeTimesUs, self.fallingEdgeTimesUs[1:])
        ]
        try:
            self.decodePulseDurations()
        except AssertionError:
            self.cleanUpGpio()
            raise

    def decodePulseDurations(self):
        if len(self.pulseDurationsUs) == 0:
            print("Didn't get any data from sensor.")
            raise AM2302NoData
        elif len(self.pulseDurationsUs) != 41:
            print(
                "Only received {} of 40 bits from sensor, try again.".format(
                    len(self.pulseDurationsUs) - 1
                )
            )
            raise AM2302InsufficientDataRecieved

        # each pulse has a 50us low, followed by high of ~25us for 0, 75us for 1
        bits = [tDeltaUs > 100 for tDeltaUs in self.pulseDurationsUs]

        # the first pulse is the start signal from sensor, ignore
        bits.pop(0)

        RH_INDEX_RANGE = [0, 16]
        TEMP_SIGN_BIT = 16
        TEMP_INDEX_RANGE = [17, 32]
        CHECKSUM_INDEX_RANGE = [32, 41]
        AM2302_SCALE_FACTOR = 1.0 / 10.0

        relativeHumidityBytes = bitArrayToInt(
            bits[RH_INDEX_RANGE[0] : RH_INDEX_RANGE[1]]
        )
        temperatureBytes = bitArrayToInt(
            bits[TEMP_INDEX_RANGE[0] : TEMP_INDEX_RANGE[1]]
        )
        checksumByte = bitArrayToInt(
            bits[CHECKSUM_INDEX_RANGE[0] : CHECKSUM_INDEX_RANGE[1]]
        )
        if bits[TEMP_SIGN_BIT]:
            signBit = 1
        else:
            signBit = 0

        # add top byte & bottom bytes of RH, top byte (w sign bit) & bottom byte of temp
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
            raise AM2302ChecksumFailed
        self.checksum = mySum

        self.relativeHumidity = relativeHumidityBytes * AM2302_SCALE_FACTOR
        self.temperatureF = temperatureBytes * AM2302_SCALE_FACTOR * 9.0 / 5.0 + 32.0
        if bits[TEMP_SIGN_BIT]:
            self.temperatureF *= -1.0

    @property
    def connectedToGpio(self):
        return self.gpio is not None and self.gpio.connected


def bitArrayToInt(bits):
    val = 0
    for bit in bits:
        val <<= 1
        val |= bit
    return val


if __name__ == "__main__":
    with AM2302Reader() as am2302:
        for count in range(10):
            try:
                print("Is connected? {}".format(am2302.connectedToGpio))
                am2302.readSensor()
                am2302.processSensorPayload()
                print(
                    "T: {}F, RH: {}%".format(
                        round(am2302.temperatureF, 2), round(am2302.relativeHumidity, 1)
                    )
                )
            except (AM2302InsufficientDataRecieved, AM2302ChecksumFailed) as e:
                print("Caught {}, Faulty transmission, skipping".format(str(e)))
            except Exception:
                raise
            am2302.resetForSubsequentReads()
