import pyaudio
import os.path, os
import ntpath
from threading import Thread
from time import sleep
from pydub import AudioSegment
import audioop
from pydub.utils import make_chunks
from pydub.effects import compress_dynamic_range
import multiprocessing as mp
from math import ceil
from extras import sizemb, safe_print as print
import extras
import shared
import sys
from queue import Queue
import streaming

DIR = os.getcwd()

PA = pyaudio.PyAudio()
class DeviceDisconnected(BaseException):
    pass

# Missing pydub feature - taken from the pydub github
# https://github.com/jiaaro/pydub
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

# Uses a generator instead of a list because when it's a list mp breaks horrendously
# Code modified from the pydub source on github
def make_chunks(audio_segment: AudioSegment, chunk_length):
    """
    Breaks an AudioSegment into chunks that are <chunk_length> milliseconds
    long.
    if chunk_length is 50 then you'll get a list of 50 millisecond long audio
    segments back (except the last one, which can be shorter)
    """
    number_of_chunks = ceil(len(audio_segment) / float(chunk_length))
    return (audio_segment[i * chunk_length:(i + 1) * chunk_length]
            for i in range(int(number_of_chunks)))


class Channel:
    TRACK_OFFSET = 0

    def __init__(self, name='Unnamed Channel', color='#FFF', gain=0.0, mono=False, device_index=None):
        self.gain = shared.Float(gain)
        self.current: Track = Track(None)
        self._queue: [Track] = []
        self.index = 0
        self._channel_count = 1 if mono else 2
        self.compression = False
        self.comp_args = dict(threshold=-20.0, ratio=4.0, attack=5.0, release=50.0)
        self.color = color
        self.name = name
        self.fading = False
        self.device = device_index

    # Compression applies to ALL tracks queued in a channel - if you want only certain tracks compressed, a separate channel should be created for them
    # UNUSED because it's SO EXPENSIVE
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
        self.gain.set(float(to))
        sleep(0.05)  # lets the screen update with the final gain before relinquishing control over the slider
        self.fading = False

    def queue(self, track, i=-1, _ready_barrier=mp.Barrier(1)):
        # Pass parent
        track.channel = self
        track._ready_barrier = _ready_barrier  # To synchronize with main thread

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
        else:
            self._queue.insert(i, track)

        print('Initializing %s...' % track)
        track.procinit()
        self.update()
        freed = sizemb(track.track._data)
        del track.track  # The only place this is used should be in subprocesses, which have already copied the data over... therefore this is wasted RAM, and it is LARGE
        print('Freed %.2f MB of copied RAM.' % freed)

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
    EXECUTOR_QUEUE = None
    STDOUT = None
    CACHE_CONVERTED = True
    CACHE_DOWNLOADED = True

    CHUNK = 50  # 50ms chunks for processing – if it's too low then the overhead gets larger than the chunks are!
    # CHUNK overridden in config

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['proc']
        return d

    def __init__(self, file, name='',
                 start_sec=0.0, end_sec=None, fade_in=0.0, fade_out=0.0, delay_in=0.0, delay_out=0.0, gain=0.0, repeat=0,
                 repeat_transition_duration=0.1, repeat_transition_is_xf=False, cut_leading_silence=False,
                 autofollow=(), timed_commands=(), chunk_override=CHUNK):
        # If repeat_transition_xf is False then a delay will be used with repeat_transition_duration; if True, it will crossfade
        # Setting fade_in and fade_out to 0.0 will crash
        self.f = file
        self.name = name or file
        self.start = int(start_sec * 1000)
        self.end = int(end_sec * 1000) if end_sec else None
        self.fade = (int(fade_in*1000) or 1, int(fade_out*1000) or 1)  # Fades of 0.0 crash for some reason, so 1 ms will be preferred as a safety measure
        self.delay = (int(delay_in * 1000), int(delay_out * 1000))
        self.gain = shared.Float(gain)  # applied in real time
        self.channel = None
        self.empty = file is None
        self.repeats = repeat

        self._ready_barrier = mp.Barrier(1)  # To synchronize with main
        # This should be replaced in Channel.queue(), as multiple tracks are usually queued at once, and all of them need to be waited for

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
                    if self.CACHE_CONVERTED and 'yt_cache' not in file or self.CACHE_DOWNLOADED and 'yt_cache' in file:
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

            del loaded
        else: # An empty track is desired for whatever reason; use delay in and delay out
            self.track = AudioSegment.silent(self.delay[0]) + AudioSegment.silent(self.delay[1])

        self.initially_mono = False if self.track.channels > 1 else True
        self.length = self.track.duration_seconds
        self.CHUNK = chunk_override

        self.proc = mp.Process(target=self.procloop, args=(self.EXECUTOR_QUEUE, self.STDOUT), daemon=True)
        self.restart_lock = mp.Lock()
        self.restart_lock.acquire(False) # Prevents from autoplaying at launch

        self.pause_lock = mp.Lock()
        self.playing = shared.Bool()
        self.paused = shared.Bool()
        self.play_time = shared.Int()  # ms
        self.temp_start = shared.Int() # ms
        self.temp_end = shared.Int(self.length*1000)
        self.at_time_queue = []
        self.queue_index = shared.Int()
        self.old = shared.Bool()  # False until played; False when renewed, to make sure you don't renew it multiple times

        self.streaming = shared.Bool(True)

    def __repr__(self):
        return f'<Track "{self.name}">'

    def procinit(self):
        self.proc.start()

    def procloop(self, exec_queue, stdout):
        sys.stdout = sys.stderr = stdout
        print('Subprocess for %s started.' % self)
        stream = PA.open(format=PA.get_format_from_width(self.track.sample_width),
                         channels=self.track.channels,
                         rate=self.track.frame_rate,
                         output=True,  # Audio out
                         output_device_index=self.channel.device)

        data_stream = None
        if self.streaming:
            print('Freed another %.2f MB by streaming.' % (sys.getsizeof(self.track.raw_data) / 1000000))
            data_stream = streaming.AudioStream(self.track, self.name)
            print('STREAMING', self.name)
            #print(sys.getsizeof(data_stream.__dict__), sys.getsizeof(data_stream.audio.__dict__), data_stream.audio.__dict__)
            data_stream.load_ms(0, 2000)

        stream_queue = Queue(1)
        self.player_thread = Thread(target=self._write_to_stream, args=(stream, stream_queue), daemon=True)
        self.player_thread.start()
        try:
            print('%s on standby' % self)
            self._ready_barrier.wait()  # main should be the last to the barrier, unless we don't care about waiting for proc to be ready
            extras.testmem()
            while True:
                self.restart_lock.acquire(True)
                self._play(stream, stream_queue, exec_queue, data_stream)
                self._renew()
                print('%s on standby' % self)
        finally:
            stream_queue.put(None)
            stream.close()
            #os.remove(data_stream.fp)

    def _write_to_stream(self, stream: pyaudio.Stream, stream_queue: Queue):
        while True:
            data = stream_queue.get()
            if data is None:
                break
            stream.write(data)
            stream_queue.task_done()

    def _play(self, stream: pyaudio.Stream, stream_queue: Queue, exec_queue: mp.Queue, data_stream: streaming.AudioStream=None):
        self.playing.set(True)
        self.old.set(True)
        print('playing %s' % self)

        if data_stream is not None:
            data_stream.seek_chunk(data_stream.chunk_number(self.temp_start))
            data_stream.set_eof_at_chunk(data_stream.chunk_number(self.temp_end))
            chunks = streaming.audio_stream_blocker(data_stream, self.CHUNK)
            print(chunks)
        else:
            chunks = make_chunks(self.track[self.temp_start:self.temp_end], self.CHUNK)

        for chunk in chunks:
            #print('chunked')
            if self.paused:
                print('pause_lock acquired')
                stream.stop_stream()  # Sometimes audio gets stuck in the pipes and pops when pausing/resuming
                self.pause_lock.acquire()  # yay Locks; blocks until released in resume()
            #print('pause checked')
            if not self.playing:
                print('stopping track')
                break  # Kills thread
            #print('play checked')
            #print('round')
            if stream.is_stopped():
                stream.start_stream()
            #print('stop checked')

            try:
                if data_stream is not None:
                    data = audioop.mul(chunk, self.track.sample_width, 10 ** (float(self.channel.gain + self.gain) / 10))
                else:
                    data = (chunk + self.channel.gain + self.gain)._data  # Live gain editing is possible because it's applied to each chunk in real time
                #print('new segment created')
                stream_queue.join() # this should block until _write_to_stream() is done processing
                stream_queue.put(data)  # this will also block if there's more than 1 item in the queue, but that's impossible?
                #stream.write(data)
            except OSError:
                # Couldn't write to host device; maybe it unplugged?
                raise DeviceDisconnected

            #print('wrote!')
            self.play_time += self.CHUNK
            if self.queue_index != len(self.at_time_queue) and abs(self.at_time_queue[self.queue_index.get()][0] - self.play_time) < self.CHUNK:
                # If within a CHUNK of the execution time
                for s in self.at_time_queue[self.queue_index.get()][1]:
                    exec_queue.put(s)
                self.queue_index += 1
            # print(self.play_time)
        stream.stop_stream()

    def _renew(self):
        if self.old:
            self.old.set(False)
            self.queue_index.set(0)
            self.temp_start.set(0)
            self.temp_end.set(int(self.length*1000))
            self.play_time.set(0)
            print('resetting track')
            self.playing.set(False)
            self.restart_lock.acquire(False)

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
        self.old.set(True)
        self._renew()
        if sec:
            self.temp_start.set(int(sec*1000))
        self.play_time.set(self.temp_start.value)
        # Fetch the nearest queue item by distance to self.temp_start, find it's index, assign to queue_index
        if self.at_time_queue:
            self.queue_index.value = sorted([(abs(dat[0]-self.temp_start), i) for i,dat in enumerate(self.at_time_queue)], key=lambda i: i[0])[0][1]

    def end_at(self, sec=None):
        self._renew()
        if sec:
            self.temp_end.set(int(sec * 1000))

    def play(self):
        if self.empty:
            return
        print('releasing restart_lock')
        # Must call renew() if playing multiple times due to threads being unable to restart
        # print(self.restart_lock)
        try:
            self.restart_lock.release()
        except ValueError:
            print('please reset the track before playing it again')

    def pause(self):
        if not self.paused:
            self.paused.set(True)
            self.pause_lock.acquire(False)

    def resume(self):
        if self.paused:
            self.paused.set(False)
            self.pause_lock.release()

    def stop(self):
        if self.playing:
            self.playing.set(False)
        if self.paused:
            self.resume()
        self.start_at(0)

    def _die(self):
        # Track cannot be played anymore once this is called
        self.playing.set(False)
        self.proc.close()
        self.proc.join(0.5)

    def autofollow(self, track, crossfade=0.1):
        # track is Track but annotation dies :(
        # if you want delay then autofollow an empty track; crossfade 0 is acceptable if you prefer to use fade_out
        self.track = self.track.append(track.track, int(crossfade*1000))
        self.length += track.track.duration_seconds


if __name__ == "__main__":
    chan = Channel(gain=-1.0)
    chan.queue(t := Track("From Peak to Peak.wav"))
    # chan.queue(Track("Autumn's Last Breath.mp3"))  # mp3 broke
    chan.update()
    chan.play()
    chan.wait()
    chan.close()