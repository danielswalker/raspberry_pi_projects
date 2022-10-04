Extends the led lighting experiment by moving event handlers to a remote server.  This is a way to learn about gRPC basics.

A gRPC server is run on a host machine (currently with host name "Walker").  It implements a MonitorButtonService class with a unary HandleButtonEvent method.  This method counts button presses with some debouncing logic.

A gRPC client is run on the raspberry pi.  Whenever a transition is observed on pin 26, it checks the state of that pin, and sends the pin state and current time to the server.  It recieves back the total count of debounced button presses since the server was started.
