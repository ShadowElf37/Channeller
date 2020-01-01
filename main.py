import json, os
import graphics, audio
from suppressor import IndustrialGradeWarningSuppressor
import tkinter as tk
from tkinter import filedialog as fd

settings = json.load(open('config/std.json'))



"""
# Read Config
root = Tk()
root.title('temp')
root.withdraw()
config_file = fd.askopenfilename(initialdir=CFG, title="Select config file",
                                                 filetypes=(("config files", "*.cfg"), ("all files", "*.*")))
root.destroy()
"""

# Program
app = graphics.App(700, 300, bg='#0a0a0a')
channel_view = graphics.Canvas(app, 0.7, 0.2, 0.1, 0.0, bg='#111', border_width=1, border_color='red', xoffset=-1, yoffset=0, hoffset=-2)
presets = graphics.Div(app, 0.1, 0.2, 0.0, 0.0, bg='#111', border_width=1, border_color='red')
buttons = graphics.Div(app, 0.2, 0.2, 0.8, 0.0, bg='#111', border_width=1, border_color='red')

FG_1 = '#07F'
FG_2 = '#FC0'
FG_3 = '#2F0'
BG = '#111'

# PRESETS
compression_label = graphics.Label(app, '', y=0.01, fg=FG_1, bg=BG)
compression_label.define_pre_label('COMP ')
compression_label.write('OFF')
gain_label = graphics.Label(app, '', y=0.06, fg=FG_1, bg=BG)
gain_label.define_pre_label('GAIN ')
gain_label.write('0.0')
mono_label = graphics.Label(app, '', y=0.11, fg=FG_1, bg=BG)
mono_label.write('STEREO')

# TRACK NAME
track_name_label = graphics.Label(app, '', x=0.1, y=0.002, fontscale=1.3, fg=FG_2, bg=BG)
track_name_label.write('"From Peak to Peak" - 0')

# TIME
elapsed_label = graphics.Label(app, '', x=0.12, y=0.16, yoffset=-10, fontscale=0.9, fg=FG_2, bg=BG)
elapsed_label.write('00:01:57.6')
total_label = graphics.Label(app, '', x=0.7, y=0.16, yoffset=-10, fontscale=0.9, fg=FG_2, bg=BG)
total_label.write('00:04:37')

# NEXT PREV
prev_label = graphics.Label(app, '', x=0.13, y=0.067, fontscale=1, fg=FG_1, bg=BG)
prev_label.define_pre_label('Prev: ')
prev_label.write('None')
next_label = graphics.Label(app, '', x=0.45, y=0.067, fontscale=1, fg=FG_1, bg=BG)
next_label.define_pre_label('Next: ')
next_label.write('None')

# BAR
timebar = graphics.ProgressBar(app, channel_view, x=0.18, y=0.8, w=0.65, h=0.1, xoffset=10, yoffset=-5, fill_color='red', border_color='red')
timebar.percent = 50

# CHANNEL
channel_label = graphics.RightAlignLabel(app, '', x=0.817, y=0.005, fontscale=1.5, fg='#A0F', bg=BG)
channel_label.write('Channel 1')

# PAUSED
paused_label = graphics.Label(app, '', x=0.7, y=0.065, fontscale=1.3, fg='white', bg=BG)
paused_label.write('PAUSED')

# BUTTONS
LINE1Y = 0.03
LINE2Y = 0.13
CENTERX = 0.8875
SIZE = 0.02
pause_button = graphics.Button(app, SIZE, SIZE, CENTERX + 0.0, LINE1Y, imgpath='pause.png')
next_button = graphics.Button(app, SIZE, SIZE, CENTERX + 0.03, LINE1Y, imgpath='pause.png')
last_button = graphics.Button(app, SIZE, SIZE, CENTERX + 0.06, LINE1Y, imgpath='pause.png')
prev_button = graphics.Button(app, SIZE, SIZE, CENTERX - 0.03, LINE1Y, imgpath='pause.png')
first_button = graphics.Button(app, SIZE, SIZE, CENTERX - 0.06, LINE1Y, imgpath='pause.png')

app.track(channel_view)
app.track(presets)
app.track(buttons)
app.track(compression_label)
app.track(gain_label)
app.track(mono_label)
app.track(track_name_label)
app.track(elapsed_label)
app.track(total_label)
app.track(timebar)
app.track(next_label)
app.track(prev_label)
app.track(channel_label)
app.track(paused_label)
app.track(pause_button, next_button, last_button, prev_button, first_button)

class ChannelView:
    def __init__(self, channel: audio.Channel):
        self.channel = channel
        self.color = channel.color
        # include all above ^^^

    def draw(self):
        ...#border


# SCROLLING todo

app.run()

