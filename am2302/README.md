This code explores different ways to read the DHT22 / AM2303 temperature and humidity sensor.

RPi.GPIO was found to work well if we polled the sensor as fast as possible to resolve the O(10)-O(100) microsecond pulses. However, trying to set up interrupts and callbacks failed to consistently register the pulses.

pigpio relies on a daemon written in C that uses MMIO to control the GPIO - it has much quicker response than trying to execute callbacks in python. I am able to set up interrupts which are handled in the daemon and communicated to the python program.

When setting the GPIO pin low, I saw a fast transient with period 20 ns that overshoots the ground voltage and rings for a few oscillations. I added a 220 pf capacitor to damp this and remove the overshoot.

![Board Layout](https://github.com/danielswalker/raspberry_pi_projects/blob/master/am2302/IMG_0766.jpg?raw=true)

![Oscilloscope Waveform](https://github.com/danielswalker/raspberry_pi_projects/blob/master/am2302/IMG_0763.jpg?raw=true):w
