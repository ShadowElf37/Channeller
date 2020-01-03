import json
import graphics, audio, views
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


class Manager:
    SCROLLSHIFT = 50
    def __init__(self, app):
        self.channels: {str:audio.Channel} = {}
        self.views: {str:views.ChannelView} = {}
        self._slots = {}
        self.i = 0
        self.app = app

    def chget(self, name):
        return self.channels.get(name)
    def vget(self, name):
        return self.views.get(name)

    def create_channel(self, name, color, gain, mono=False, slot=None):
        self.channels[name] = c = audio.Channel(name, color, gain, mono=mono)
        self._slots[name] = slot or self.i
        if slot is None:
            self.i += 1
        return c

    def generate_views(self):
        for name, c in self.channels.items():
            self.views[name] = v = views.ChannelView(self.app, c, self._slots[name])
            self.app.track(v)

    def scroll(self, e=None):
        if e.num == 4 or e.delta == 120:
            d = 1
        elif e.num == 5 or e.delta == -120:
            d = -1
        else:
            return

        for view in self.views.values():
            view.shifty(d*self.SCROLLSHIFT)

    def load_channels(self, file):
        # The file should be formatted as line-by-line Channel instantiations
        with open(file, 'r') as f:
            self.channels = {c.name: c for c in [eval(line) for line in f.readlines() if line[0] != '#']}


# Program

app = graphics.App(700, 300, bg='#0a0a0a')
m = Manager(app)
m.create_channel('SFX 1', '#F00', 1.0)
m.create_channel('SFX 2', '#F00', 1.0)
m.create_channel('Soundtrack', '#F60', 1.0, slot=3)

t = audio.Track('From Peak to Peak.wav')
m.chget('SFX 1').queue(t)
m.chget('SFX 2').queue(t)
m.chget('Soundtrack').queue(t)

m.generate_views()

# SCROLLING todo
# SUBPROC FOR EACH CHANNEL, THREAD SONGS INSIDE OR SOMETHING todo
# GLOBAL CUES todo
# BUG: STOP IS BROKEN WHEN PAUSED todo
# CFG todo

# COMP NEEDS TO BE REALTIME IT'S TOO EXPENSIVE todo
# INCREASE CHUNK SIZE TO 500 ms SO COMP WORKS CORRECTLY

app.run()

