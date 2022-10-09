import pygame

pygame.init()
win = pygame.display.set_mode((100, 100))

def getKeyStates(keyList):
    for eve in pygame.event.get():
        pass
    keyInput = pygame.key.get_pressed()
    keyStateDict = {}
    for key in keyList:
        keyStateDict[key] = \
                keyInput[getattr(pygame, 'K_{}'.format(key))]
    # if keyInput[pygame.K_a]:
    #     print('key a was pressed')
    pygame.display.update()
    return keyStateDict

while True:
    keyStateDict = getKeyStates(['w', 'a', 's', 'd'])
    if any(keyStateDict.values()):
        print(keyStateDict)
