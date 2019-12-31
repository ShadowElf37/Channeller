import pyaudio
from suppressor import IndustrialGradeWarningSuppressor
from threading import Thread, Lock
from time import sleep

# TODO
# def at_time(t, f): thread... # for tracks

with IndustrialGradeWarningSuppressor():
    # Dumb bitch whines a lot
    from pydub import AudioSegment
    from pydub.utils import make_chunks
    from pydub.effects import compress_dynamic_range

PA = pyaudio.PyAudio()
CHUNK = 50  # 50ms chunks for processing – if it's too low then the overhead gets larger than the chunks are!

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


class Manager:
    def __init__(self, *channels):
        self.channels = {name:Channel(name) for name in channels}

    def load_channels(self, file):
        # The file should be formatted as line-by-line Channel instantiations
        with open(file, 'r') as f:
            self.channels = {c.name: c for c in [eval(line) for line in f.readlines() if line[0] != '#']}

class Channel:
    def __init__(self, name='Unnamed Channel', color='#FFF', gain=0.0, mono=False):
        self.gain = gain
        self.current: Track = None
        self._queue: [Track] = []
        self.index = 0
        self._channel_count = 1 if mono else 2
        self.compression = False
        self.comp_args = dict(threshold=-20.0, ratio=4.0, attack=5.0, release=50.0)
        self.color = color
        self.name = name

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

    def get_current(self):
        return f'<Track {self.index} - "{self.current.name}">'  # yay f-strings

    def fade_gain(self, to, duration):
        Thread(target=self._fade_gain, args=(to, duration)).start()
    def _fade_gain(self, to, duration, interval=10):
        # interval is in ms
        duration *= 1000
        delta = (to - self.gain)*(interval/duration)
        for _ in range(duration//interval):
            self.gain += delta
            sleep(interval/1000)
        self.gain = float(to)

    def queue(self, track, i=-1):
        # Pass parent
        track.channel = self

        # Set mono/stereo
        if not track.initially_mono and self._channel_count == 1:
            tracks = track.track.split_to_mono()
            track.track = tracks[0].overlay(tracks[1]).set_frame_rate(track.track.frame_rate * 2)  # Number of frames doubles in the unification, and that has some side effects
        else:
            track.track = track.track.set_channels(self._channel_count)

        # Compression
        track.track = compress_dynamic_range(track.track, **self.comp_args)

        # Queue
        if i == -1:
            self._queue.append(track)
            return
        self._queue.insert(i, track)

    def goto(self, i):
        if len(self._queue) > i > -1:
            self.index = i
            self.update()
    def update(self):
        self.current = self._queue[self.index]

    def next(self):
        self.goto(self.index + 1)
    def back(self):
        self.goto(self.index - 1)
    def first(self):
        self.goto(0)
    def last(self):
        self.goto(len(self._queue))

    def play(self):
        self.current.play()
    def stop(self):
        self.current.stop()
    def pause(self):
        self.current.pause()
    def resume(self):
        self.current.resume()
    def murder(self, i=None):  # Not sure why you'd want to call this
        self._queue[i or self.index]._die()
    def wait(self):
        self.current.wait()
    def close(self):
        for track in self._queue:
            track._die()


class Track:
    def __init__(self, f, name='', start_sec=0.0, end_sec=None, fade_in=0.0, fade_out=0.0, delay_in=0.0, delay_out=0.0, gain=0.0, repeat=0, repeat_transition_duration=0.1, repeat_transition_is_xf=False, cut_leading_silence=False):
        # NOTE: gain here is PRESET and CANNOT BE CHANGED DURING RUNTIME; apply runtime gain changes in the track's CHANNEL
        # If repeat_transition_xf is False then a delay will be used with repeat_transition_duration; if True, it will crossfade
        # Setting fade_in and fade_out to 0.0 will crash
        self.f = f
        self.name = name or f
        self.start = int(start_sec * 1000)
        self.end = int(end_sec * 1000) if end_sec else None
        self.fade = (int(fade_in*1000) or 1, int(fade_out*1000) or 1)  # Fades of 0.0 crash for some reason, so 1 ms will be preferred as a safety measure
        self.delay = (int(delay_in * 1000), int(delay_out * 1000))
        self.gain = gain
        self.channel = None
        self.repeats = repeat

        if f is not None: # File is passed
            with IndustrialGradeWarningSuppressor(): # Shut up no one likes you
                loaded = AudioSegment.from_file(f)
                # delay in, start time, end of leading silence, end time, fade in, fade out, preset-gain
                self.track = AudioSegment.silent(self.delay[0]) +\
                             (loaded[self.start + (detect_leading_silence(loaded) if cut_leading_silence else 0):self.end].fade_in(self.fade[0]).fade_out(self.fade[1]) + gain)
                # repeats; track + delay + track + ...
                if repeat_transition_is_xf: # delay
                    for _ in range(repeat):
                        self.track += AudioSegment.silent(int(repeat_transition_duration*1000)) + self.track
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
        self.pause_lock = Lock()
        self.playing = False
        self.paused = False
        self.play_time = 0  # ms
        self.temp_start = 0 # ms
        self.temp_end = self.length

        self.thread = Thread(target=self._play, daemon=True)

    def __repr__(self):
        return f'<Track "{self.name}">'
    @property
    def length(self):
        return self.track.duration_seconds

    def _play(self, from_=0.0, to=None):
        self.playing = True
        self.play_time = 0
        for chunk in make_chunks(self.track[self.temp_start:self.temp_end], CHUNK):
            if not self.playing:
                break  # Kills thread
            if self.paused:
                self.pause_lock.acquire()  # yay Locks; blocks until released in resume()
            self.stream.write((chunk + self.channel.gain)._data)  # Live channel.gain editing is possible because it's applied to each 50 ms chunk in real time
            self.play_time += CHUNK
            # print(self.play_time)
        self._renew()  # Thread automatically renewed because I don't want to do this manually

    def _renew(self):
        self.temp_start = 0
        self.temp_end = self.length
        self.thread = Thread(target=self._play, daemon=True)

    def start_at(self, sec):
        self._renew()
        self.temp_start = int(sec*1000)
        self.play_time = self.temp_start
    def end_at(self, sec):
        self._renew()
        self.temp_end = int(sec * 1000)

    def play(self):
        # Must call renew() if playing multiple times due to threads being unable to restart
        self.thread.start()

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
    manager = Manager()
    manager.load_channels('test.cfg')
    print(manager.channels)
    PA.terminate()

    exit()
    chan = Channel(gain=-1.0)
    chan.queue(Track("From Peak to Peak.wav"))
    # chan.queue(Track("Autumn's Last Breath.mp3"))  # mp3 broke
    chan.next()
    chan.play()
    sleep(2)
    chan.fade_gain(1.0, 3)
    chan.wait()
    chan.close()