from math import ceil
from os.path import getsize, exists, join
from pydub import AudioSegment
from io import SEEK_SET, SEEK_CUR
import shared
import sys
import uuid

class BinaryStream:
    def __init__(self, fp, chunk=1):
        self.fp = fp
        self.f = open(fp, 'rb')
        self.size = getsize(fp)
        self.chunk = chunk
        self.f.seek(0)
        self.cache: {(int, int): bytes} = dict()  # (start, end): data

    def __next__(self):
        return self.read(1)

    def __iter__(self):
        for _ in range(ceil(self.size / self.chunk)):
            yield self.read(1)

    @property
    def pos(self):
        return self.f.tell()

    def load(self, from_, to):
        self.cache[(from_, to)] = self.read_all(from_, to)
    def load_all(self):
        self.load(0, -1)
    def dump_cache(self):
        self.cache.clear()
    def cache_notify(self, t, interval):
        print(f'FILE STREAM: Type {t} cache access on', interval)

    def skip_bytes(self, n):
        self.f.seek(n, SEEK_CUR)
    def skip(self, chunks=1):
        self.skip_bytes(self.chunk*chunks)

    def read_bytes(self, n):
        if n == 0:
            return b''
        p1, p2 = self.pos, self.pos+n
        for interval in self.cache.keys():
            dp1 = p1 - interval[0]
            dp2 = p2 - interval[1]
            if p1 >= interval[0] and p2 <= interval[1]:  # desired is within or equal to cached data
                #self.cache_notify(1, interval)
                data = self.cache[interval][dp1:dp2 or None]
                self.f.seek(p2)
            elif p1 < interval[0] and p2 <= interval[1] and p2 > interval[0]:  # desired overlaps with first border of cached data
                #self.cache_notify(2, interval)
                data = self.read_bytes(-dp1) + self.cache[interval][:dp2 or None]
                self.f.seek(p2)
            elif p1 >= interval[0] and p1 < interval[1] and p2 > interval[1]: # desired overlaps with second border of cached data
                #self.cache_notify(3, interval)
                data = self.cache[interval][dp1:]
                self.skip_bytes(len(data))
                data += self.read_bytes(dp2)
            elif p1 < interval[0] and p2 > interval[1]: # cached is within desired
                #self.cache_notify(4, interval)
                c = self.cache[interval]
                data = self.read_bytes(-dp1) + c
                self.skip_bytes(len(c))
                data += self.read_bytes(dp2)
            else:
                continue

            return data

        return self.f.read(n)
    def read(self, chunks=1):
        return self.read_bytes(chunks*self.chunk)

    def read_all(self, from_=0, to=-1):
        old_pos = self.pos
        self.f.seek(from_)
        data = self.read_bytes(to - from_)
        self.f.seek(old_pos)
        return data
    def read_all_chunks(self, from_=0, to=-1):
        return self.read_all(from_*self.chunk, to*(self.chunk if to > -1 else 1))

    def close(self):
        self.f.close()


class AudioStream(BinaryStream):
    def __init__(self, audio: AudioSegment, trackname: str):
        self.audio = audio
        self.UUID = uuid.uuid5(uuid.NAMESPACE_DNS, 'stream.%s' % trackname)
        self.fp = join('stream_cache', '_CHANNELLER_DISKSTREAM_%s' % self.UUID)
        if exists(self.fp):
            self.f = open(self.fp, 'rb')
        else:
            self.f = open(self.fp, 'wb+')
            self.f.write(self.audio.raw_data)
            self.f.flush()
        self.chunk = self.audio.frame_width  # frame
        self.size = self.eof = len(self.audio.raw_data)  # eof will be used in the blocker; see bottom of file
        self.f.seek(0)
        self.cache: {(int, int): bytes} = dict()  # (start, end): data

        self.frame_rate = self.audio.frame_rate

        #print(sys.getrefcount(self.audio._data))
        del self.audio._data


    def chunk_number(self, ms):
        return int(ms * self.frame_rate / 1000.0)

    def read_bytes(self, n):
        return super().read_bytes(n)

    def read_ms(self, start, end=None):
        start_chunk = self.chunk_number(start)
        end_chunk = self.chunk_number(end)
        return self.audio._spawn(self.read_all_chunks(start_chunk, end_chunk))
    def load_ms(self, start, end=None):
        start_byte = self.chunk_number(start) * self.chunk
        end_byte = self.chunk_number(end) * self.chunk
        return self.load(int(start_byte), int(end_byte))

    def read_as_audio(self, ms):
        return self.audio._spawn(self.read(self.chunk_number(ms)))

    def seek_chunk(self, n):
        self.f.seek(n*self.chunk, SEEK_SET)

    def set_eof_at_chunk(self, n=None):
        if n is None or n < 0:
            self.eof = self.size / self.chunk
        else:
            self.eof = n


def audio_stream_blocker(audio_stream: AudioStream, ms_per_block):  # this is the only function that uses eof to stop serving audio at a certain point
    # print('$$', audio_stream.eof , audio_stream.chunk , ms_per_block, audio_stream.eof / ms_per_block)
    for block in range(ceil(audio_stream.eof / ms_per_block)):
        yield audio_stream.read(audio_stream.chunk_number(ms_per_block))



if __name__ == "__main__":
    f = BinaryStream('CHANGELOG', chunk=3)
    f.load(2, 4)
    for chunk in f:
        print(chunk)