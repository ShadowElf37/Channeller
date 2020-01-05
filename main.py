import json
import graphics, audio, views, cues, manager
from os.path import exists, join
import tkinter as tk
from tkinter import filedialog as fd


# Program
app = graphics.App(700, 300, bg='#080808')
app.resize(250, 50)

app.bind('F5', app.toggle_fullscreen)
app.bind('Alt_L', app.alt_tab)
app.bind('Win_L', app.alt_tab)

m = manager.Manager(app)

loading_text = tk.StringVar()
loading_label = tk.Label(app.root, textvar=loading_text, fg='white', bg='#080808')
loading_label.pack()

m.load_channels(app.CFG + 'channels.json')
m.load_tracks(app.CFG + 'tracks.json', loading_text)

cm = cues.CueManager(m)
cv = views.CueView(app, cm)

cm.locals = {
    'cues': cm,
    'manager': m,
    'chan': m.chget,
    'channel': m.chget,
    'view': m.vget,
    'stop_all': m.stop_all
}
cm.load_file(app.CFG + 'cues.cfg')

app.bind('MouseWheel', m.scroll)  # windows scroll
app.bind("Button-4", m.scroll)  # linux scroll 1
app.bind("Button-5", m.scroll)  # linux scroll 2

app.bind('Button-1', m.scrub)  # timeline scrubbing

app.bind('Motion', m.hover)  # timeline hovering

# SETTINGS
settings = json.load(open('config/settings.json'))

m.SCROLL = settings['scroll_fraction']
views.CueView.CUE_OFFSET = settings['cue_number_start']
views.ChannelView.TRACK_OFFSET = audio.Channel.TRACK_OFFSET = settings['track_number_start']

import keymap as km
app.bind(km.map[settings['keybind_last_cue']], lambda e: cm.back())
app.bind(km.map[settings['keybind_next_cue']], lambda e: cm.next())
app.bind(km.map[settings['keybind_stop_all']], lambda e: m.stop_all())
app.bind(km.map[settings['keybind_cue_go_next']], lambda e: cm.go())

loading_label.destroy()
del loading_label
del loading_text

app.resize(700, 300)
m.generate_views()
app.run()

# SUBPROC FOR EACH CHANNEL, THREAD SONGS INSIDE OR SOMETHING todo

# EASIER WAY TO ADD TRACKS
# TRACK/CHANNEL CFG WRITE TOOL todo

# CANVAS TEXT FOR PREV AND NEXT

# MARKERS
# REMOVE COMP AND GAIN INDICATORS
