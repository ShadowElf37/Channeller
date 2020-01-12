import json
import graphics, audio, views, cues, manager
import tkinter as tk
from tkinter import filedialog as fd
import sys
import datetime as dt
import os
from extras import Path
import ntpath

# FILE SELECTION
cfolder = Path(os.getcwd(), 'config')
conf = open(cfolder + 'stored.json', 'r+')
data = json.load(conf)

lfchan = data['last_channel_file'] or cfolder + 'channels.json'
lftrack = data['last_track_file'] or cfolder + 'tracks.json'
lfcue = data['last_cue_file'] or cfolder + 'cues.cfg'

def load_cfg(key, sv=None):
    global data
    path = fd.askopenfilename(initialdir='.', filetypes=(
                                        ("Config/JSON files", "*.json;*.cfg"),
                                        ("All files", "*.*")
                                            ))
    if sv:
        sv.set(ntpath.basename(path))
    data[key] = path

root = tk.Tk()
root.title('Load Files')

channel_label = tk.Label(root, text='Channel file:', anchor='e')
ch_sv = tk.StringVar(value=ntpath.basename(lfchan))
channel_selector = tk.Button(root, textvar=ch_sv, command=lambda: load_cfg('last_channel_file', ch_sv), anchor='w')

track_label = tk.Label(root, text='Track file:', anchor='e')
t_sv = tk.StringVar(value=ntpath.basename(lftrack))
track_selector = tk.Button(root, textvar=t_sv, command=lambda: load_cfg('last_track_file', t_sv), anchor='w')

cue_label = tk.Label(root, text='Cue file:', anchor='e')
c_sv = tk.StringVar(value=ntpath.basename(lfcue))
cue_selector = tk.Button(root, textvar=c_sv, command=lambda: load_cfg('last_cue_file', c_sv), anchor='w')

channel_label.grid(row=1, column=1)
channel_selector.grid(row=1, column=3)
track_label.grid(row=2, column=1)
track_selector.grid(row=2, column=3)
cue_label.grid(row=3, column=1)
cue_selector.grid(row=3, column=3)

ready = False
def r(*args):
    global ready
    ready = True
    root.destroy()

start = tk.Button(root, text='Enter', command=r)
start.grid(row=5, column=2)
root.bind('<Return>', r)

try:
    root.mainloop()
except tk.TclError:
    pass

if not ready:
    exit()

print('storing config locations')
json.dump(data, open(cfolder + 'stored.json', 'w'), indent=4)
print('done')

fchan = data['last_channel_file'] or cfolder + 'channels.json'
ftrack = data['last_track_file'] or cfolder + 'tracks.json'
fcue = data['last_cue_file'] or cfolder + 'cues.cfg'

# Program
newlogpath = os.path.join(os.getcwd(), 'logs', dt.datetime.now().strftime('%Y-%m-%d %H.%M.%S %p.log').replace('/', '-').replace(':', ';'))

with open(newlogpath, 'w+', encoding='utf-8') as log:
    sys.stdout = sys.stderr = log

    app = graphics.App(700, 300, bg='#080808')
    app.resize(250, 50)

    app.bind('F5', app.toggle_fullscreen)
    app.bind('Alt_L', app.alt_tab)
    app.bind('Win_L', app.alt_tab)

    m = manager.Manager(app)

    loading_text = tk.StringVar()
    loading_label = tk.Label(app.root, textvar=loading_text, fg='white', bg='#080808')
    loading_label.pack()

    print('we go')
    cdat = json.load(open(fchan))
    tdat = json.load(open(ftrack))
    print('loading channels')
    m.load_channels(cdat)
    print('loading tracks')
    m.load_tracks(tdat, loading_text)

    cm = cues.CueManager(m)
    cv = views.CueView(app, cm)

    print('loading cues')
    cm.locals = audio.Track.LOCALS = {
        'cues': cm,
        'manager': m,
        'app': app,
        'chan': m.chget,
        'channel': m.chget,
        'view': m.vget,
        'stop_all': m.stop_all
    }
    cm.load_file(fcue)
    print('loaded')

    app.bind('MouseWheel', m.scroll)  # windows scroll
    app.bind("Button-4", m.scroll)  # linux scroll 1
    app.bind("Button-5", m.scroll)  # linux scroll 2

    app.bind('Button-1', m.scrub)  # timeline scrubbing

    app.bind('Motion', m.hover)  # timeline hovering

    # SETTINGS
    settings = json.load(open('config/settings.json'))

    m.SCROLL = settings['scroll_fraction']
    views.CueView.CUE_OFFSET = cues.CueManager.CUE_OFFSET = settings['cue_number_start']
    views.ChannelView.TRACK_OFFSET = audio.Channel.TRACK_OFFSET = settings['track_number_start']

    km = json.load(open(app.CFG + 'keymap.json'))
    app.bind(km[settings['keybind_last_cue']], lambda e: cm.back())
    app.bind(km[settings['keybind_next_cue']], lambda e: cm.next())
    app.bind(km[settings['keybind_stop_all']], lambda e: m.stop_all())
    app.bind(km[settings['keybind_cue_go_next']], lambda e: cm.go())

    loading_label.destroy()
    del loading_label
    del loading_text

    app.resize(700, 340)
    print('creating views')
    m.generate_views()
    print('Running...')
    app.run()


# CUE, CHANNEL, TRACK GUIDES

# EASIER WAY TO ADD TRACKS
# TRACK/CHANNEL CFG WRITE TOOL todo

# CANVAS TEXT FOR PREV AND NEXT todo
