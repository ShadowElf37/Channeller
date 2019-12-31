import tkinter as tk
from audio import Channel

def in_box(x, y, x1, y1, x2, y2):
    if x2 > x > x1 and y2 > y > y1:
        return True
    return False

def htrgb(hex):
    hex = hex.strip('#')
    l = len(hex)
    scalar = 6//l
    if scalar == 0:
        raise ArithmeticError('Can\'t solve > 24-bit RGB values')
    elif scalar == 6:
        return (int(hex*2, 16),)*3
    return int(hex[:l//3]*scalar, 16), int(hex[l//3:2*l//3]*scalar, 16), int(hex[2*l//3:]*scalar, 16)

class ChannelView:
    def __init__(self, channel: Channel):
        self.channel = channel
        self.color = channel.color

    def draw(self):
        ...#border

class App:
    def __init__(self, w):