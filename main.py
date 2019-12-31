import audio
import json
from suppressor import IndustrialGradeWarningSuppressor
import pygame, thorpy
import graphics
from pygame.locals import *

settings = json.load(open('std.json'))

pygame.init()
W = 700
H = 400
BG = (16,16,16)
screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
pygame.display.set_caption('Channeller')
screen.fill(BG)

container = pygame.Surface((W, H))
container.fill(BG)
screen.blit(container, (0,0))

clock = pygame.time.Clock()

color = graphics.htrgb('#F00')

pygame.display.flip()
running = True
while running:
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
            break
        elif event.type == K_LEFT:
            ...
        elif event.type == K_RIGHT:
            ...
        elif event.type == VIDEORESIZE:
            old = container
            W = event.w
            H = event.h
            screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
            container = pygame.Surface((W, H))
            container.fill(BG)
            #screen.blit(old, (0,0))
            screen.blit(container, (0,0))
            del old

            # draw
            # Channel
            pygame.draw.rect(container, color, Rect(W * 0.1, 0, W * 0.75, 100))
            # Presets
            # View
            #pygame.draw.rect(container, BG, Rect(W*0.1+1, 1, W*0.75-2, 98))
            # Settings

        #UI.react(event)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()