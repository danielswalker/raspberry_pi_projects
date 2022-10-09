import keyboard

while True:
    if keyboard.read_key() == "p":
        print("You pressed p")
        break
# keyboard.on_press_key("p", lambda _:print("You pressed p"))

# while True:
#     pass
