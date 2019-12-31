import audio
import json
from suppressor import IndustrialGradeWarningSuppressor
import pygame, thorpy as thor

settings = json.load(open('std.json'))

pygame.init()
screen = pygame.display.set_mode((700, 400))

running = True
while running:
    ...

pygame.quit()