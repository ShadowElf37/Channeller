import json, os
import graphics, audio
from suppressor import IndustrialGradeWarningSuppressor
import tkinter as tk
from tkinter import filedialog as fd
import datetime as dt

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

def hms(sec):
    sec = int(sec)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f'{h:02d}:{m:02d}:{s:02d}'
def hmsm(sec, decimals=1):
    ms = round(int(sec) - sec, decimals)
    return hms(sec) + '.' + str(ms)


# Program

class ChannelView:
    FG_1 = '#07F'
    FG_2 = '#FC0'
    FG_3 = '#2F0'
    BG = '#111'
    BUTTONBG = '#aaa'

    @property
    def stereo(self):
        return 'STEREO' if self.channel._channel_count > 1 else 'MONO'
    @property
    def gain(self):
        return str(self.channel.gain)
    @property
    def compression(self):
        return 'ON' if self.channel.compression else 'OFF'
    @property
    def current(self):
        return self.channel.current
    @property
    def elapsed(self):
        return hmsm(self.current.play_time)
    @property
    def end(self):
        return hms(self.current.length)

    @property
    def paused(self):
        return 'PAUSED' if self.channel.current.paused else ''


    @property
    def next(self):
        if t := self.channel.get_next():
            return t.name
        return 'None'
    @property
    def prev(self):
        if t := self.channel.get_prev():
            return t.name
        return 'None'

    def __init__(self, app, channel: audio.Channel, y_off=0):
        self.app = app
        self.channel = channel
        self.channel.update()
        self.color = channel.color
        y_off *= 0.21
        self.y = y_off
        
        # DIVS
        self.channel_view = graphics.Canvas(app, 0.7, 0.2, 0.1, 0.0+y_off, bg=self.BG, border_width=1, border_color=self.color,
                                       xoffset=-1, yoffset=0+self.y, hoffset=-2)
        self.presets = graphics.Div(app, 0.1, 0.2, 0.0, 0.0+y_off, bg=self.BG, border_width=1, border_color=self.color)
        self.buttons = graphics.Div(app, 0.2, 0.2, 0.8, 0.0+y_off, bg=self.BG, border_width=1, border_color=self.color)

        # PRESETS
        self.compression_label = graphics.Label(app, '', y=0.01+y_off, fg=self.FG_1, bg=self.BG)
        self.compression_label.define_pre_label('COMP ')
        self.gain_label = graphics.Label(app, '', y=0.06+y_off, fg=self.FG_1, bg=self.BG)
        self.gain_label.define_pre_label('GAIN ')
        self.mono_label = graphics.Label(app, '', y=0.11+y_off, fg=self.FG_1, bg=self.BG)

        # TRACK NAME
        self.track_name_label = graphics.Label(app, '', x=0.1, y=0.002+y_off, fontscale=1.3, fg=self.FG_2, bg=self.BG)
        self.track_name_label.write('"%s" - %s' % (self.current.name, self.channel.index))

        # TIME
        self.elapsed_label = graphics.Label(app, '', x=0.12, y=0.16+y_off, yoffset=-10, fontscale=0.9, fg=self.FG_2, bg=self.BG)
        self.total_label = graphics.Label(app, '', x=0.7, y=0.16+y_off, yoffset=-10, fontscale=0.9, fg=self.FG_2, bg=self.BG)

        # NEXT PREV
        self.prev_label = graphics.Label(app, '', x=0.13, y=0.067+y_off, fontscale=1, fg=self.FG_1, bg=self.BG)
        self.prev_label.define_pre_label('Prev: ')
        self.next_label = graphics.Label(app, '', x=0.45, y=0.067+y_off, fontscale=1, fg=self.FG_1, bg=self.BG)
        self.next_label.define_pre_label('Next: ')


        # BAR
        self.timebar = graphics.ProgressBar(app, self.channel_view, x=0.18, y=0.8+y_off, w=0.65, h=0.1, xoffset=10, yoffset=-5,
                                       fill_color=self.color, border_color=self.color)

        # CHANNEL
        self.channel_label = graphics.RightAlignLabel(app, self.channel.name, x=0.817, y=0.005+y_off, fontscale=1.5, fg=self.color, bg=self.BG)

        # PAUSED
        self.paused_label = graphics.Label(app, '', x=0.7, y=0.065+y_off, fontscale=1.3, fg='white', bg=self.BG)

        # BUTTONS
        LINE1Y = 0.03
        LINE2Y = 0.11
        CENTERX = 0.8875
        SIZE = 0.02

        self.pause_button = graphics.Button(app, SIZE, SIZE, CENTERX + 0.0, LINE1Y+y_off, img_name=app.IMG + 'pause.png',
                                       img_scale=0.9, background=self.BUTTONBG)
        self.next_button = graphics.Button(app, SIZE, SIZE, CENTERX + 0.03, LINE1Y+y_off, img_name=app.IMG + 'next.png',
                                      background=self.BUTTONBG)
        self.last_button = graphics.Button(app, SIZE, SIZE, CENTERX + 0.06, LINE1Y+y_off, img_name=app.IMG + 'last.png',
                                      background=self.BUTTONBG)
        self.prev_button = graphics.Button(app, SIZE, SIZE, CENTERX - 0.03, LINE1Y+y_off, img_name=app.IMG + 'prev.png',
                                      background=self.BUTTONBG)
        self.first_button = graphics.Button(app, SIZE, SIZE, CENTERX - 0.06, LINE1Y+y_off, img_name=app.IMG + 'first.png',
                                       background=self.BUTTONBG)

        self.stop_button = graphics.Button(app, SIZE, SIZE, CENTERX, LINE2Y+y_off, img_name=app.IMG + 'stop.png', img_scale=0.8,
                                      background=self.BUTTONBG)

        self.ch_gain_inc = graphics.Incrementor(app, min=-99.9, max=10, step=0.5, x=0.92, y=0.111+y_off, w=5, yoffset=0,
                                           bg='#000', fg=self.color, buttonbg=self.BUTTONBG, fontscale=1)
        self.tr_gain_inc = graphics.Incrementor(app, min=-99.9, max=10, step=0.5, x=0.8125, y=0.111+y_off, w=5, yoffset=0,
                                           bg='#000', fg=self.color, buttonbg=self.BUTTONBG, fontscale=1)

        self.ch_gain_label = graphics.Label(app, 'CH GAIN', x=0.9275, y=0.15+y_off, fontscale=0.6, fg=self.FG_1, bg=self.BG)
        self.tr_gain_label = graphics.Label(app, 'TR GAIN', x=0.82, y=0.15+y_off, fontscale=0.6, fg=self.FG_1, bg=self.BG)

        app.track(self.channel_view, self.presets, self.buttons)
        app.track(self.compression_label, self.gain_label, self.mono_label)
        app.track(self.track_name_label, self.elapsed_label, self.total_label)
        app.track(self.next_label, self.prev_label, self.channel_label, self.paused_label)
        app.track(self.timebar)
        app.track(self.pause_button, self.next_button, self.last_button, self.prev_button, self.first_button, self.stop_button)
        app.track(self.ch_gain_inc, self.tr_gain_inc)
        app.track(self.ch_gain_label, self.tr_gain_label)

        self.update_labels()
        self.update_times()
        self.ch_gain_inc.set(str(self.channel.gain))
        self.tr_gain_inc.set(str(self.channel.current.gain))

    def update_labels(self):
        self.compression_label.write(self.compression)
        self.gain_label.write(self.gain)
        self.mono_label.write(self.stereo)

        self.prev_label.write(self.prev)
        self.next_label.write(self.next)

        self.paused_label.write(self.paused)

    def update_times(self):
        self.timebar.percent = 0
        if self.current.length:
            self.timebar.percent = self.channel.current.play_time / len(self.channel.current.track)
        self.elapsed_label.write(self.elapsed)
        self.total_label.write(self.end)

    def draw(self):
        ...#border


app = graphics.App(700, 300, bg='#0a0a0a')
chan1 = audio.Channel('Channel 1', '#00F', 1.0)
chan2 = audio.Channel('Channel 2', '#F00', 1.0)
chan3 = audio.Channel('Channel 3', '#FF0', 1.0)
t = audio.Track('From Peak to Peak.wav')
chan1.queue(t)
chan2.queue(t)
chan3.queue(t)
views =[
    ChannelView(app, chan1, 0),
    ChannelView(app, chan2, 1),
    ChannelView(app, chan3, 2),
]



# SCROLLING todo

app.run()

