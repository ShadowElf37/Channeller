import audio, graphics, views
import json
import pafy
from tkinter import Canvas
from extras import *
from extras import safe_print as print
from urllib.parse import parse_qs, urlparse
from multiprocessing.pool import ThreadPool
import multiprocessing as mp

class Manager:
    def __init__(self, app):
        self.channels: {str: audio.Channel} = {}
        self.views: {str: views.ChannelView} = {}
        self.track_dict: {str: audio.Track} = {}
        self._slots = {}
        self.i = 0
        self.app = app
        self.total_scroll = 0
        self.app.on_resize = self.recalculate_scroll_on_resize
        self.SCROLL = 0.1
        self.timebar_hover_text = None

    @property
    def SCROLLSHIFT(self):
        return int(self.app.h*self.SCROLL)

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
        return self.track_dict.get(name)

    def stop_all(self):
        for c in self.channels.values():
            c.stop_all()

    def create_channel(self, name, color, gain, mono=False, slot=None, device_index=None):
        self.channels[name] = c = audio.Channel(name, color, gain, mono=mono, device_index=device_index)
        # slot if not None, else whatever index we're at, but if that's taken by a manual slot, just put it at the end
        self._slots[name] = slot if slot is not None else self.i if self.i not in self._slots.values() else max(self._slots.values()) + 1
        if slot is None:
            self.i += 1
        return c

    def generate_views(self):
        print(self.channels)
        for name, c in self.channels.items():
            self.views[name] = v = views.ChannelView(self.app, c, self._slots[name])
            self.app.track(v)

    def scroll(self, e):  # Allows scrollwheeling
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

    def scrub(self, e):  # Allows timeline scrubbing
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

    def hover(self, e):  # Detects location over timeline and spawns text to show you where your cursor is in the song
        x = e.x
        y = e.y
        canvas: Canvas = e.widget
        v = None
        for view in self.views.values():
            view.channel_view.canvas.delete(self.timebar_hover_text)  # now it won't get stuck when the window is calculating stuff
            if view.channel_view.canvas == e.widget:
                v: views.ChannelView = view
                break

        if v is None:
            return

        scrubber_box = v.timebar.coords
        if graphics.in_box(x, y, *scrubber_box):
            pct = (x - scrubber_box[0]) / (scrubber_box[2] - scrubber_box[0])
            self.timebar_hover_text = canvas.create_text(x, scrubber_box[1]-self.app.h/100*2, text=views.hms(pct* v.current.length), fill='#660', font="LucidaConsole %d" % (6*self.app.h/self.app.H))

    def load_channels(self, data):
        for channel in data:
            self.create_channel(**channel)

    def load_tracks(self, data, loading_notifier=NonceVar()):
        # loading_notifier is a StringVar, usually, for a loading screen, because loading tracks fresh can take a sec; NonceVar mimics StringVar interface
        cache = Path(self.app.DIR, 'yt_cache')
        urls = json.load(open(cache + 'urls.json'))
        ntracks = 0
        tracks_per_channel = {}

        for channel in self.channels.values():
            if listing := data.get(channel.name):
                l = len(listing)
                track_list = []
                for i, track in enumerate(listing):
                    YT = track.get('url')
                    cache_fp = None
                    i += 1

                    if YT:  # YOUTUBE DOWNLOADS WORK AHAHAHAHAHA IM SO HAPPY
                        url = track['url'].replace('music.', '')
                        video_id = parse_qs(urlparse(url).query)['v'][0]

                        url_short = url  # Shortened for visual appeal in the loading screen
                        if len(url) > 41:
                            url_short = url[:19] + '...' + url[-19:]

                        loading_notifier.set(f'[{channel.name}]Resolving \n {url_short} \n ({i}/{l})')
                        self.app.root.update()
                        print('resolving url')
                        vid = None
                        if video_id in urls:  # We keep urls stored with their video titles in case we have them; cuts the 2 seconds required for pafy.new()
                            name = urls[video_id]
                        else:  # If it's not listed then that's very suspicious, probably not cached, so we resolve it ourselves
                            try:
                                vid = pafy.new(video_id)
                            except:
                                continue
                            name = vid.title
                            urls[video_id] = name

                        wave_path = Path(self.app.DIR, 'wave_cache', name+'.wav').path

                        if os.path.exists(wave_path):
                            # Now actually check if we have it cached.
                            # If you clear urls.json but still have the wav hanging around this will save you,
                            # otherwise it's a redundant check
                            track['file'] = wave_path
                            print('not downloading')

                        else:  # But if not cached, gotta download!
                            if vid is None:
                                try:
                                    vid = pafy.new(video_id)
                                except:
                                    continue

                            loading_notifier.set(f'[{channel.name}]\nDownloading "{name}" from YouTube ({i}/{l})')
                            self.app.root.update()
                            print('downloading!')
                            print(vid)
                            aud = vid.getbestaudio()  # mod this
                            print('1')
                            # download it to the yt_cache
                            cache_fp = cache + (vid.title + '.' + aud.extension)
                            aud.download(cache_fp)
                            print('DOWNLOADED:', cache_fp)
                            track['file'] = cache_fp

                        if not track.get('name'):  # Give it a name
                            track['name'] = name + ' (YT)'

                    # not a Track() arg, and videos should have been downloaded...
                    if 'url' in track:
                        del track['url']

                    # Handles general files, as well as the downloaded YouTube audio
                    name = track.get('name', track['file'])
                    loading_notifier.set(f'[{channel.name}]\nLoading {name} ({i}/{l})')
                    self.app.root.update()

                    # Generate track and queue it
                    self.track_dict[name] = t = audio.Track(**track)
                    track_list.append(t)

                    # yt_cache is EVANESCENT
                    if cache_fp:
                        os.remove(cache_fp)

                # Fix up autofollows and at_times
                loading_notifier.set(f'[{channel.name}]\nRendering autofollows...')
                self.app.root.update()

                tracks_to_remove = []
                for track in track_list:
                    for at_data in track.at_time_mods:
                        # [5.0, "print('hello')"]
                        track.at_time(*at_data)

                    for af_name in track.auto_follow_mods:
                        # "track name"
                        if not (af_track := self.track_dict.get(af_name)):
                            continue
                        track.autofollow(af_track)
                        # inherit timed commands
                        track.at_time_mods += [(t+af_track.length*1000, f) for t,f in af_track.at_time_mods]
                        tracks_to_remove.append(af_track)
                        # Remove auto'd tracks from the queue since they attach to the parent

                # REMOVE autofollowed etc.
                for track in tracks_to_remove:
                    track_list.remove(track)

                # We'll queue in a hot sec
                tracks_per_channel[channel] = track_list

        ntracks = sum(len(tracks) for tracks in tracks_per_channel.values())
        ready_barrier = mp.Barrier(ntracks + 1)
        # We need this Barrier so that main won't proceed with running Channeller until all the tracks are on standby
        for channel, tracks in tracks_per_channel.items():
            # Finally queue the fully resolved tracks
            print(f'Queueing tracks for channel "{channel.name}"')
            l = len(tracks)

            loading_notifier.set(f'[{channel.name}]\nSpawning {l} children...')
            self.app.root.update()

            # Spawning all the processes at the same time is much faster
            ThreadPool(processes=l).starmap(channel.queue, zip(tracks, [-1]*l, [ready_barrier]*l))  # passes: track, -1 (default for i=), the barrier so main knows when they're all standing by
            #for i, t in enumerate(track_list):
            #    loading_notifier.set(f'Spawning children... ({i+1}/{l})')
            #    self.app.root.update()
            #    channel.queue(t)
            print(f'Finished track queueing for channel "{channel.name}"')

        json.dump(urls, open(cache + 'urls.json', 'w'), indent=4)
        print('cached urls')
        return ready_barrier
