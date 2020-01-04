import json
import graphics, audio, views, cues
from os.path import exists
import tkinter as tk
from tkinter import filedialog as fd

settings = json.load(open('config/settings.json'))

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
    def __init__(self, app):
        self.channels: {str: audio.Channel} = {}
        self.views: {str: views.ChannelView} = {}
        self.tracks: {str: audio.Track} = {}
        self._slots = {}
        self.i = 0
        self.app = app
        self.total_scroll = 0
        self.app.on_resize = self.recalculate_scroll_on_resize

    @property
    def SCROLLSHIFT(self):
        return self.app.h//10

    def recalculate_scroll_on_resize(self):
        # Since the scroll increment changes dynamically to 1/10 of the window height, the scroll y needs to be recalculated on window resize
        for view in self.views.values():
            view.reset_shifty()
            view.shifty(self.total_scroll * self.SCROLLSHIFT)

    def chget(self, name):
        return self.channels.get(name)
    def vget(self, name):
        return self.views.get(name)
    def tget(self, name):
        return self.tracks.get(name)

    def stop_all(self):
        for c in self.channels.values():
            c.stop_all()

    def create_channel(self, name, color, gain, mono=False, slot=None):
        self.channels[name] = c = audio.Channel(name, color, gain, mono=mono)
        self._slots[name] = slot or self.i
        if slot is None:
            self.i += 1
        return c

    def generate_views(self):
        print(self.channels)
        for name, c in self.channels.items():
            self.views[name] = v = views.ChannelView(self.app, c, self._slots[name])
            self.app.track(v)

    def scroll(self, e):
        if e.num == 4 or e.delta == 120:
            d = 1  # Up
        elif e.num == 5 or e.delta == -120:
            d = -1  # Down
        else:
            return

        # max in SCROLL SHIFTS, i.e. tenths
        max_up = 8
        max_down = -max(self._slots.values())*2
        if (self.total_scroll == max_up and d == 1) or (self.total_scroll == max_down and d == -1):
            return

        self.total_scroll += d
        for view in self.views.values():
            view.shifty(d*self.SCROLLSHIFT)

    def scrub(self, e):
        x = e.x
        y = e.y
        v = None
        c = None
        for view in self.views.values():
            if view.channel_view.canvas == e.widget:
                v = view
                c: audio.Channel = v.channel
                break
        if v is None:
            return

        scrubber_box = v.timebar.coords
        if graphics.in_box(x, y, *scrubber_box):
            x1 = scrubber_box[0]
            x2 = scrubber_box[2]
            frac = (x - x1) / (x2 - x1)
            time = c.current.length * frac
            if c.current.paused:
                c.current.stop()
                c.current.start_at(time)
                c.current.pause()
                c.current.play()
            elif c.current.playing:
                c.current.stop()
                c.current.start_at(time)
                c.current.play()
            else:
                c.current.stop()
                c.current.start_at(time)

    def load_channels(self, file):
        for channel in json.load(open(file)):
            self.create_channel(**channel)

    def load_tracks(self, file):
        data = json.load(open(file))
        for channel in self.channels.values():
            if listing := data.get(channel.name):
                for track in listing:
                    self.tracks[track.get('name', track['file'])] = t = audio.Track(**track)
                    channel.queue(t)


# Program
app = graphics.App(700, 300, bg='#080808')

app.bind('F5', app.toggle_fullscreen)
app.bind('Alt_L', app.alt_tab)
app.bind('Win_L', app.alt_tab)

m = Manager(app)
m.load_channels(app.CFG + 'channels.json')
m.load_tracks(app.CFG + 'tracks.json')

m.generate_views()

cm = cues.CueManager(m)
cv = views.CueViewer(app, cm)
cm.locals = {
    'cues': cm,
    'manager': m,
    'chan': m.chget,
    'channel': m.chget,
    'view': m.vget,
    'stop_all': m.stop_all
}
cm.load_file(app.CFG + 'cues.cfg')

# Windows
app.bind('MouseWheel', m.scroll)
# Linux
app.bind("Button-4", m.scroll)
app.bind("Button-5", m.scroll)

app.bind_all('Button-1', m.scrub)

# SUBPROC FOR EACH CHANNEL, THREAD SONGS INSIDE OR SOMETHING todo
# TRACK CFG
# MARKERS

# REMOVE COMP AND GAIN INDICATORS

app.run()

