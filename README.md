A collection of raspberry pi experiments to learn what it can do!

* __am2302__ - experiments in reading a DHT22/AM2302 temperature & humidity sensor

* __gpio_led_and_switch__ - basic GPIO control to light an LED and later to sense a switch state, using both polling and interrupts.

* __grpc_hello_world__ - extends the GPIO LED and switch setup to keep track of switch presses on a remote server, with a client on the Raspberry Pi

* __grpc_forward_keypresses__ - a client on a laptop forwards keypresses to a server on the Raspberry Pi - this is meant to demonstrate the potential to do remote control via keyboard

* __keypress__ - various ways to detect keypresses - this would likely be run on a laptop as opposed to the Raspberry Pi

* __pca9685__ - basic example of servo control from the Raspberry Pi

* __stream_camera__ - several methods to stream the Raspberry Pi's camera for remote viewing - I used the http method to drive an RC car with the Raspberry Pi mounted on top through my house while watching the stream