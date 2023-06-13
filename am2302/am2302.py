import pigpio
import time

SENSOR_PIN = 19
sendStartTimeMs = 1.5
initTimeMs = 0.5
MS_TO_S = 1.0 / 1000.0
AM2302_SCALE_FACTOR = 1.0 / 10.0
MIN_TIME_BETWEEN_READS_S = 2.0


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
        self.checksum = None
        self.temperatureF = None
        self.relativeHumidity = None
        self.lastRequestTimeS = None
        self.validatedPayloadAvailable = False

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

    def cleanUpGpio(self):
        """Clean up GPIO state"""
        if self.piGpioCallback is not None:
            self.piGpioCallback.cancel()
        if self.connectedToGpio:
            self.gpio.set_mode(SENSOR_PIN, pigpio.INPUT)
            self.gpio.stop()

    def readSensor(self):
        if self.lastRequestTimeS:
            tElapsedS = time.clock_gettime(time.CLOCK_MONOTONIC) - self.lastRequestTimeS
            if tElapsedS < MIN_TIME_BETWEEN_READS_S:
                time.sleep(MIN_TIME_BETWEEN_READS_S - tElapsedS)
        self.clearPreviousRead()
        self.getDataFromSensor()
        self.processSensorData()

    def clearPreviousRead(self):
        """Resets all values related to the previous read of the AM2302"""
        self.fallingEdgeTimesUs = []
        self.checksum = None
        self.temperatureF = None
        self.relativeHumidity = None
        self.validatedPayloadAvailable = False

    def getDataFromSensor(self):
        # check connection state
        if not self.connectedToGpio:
            self.connectToPigpio()

        # get payload from sensor
        self.sendRequestForPayload()
        self.recievePayloadTransmission()
        self.validatePayload()

    def processSensorData(self):
        if not self.validatedPayloadAvailable:
            raise Exception("There is no validated payload available to process")
        bytes = self.convertEdgeTimesIntoBytes()
        self.setChecksum(bytes)
        self.verifyChecksum(bytes)
        self.relativeHumidity, self.temperatureF = self.convertBytesToPhysicalReadings(
            bytes
        )

    def sendRequestForPayload(self):
        # set pin as output in high state
        self.gpio.set_pull_up_down(SENSOR_PIN, pigpio.PUD_UP)
        self.gpio.write(SENSOR_PIN, 1)
        self.gpio.set_mode(SENSOR_PIN, pigpio.OUTPUT)
        time.sleep(initTimeMs * MS_TO_S)

        # set output low & wait
        self.gpio.write(SENSOR_PIN, 0)
        time.sleep(sendStartTimeMs * MS_TO_S)

        # switch to input with a pull up
        self.gpio.set_mode(SENSOR_PIN, pigpio.INPUT)
        self.gpio.set_pull_up_down(SENSOR_PIN, pigpio.PUD_UP)
        self.lastRequestTimeS = time.clock_gettime(time.CLOCK_MONOTONIC)

    def recievePayloadTransmission(self):
        """Set up GPIO to detect falling edges and wait for them to arrive"""

        # check that we recently requested a payload
        self.piGpioCallback = self.gpio.callback(
            SENSOR_PIN, pigpio.FALLING_EDGE, self.respondToEdge
        )
        if time.clock_gettime(time.CLOCK_MONOTONIC) - self.lastRequestTimeS > 270e-6:
            self.piGpioCallback.cancel()
            raise Exception(
                "Did not signal device recently; might have missed pulses... "
                + "skipping payload monitoring"
            )

        # DHT22 datasheet suggests minimum time between subsequent reads should
        # be 2 seconds
        self.collectNEdges(42)
        self.piGpioCallback.cancel()

    def collectNEdges(self, nEdges):
        T_MAX = (160e-6 + 41.0 * 120e-6) * 10
        try:
            for attempt in range(2):
                if len(self.fallingEdgeTimesUs) >= nEdges:
                    break
                else:
                    time.sleep(T_MAX)
        except KeyboardInterrupt:
            raise

    def respondToEdge(self, channel: int, level: bool, tickUs: int):
        """Callback function when an edge event is detected.

        Appends the edge time to an internal buffer.

        Args:
            channel (int): pin number where event was detected
            level (bool): the pin state
            tickUs (int): clock time in microseconds when event was detected
        """
        self.fallingEdgeTimesUs.append(tickUs)

    def validatePayload(self):
        # validate the data returned
        if len(self.fallingEdgeTimesUs) == 0:
            raise AM2302NoData("Didn't get any data from sensor.")
        elif len(self.fallingEdgeTimesUs) < 41:
            raise AM2302InsufficientDataRecieved(
                "Only received {} of 40 bits from sensor, try again.".format(
                    len(self.fallingEdgeTimesUs) - 2
                )
            )
        elif len(self.fallingEdgeTimesUs) == 41:
            print("Warning: missed one edge - usually is the first; verify checksum")
            self.validatedPayloadAvailable = True
        elif len(self.fallingEdgeTimesUs) > 42:
            raise AM2302InsufficientDataRecieved(
                "Received {} of expected 40 bits from sensor, try again.".format(
                    len(self.fallingEdgeTimesUs) - 2
                )
            )
        else:
            self.validatedPayloadAvailable = True

    def convertEdgeTimesIntoBytes(self):
        pulseDurationsUs = [
            t - s for s, t in zip(self.fallingEdgeTimesUs, self.fallingEdgeTimesUs[1:])
        ]
        # each pulse has a 50us low, followed by high of ~25us for 0, 75us for 1
        bits = ["1" if tDeltaUs > 100 else "0" for tDeltaUs in pulseDurationsUs]

        # the first pulse is the start signal from sensor - sometimes it is missed
        if len(bits) == 41:
            bits.pop(0)

        # assert that we have 40 bits, otherwise something has gone wrong
        try:
            assert len(bits) == 40
        except AssertionError:
            raise Exception(
                "Had {} bits instead of 40 while decoding payload".format(len(bits))
            )

        return [int("".join(bits[i : i + 8]), 2) for i in range(0, len(bits), 8)]

    def convertBytesToPhysicalReadings(self, bytes):
        relativeHumidity = ((bytes[0] << 8) + bytes[1]) * AM2302_SCALE_FACTOR
        temperatureF = (
            ((bytes[2] & 0x7F) << 8) + bytes[3]
        ) * AM2302_SCALE_FACTOR * 9.0 / 5.0 + 32.0
        if bytes[2] & 0x80:
            temperatureF *= -1.0
        return relativeHumidity, temperatureF

    def setChecksum(self, bytes):
        self.checksum = bytes[4]

    def verifyChecksum(self, bytes):
        try:
            assert (sum(bytes[:4]) & 0xFF) == self.checksum
        except AssertionError:
            raise AM2302ChecksumFailed(
                "Failed checksum verification {} != {}".format(
                    bin(sum(bytes[:4]) & 0xFF), bin(self.checksum)
                )
            )

    @property
    def connectedToGpio(self):
        return self.gpio is not None and self.gpio.connected


if __name__ == "__main__":
    with AM2302Reader() as am2302:
        for count in range(10):
            try:
                print("Is connected? {}".format(am2302.connectedToGpio))
                am2302.readSensor()
                print(
                    "T: {}F, RH: {}%".format(
                        round(am2302.temperatureF, 2), round(am2302.relativeHumidity, 1)
                    )
                )
            except (AM2302InsufficientDataRecieved, AM2302ChecksumFailed) as e:
                print("Caught {} - Faulty transmission, skipping".format(str(e)))
            except Exception:
                am2302.cleanUpGpio()
                raise
