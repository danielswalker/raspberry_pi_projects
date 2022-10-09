import grpc
from send_keypresses_pb2 import KeysPressed, Empty
from send_keypresses_pb2_grpc import KeySenderStub
from pynput import keyboard

class KeyboardMonitor():
    keys_pressed = set()


    def on_press(self, key):
        self.keys_pressed.add(key)
        # print(self.keys_pressed)
        keys_pressed = KeysPressed(keys=[str(key) for key in self.keys_pressed])
        response = client.HandleKeyEvent(keys_pressed)


    def on_release(self, key):
        self.keys_pressed.remove(key)
        # keys_pressed = KeysPressed(keys=list(self.keys_pressed))
        keys_pressed = KeysPressed(keys=[str(key) for key in self.keys_pressed])
        response = client.HandleKeyEvent(keys_pressed)
        # if(len(self.keys_pressed) == 0):
        #     print("{ }")
        # else:
        #     print(self.keys_pressed)


# channel = grpc.insecure_channel("raspberrypi.local:50051")
channel = grpc.insecure_channel("192.168.1.218:50051")
client = KeySenderStub(channel)
myKeyboard = KeyboardMonitor()
with keyboard.Listener(
        on_press=myKeyboard.on_press,
        on_release=myKeyboard.on_release) as listener:
    listener.join()

while True:
    time.sleep(1)
