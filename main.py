"""
main.py
All the initialization code is in here, albeit in abstract function-call form.
All of the audio action happens in audio.Track._play()

DO NOT define any classes or functions in this file
If you need to define a class for main.py only, do it in extras.py and import it
Attempting to define useful stuff here will result in fatal bugs when run as an executable
"""

# EASIER WAY TO ADD TRACKS
# TRACK/CHANNEL CFG WRITE TOOL

# CANVAS TEXT FOR PREV AND NEXT

import sys, os
import json
import datetime as dt
import tkinter as tk
from tkinter import filedialog as fd
import ntpath
from sounddevice import query_devices
from threading import Thread
from extras import Path, ProxyManager, safe_print as print
import multiprocessing as mp
import graphics, audio, views, cues, manager, osc
import builtins


# mp tries to run this so we're not gonna let it do that
if __name__ == "__main__":
    mp.freeze_support()

    newlogpath = os.path.join(os.getcwd(), 'logs',
                              dt.datetime.now().strftime('%Y-%m-%d %H.%M.%S.log').replace('/', '-').replace(':', ';'))

    # This mp-manager's sole purpose is to proxy the log file
    ProxyManager.register('open', open)

    with ProxyManager() as mp_proxy_manager:
        log = mp_proxy_manager.open(newlogpath, 'w+', encoding='utf-8')
        sys.stdout = sys.stderr = audio.Track.STDOUT = log
        # with statement doesn't work with proxy open(); manual try-finally
        try:
            #====================
            # FILE SELECTION
            #====================
            print('PID', os.getpid())

            # FILE SELECTION
            cfolder = Path(os.getcwd(), 'config')
            conf = open(cfolder + 'stored.json', 'r+')
            data = json.load(conf)

            # Write down available audio devices real quick
            with open(cfolder + 'audio_devices.txt', 'w') as f:
                f.write(str(query_devices()))
            print('Fetched audio devices.')

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

            start = tk.Button(root, text='Start', command=r)
            start.grid(row=5, column=2)
            root.bind('<Return>', r)

            print('Waiting for user...')
            try:
                root.mainloop()
            except tk.TclError:
                pass

            if not ready:
                print('User quit?')
                sys.exit()
            print('Ready.')

            print('Storing config locations...')
            json.dump(data, open(cfolder + 'stored.json', 'w'), indent=4)

            fchan = data['last_channel_file'] or cfolder + 'channels.json'
            ftrack = data['last_track_file'] or cfolder + 'tracks.json'
            fcue = data['last_cue_file'] or cfolder + 'cues.cfg'

            # This takes timed commands from the child processes and runs them up here where the manager, etc. can be accessed safely
            EXECUTOR_QUEUE = mp.Queue()
            def execute_commands_loop():
                while True:
                    string = EXECUTOR_QUEUE.get()  # blocks
                    print('Command received:', '[ '+string+' ]')
                    try:
                        exec(string, {**builtins.__dict__, **userfunctions.__dict__}, cm.locals)
                    except Exception as e:
                        print('Timed command failed:', e)


            #===============
            # Begin Program
            #===============

            audio.Track.EXECUTOR_QUEUE = EXECUTOR_QUEUE

            app = graphics.App(700, 300, bg='#080808', fps=30)
            app.resize(275, 60)

            app.bind('F5', app.toggle_fullscreen)
            app.bind('Alt_L', app.alt_tab)
            app.bind('Win_L', app.alt_tab)

            m = manager.Manager(app)

            loading_text = tk.StringVar()
            loading_label = tk.Label(app.root, textvar=loading_text, fg='white', bg='#080808')
            loading_label.pack()

            print('Channeller launched.')
            cdat = json.load(open(fchan))
            tdat = json.load(open(ftrack))
            print('Loading channels...')
            m.load_channels(cdat)

            cm = cues.CueManager(m)
            cv = views.CueView(app, cm)

            loading_text.set('Loading settings...')
            print('Loading cues...')
            cm.load_file(fcue)
            print('Channels and cues loaded.')

            app.bind('MouseWheel', m.scroll)  # windows scroll
            app.bind("Button-4", m.scroll)  # linux scroll 1
            app.bind("Button-5", m.scroll)  # linux scroll 2

            app.bind('Button-1', m.scrub)  # timeline scrubbing

            app.bind('Motion', m.hover)  # timeline hovering

            # SETTINGS
            settings = json.load(open(cfolder + 'settings.json'))

            views.ChannelView.GAIN_MAX = settings['gain_ceiling']
            views.ChannelView.GAIN_MIN = settings['gain_floor']
            views.ChannelView.GAIN_STEP_INC = settings['gain_step']
            for cv in m.views.values():
                cv.apply_gain_minmax()

            m.SCROLL = settings['scroll_fraction']
            views.CueView.CUE_OFFSET = cues.CueManager.CUE_OFFSET = settings['cue_number_start']
            views.ChannelView.TRACK_OFFSET = audio.Channel.TRACK_OFFSET = settings['track_number_start']
            cues.CueManager.SKIP_EMPTY_CUES = settings['skip_empty_cues']

            km = json.load(open(cfolder + 'keymap.json'))
            app.bind(km[settings['keybind_last_cue']], lambda e: cm.back())
            app.bind(km[settings['keybind_next_cue']], lambda e: cm.next())
            app.bind(km[settings['keybind_stop_all']], lambda e: m.stop_all())
            app.bind(km[settings['keybind_cue_go_next']], lambda e: cm.go())

            audio.Track.CACHE_DOWNLOADED = settings['cache_downloaded_tracks']
            audio.Track.CACHE_CONVERTED = settings['cache_converted_tracks']

            audio.Track.CHUNK = settings['chunk_size']

            # OSC
            osc_server = osc.Server(host=settings['osc_host_ip'], port=settings['osc_host_port'])
            osc_server.init()
            # ADD CLIENTS TO REGISTRY
            osc_devices = json.load(open(cfolder + 'osc.json'))
            for name, addr in osc_devices.items():
                osc_server.add_client(name, *addr)

            # exec locals
            cm.locals = {
                'cues': cm,
                'manager': m,
                'app': app,
                'chan': m.chget,
                'channel': m.chget,
                'view': m.vget,
                'stop_all': m.stop_all,
                'osc': osc_server,
                'OSC': osc_server
            }
            import channeller
            channeller._import(cm.locals)
            print('Loading userfunctions...')
            loading_text.set('Loading external functions...')
            import userfunctions
            print('Interfaced with userfunctions.py!')

            EXECUTOR_THREAD = Thread(target=execute_commands_loop, daemon=True)
            EXECUTOR_THREAD.start()

            print('Loading tracks...')
            all_tracks_ready_barrier = m.load_tracks(tdat, loading_text)  # returns our synchronization method
            print('Tracks loaded.')

            loading_text.set('Wrapping up...')
            app.root.update()

            loading_label.destroy()
            del loading_label
            del loading_text

            app.resize(700, 340)
            print('Creating views...')
            m.generate_views()
            print('Generation complete. Checking on the children...')
            all_tracks_ready_barrier.wait()
            print('All children standing by. Log should be flushed.')
            print('Channeller initialized successfully.\n' + ('='*50) + '\n')
            log.flush()
            app.run()

        except Exception as e:
            from traceback import format_exc
            print(format_exc())
        finally:
            log.close()
