#!/usr/bin/env python

from pynput import keyboard

class KeyboardMonitor():
    keys_pressed = set()


    def on_press(self, key):
        self.keys_pressed.add(key)
        print(self.keys_pressed)


    def on_release(self, key):
        self.keys_pressed.remove(key)
        if(len(self.keys_pressed) == 0):
            print("{ }")
        else:
            print(self.keys_pressed)


if __name__ == '__main__':
    # Collect events until released
    myKeyboard = KeyboardMonitor()
    with keyboard.Listener(
            on_press=myKeyboard.on_press,
            on_release=myKeyboard.on_release) as listener:
        listener.join()

