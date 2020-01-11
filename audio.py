import pyaudio
import os.path, os
import ntpath
from threading import Thread, Lock
from time import sleep
from pydub import AudioSegment
from pydub.utils import make_chunks
from pydub.effects import compress_dynamic_range
import builtins

PA = pyaudio.PyAudio()
CHUNK = 5  # 50ms chunks for processing – if it's too low then the overhead gets larger than the chunks are!
DIR = os.getcwd()

# Missing pydub feature
def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
    '''
    sound is a pydub.AudioSegment
    silence_threshold in dB
    chunk_size in ms
    iterate over chunks until you find the first one with sound
    '''
    trim_ms = 0 # ms
    assert chunk_size > 0 # to avoid infinite loop
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms



class Channel:
    TRACK_OFFSET = 0

    def __init__(self, name='Unnamed Channel', color='#FFF', gain=0.0, mono=False):
        self.gain = gain
        self.current: Track = Track(None)
        self._queue: [Track] = []
        self.index = 0
        self._channel_count = 1 if mono else 2
        self.compression = False
        self.comp_args = dict(threshold=-20.0, ratio=4.0, attack=5.0, release=50.0)
        self.color = color
        self.name = name
        self.fading = False

    # Compression applies to ALL tracks queued in a channel - if you want only certain tracks compressed, a separate channel should be created for them
    def with_compression(self, threshold=-20.0, ratio=4.0, attack=5.0, release=50.0):
        """ --FROM PYDUB SRC--
            Keyword Arguments:

                threshold - default: -20.0
                    Threshold in dBFS. default of -20.0 means -20dB relative to the
                    maximum possible volume. 0dBFS is the maximum possible value so
                    all values for this argument sould be negative.
                ratio - default: 4.0
                    Compression ratio. Audio louder than the threshold will be
                    reduced to 1/ratio the volume. A ratio of 4.0 is equivalent to
                    a setting of 4:1 in a pro-audio compressor like the Waves C1.

                attack - default: 5.0
                    Attack in milliseconds. How long it should take for the compressor
                    to kick in once the audio has exceeded the threshold.
                release - default: 50.0
                    Release in milliseconds. How long it should take for the compressor
                    to stop compressing after the audio has falled below the threshold.

            For an overview of Dynamic Range Compression, and more detailed explanation
            of the related terminology, see:
                http://en.wikipedia.org/wiki/Dynamic_range_compression
        """

        self.compression = True
        self.comp_args = dict(threshold=threshold, ratio=ratio, attack=attack, release=release)
        return self  # So you can use this in channel setup files and return the channel

    def get_next(self):
        if len(self._queue) > self.index+1:
            return self._queue[self.index+1]
    def get_prev(self):
        if self.index-1 > -1:
            return self._queue[self.index-1]
    def get_last(self):
        return self._queue[-1]
    def get_first(self):
        return self._queue[0]

    def get_current(self):
        return f'<Track {self.index} - "{self.current.name}">'  # yay f-strings

    def fade_gain(self, to, duration):
        Thread(target=self._fade_gain, args=(to, duration), daemon=True).start()
    def _fade_gain(self, to, duration, interval=10):
        self.fading = True  # takes control of the gain slider
        if duration:
            # interval is in ms
            duration *= 1000
            delta = (to - self.gain) * (interval / duration)
            for _ in range(duration//interval):
                self.gain += delta
                sleep(interval/1000)
        self.gain = float(to)
        sleep(0.05)  # lets the screen update with the final gain before relinquishing control over the slider
        self.fading = False

    def queue(self, track, i=-1):
        # Pass parent
        track.channel = self

        # Set mono/stereo
        if not track.initially_mono and self._channel_count == 1:
            tracks = track.track.split_to_mono()
            track.track = tracks[0].overlay(tracks[1]).set_frame_rate(track.track.frame_rate * 2)  # Number of frames doubles in the unification, and that has some side effects
        else:
            track.track = track.track.set_channels(self._channel_count)

        # COMPRESSION IS TOO EXPENSIVE
        #print('comp')
        # Compression
        #if self.compression:
        #    track.track = compress_dynamic_range(track.track, **self.comp_args)
        #print('excomp')

        # Queue
        if i == -1:
            self._queue.append(track)
            return
        self._queue.insert(i, track)

        self.update()

    def goto(self, i, offset=False):
        if i is None:
            return True
        if offset:
            i -= self.TRACK_OFFSET
        if len(self._queue) > i > -1:
            self.index = i
            self.update()
            return True
        return False
    def update(self):
        if self._queue:
            self.current = self._queue[self.index]

    def next(self):
        return self.goto(self.index + 1)
    def back(self):
        return self.goto(self.index - 1)
    def first(self):
        return self.goto(0)
    def last(self):
        return self.goto(len(self._queue)-1)

    def play(self, i=None):
        self.goto(i, True)
        self.current.play()
    def stop(self, i=None):
        self.goto(i, True)
        self.current.stop()
    def pause(self, i=None):
        self.goto(i, True)
        self.current.pause()
    def resume(self, i=None):
        self.goto(i, True)
        self.current.resume()

    def stop_all(self):
        for track in self._queue:
            track.stop()

    def murder(self, i=None):  # Not sure why you'd want to call this
        self._queue[i or self.index]._die()
    def wait(self):
        self.current.wait()
    def close(self):
        for track in self._queue:
            track._die()

    def play_next(self):
        if len(self._queue) > self.index+1:
            self.stop()
            self.next()
            self.play()

    go = play_next


class Track:
    LOCALS = {}
    def __init__(self, file, name='',
                 start_sec=0.0, end_sec=None, fade_in=0.0, fade_out=0.0, delay_in=0.0, delay_out=0.0, gain=0.0, repeat=0,
                 repeat_transition_duration=0.1, repeat_transition_is_xf=False, cut_leading_silence=False,
                 autofollow=(), timed_commands=()):
        # If repeat_transition_xf is False then a delay will be used with repeat_transition_duration; if True, it will crossfade
        # Setting fade_in and fade_out to 0.0 will crash
        self.f = file
        self.name = name or file
        self.start = int(start_sec * 1000)
        self.end = int(end_sec * 1000) if end_sec else None
        self.fade = (int(fade_in*1000) or 1, int(fade_out*1000) or 1)  # Fades of 0.0 crash for some reason, so 1 ms will be preferred as a safety measure
        self.delay = (int(delay_in * 1000), int(delay_out * 1000))
        self.gain = float(gain)  # applied in real time
        self.channel = None
        self.empty = file is None
        self.repeats = repeat

        # Mods; handled by a manager
        # BOTH SHOULD BE LISTS
        self.auto_follow_mods = autofollow
        self.at_time_mods = timed_commands

        if not self.empty:  # File is passed
            fname, ext = os.path.splitext(ntpath.basename(file))  # ntpath.basename splits off the file name from a path
            loaded = None
            wc = os.path.join(DIR, 'wave_cache')

            # We need to check if the file is a wav or not because loading wav is fast af
            if ext != '.wav':
                for f in os.listdir(wc):
                    if os.path.splitext(f)[0] == fname:
                        # Not a wav but we found a cached wav copy
                        print('WAV CACHE:', os.path.join(wc, f))
                        loaded = AudioSegment.from_file(os.path.join(wc, f))
                        break
                if loaded is None:
                    # We didn't find a cached wav so we need to load it; cache a wav copy
                    loaded = AudioSegment.from_file(file)
                    print('GENERATING WAV:', os.path.join(wc, fname+'.wav'))
                    loaded.export(os.path.join(wc, fname+'.wav'), format='wav')
            else:
                # They gave us a wav thank God
                print('WAV RECEIVED:', file)
                loaded = AudioSegment.from_file(file)

            # delay in, start time, end of leading silence, end time, fade in, fade out
            self.track = AudioSegment.silent(self.delay[0]) +\
                         (loaded[self.start + (detect_leading_silence(loaded) if cut_leading_silence else 0):self.end].fade_in(self.fade[0]).fade_out(self.fade[1]))
            # repeats; track + delay + track + ...
            if repeat_transition_is_xf: # delay
                if repeat_transition_duration:
                    for _ in range(repeat):
                        self.track += AudioSegment.silent(int(repeat_transition_duration*1000)) + self.track
                else:
                    self.track *= repeat
            else: # xf
                for _ in range(repeat):
                    self.track = self.track.append(self.track, crossfade=repeat_transition_duration)
            # delay out
            self.track += AudioSegment.silent(self.delay[1])
        else: # An empty track is desired for whatever reason; use delay in and delay out
            self.track = AudioSegment.silent(self.delay[0]) + AudioSegment.silent(self.delay[1])

        self.initially_mono = False if self.track.channels > 1 else True
        self.stream = PA.open(format=PA.get_format_from_width(self.track.sample_width),
                              channels=self.track.channels,
                              rate=self.track.frame_rate,
                              output=True)  # Audio out
        self._renew_thread()

        self.pause_lock = Lock()
        self.playing = False
        self.paused = False
        self.play_time = 0  # ms
        self.temp_start = 0 # ms
        self.temp_end = int(self.length*1000)
        self.at_time_queue = []
        self.queue_index = 0
        self.old = False  # False until played; False when renewed, to make sure you don't renew it multiple times

    def __repr__(self):
        return f'<Track "{self.name}">'

    @property
    def length(self):
        return self.track.duration_seconds

    def _play(self):
        self.playing = True
        self.old = True
        print('playing')
        for chunk in make_chunks(self.track[self.temp_start:self.temp_end], CHUNK):
            if self.paused:
                print('lock')
                self.stream.stop_stream()  # Sometimes audio gets stuck in the pipes and pops when pausing/resuming
                self.pause_lock.acquire()  # yay Locks; blocks until released in resume()
            if not self.playing:
                print('stop')
                break  # Kills thread
            #print('round')
            if self.stream.is_stopped():
                self.stream.start_stream()
            try:
                self.stream.write((chunk + self.channel.gain + self.gain)._data)  # Live gain editing is possible because it's applied to each 50 ms chunk in real time
            except OSError:
                # Couldn't write to host device; maybe it unplugged?
                pass
            self.play_time += CHUNK
            if self.queue_index != len(self.at_time_queue) and abs(self.at_time_queue[self.queue_index][0] - self.play_time) < CHUNK:
                # If within a CHUNK of the execution time
                for s in self.at_time_queue[self.queue_index][1]:
                    try:
                        exec(s, builtins.__dict__, self.LOCALS)
                    except Exception as e:
                        print('Timed command failed:', e)
                self.queue_index += 1
            # print(self.play_time)
        self._renew()  # Thread automatically renewed just in case because I don't want to do this manually
        self.play_time = 0
        self.stream.stop_stream()

    def _renew_thread(self):
        self.thread = Thread(target=self._play, daemon=True)

    def _renew(self):
        if self.old:
            self.old = False
            self.queue_index = 0
            self.temp_start = 0
            self.temp_end = int(self.length*1000)
            print('RENEW')
            self.playing = False
            self._renew_thread()

    def at_time(self, sec, *execstr):
        q = self.at_time_queue
        ms = int(sec*1000)
        data = (ms, execstr)
        if not q:  # Empty queue, just append
            q.append(data)
        else:  # Iterate through the queue until we hit something that's larger; if there's nothing larger, append
            for i, item in enumerate(q):
                if item[0] > ms:
                    q.insert(i, data)
                    return
            q.append(data)

    def start_at(self, sec=None):
        self.old = True
        self._renew()
        if sec:
            self.temp_start = int(sec*1000)
        self.play_time = self.temp_start
        # Fetch the nearest queue item by distance to self.temp_start, find it's index, assign to queue_index
        if self.at_time_queue:
            self.queue_index = sorted([(abs(dat[0]-self.temp_start), i) for i,dat in enumerate(self.at_time_queue)], key=lambda i: i[0])[0][1]

    def end_at(self, sec=None):
        self._renew()
        if sec:
            self.temp_end = int(sec * 1000)

    def play(self):
        if self.empty:
            return
        print('threading')
        # Must call renew() if playing multiple times due to threads being unable to restart
        try:
            self.thread.start()
        except RuntimeError:
            print('PLEASE RENEW BEFORE YOU DO THAT')

    def wait(self):
        self.thread.join()

    def pause(self):
        if not self.paused:
            self.paused = True

    def resume(self):
        if self.paused:
            self.paused = False
            self.pause_lock.release()

    def stop(self):
        if self.playing:
            self.playing = False
        if self.paused:
            self.resume()
        self.play_time = 0
        try:
            self.thread.join(0.2)
        except RuntimeError:
            pass

    def _die(self):
        # Track cannot be played anymore once this is called
        self.playing = False
        self.stream.stop_stream()
        self.stream.close()

    def autofollow(self, track, crossfade=0.1):
        # track is Track
        # if you want delay then autofollow an empty track; crossfade 0 is acceptable if you prefer to use fade_out
        self.track = self.track.append(track.track, int(crossfade*1000))


if __name__ == "__main__":
    chan = Channel(gain=-1.0)
    chan.queue(t := Track("From Peak to Peak.wav"))
    # chan.queue(Track("Autumn's Last Breath.mp3"))  # mp3 broke
    chan.update()
    chan.play()
    chan.wait()
    chan.close()