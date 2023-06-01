A collection of raspberry pi experiments to learn what it can do!

* am2302 - experiments in reading a DHT22/AM2302 temperature & humidity sensor

* gpio_led_and_switch - basic GPIO control to light an LED and later to sense a switch state, using both polling and interrupts.

* grpc_hello_world - extends the GPIO LED and switch setup to keep track of switch presses on a remote server, with a client on the Raspberry Pi

* grpc_forward_keypresses - a client on a laptop forwards keypresses to a server on the Raspberry Pi - this is meant to demonstrate the potential to do remote control via keyboard

* keypress - various ways to detect keypresses - this would likely be run on a laptop as opposed to the Raspberry Pi

* pca9685 - basic example of servo control from the Raspberry Pi

* stream camera - several methods to stream the Raspberry Pi's camera for remote viewing - I used the http method to drive an RC car with the Raspberry Pi mounted on top through my house while watching the stream