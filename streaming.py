from math import ceil
from os.path import getsize

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
        from io import SEEK_CUR
        self.f.seek(n, SEEK_CUR)
    def skip(self, chunks=1):
        self.skip_bytes(self.chunk*chunks)

    def read_bytes(self, n):
        if n == 0:
            return b''
        p1, p2 = self.pos, self.pos+n
        for interval in self.cache.keys():
            if p1 >= interval[0] and p2 <= interval[1]:  # desired is within or equal to cached data
                self.cache_notify(1, interval)
                data = self.cache[interval][p1-interval[0]:p2-interval[1] or None]
                self.f.seek(p2)
            elif p1 < interval[0] and p2 <= interval[1] and p2 > interval[0]:  # desired overlaps with first border of cached data
                self.cache_notify(2, interval)
                data = self.read_bytes(interval[0]-p1) + self.cache[interval][:p2-interval[1] or None]
                self.f.seek(p2)
            elif p1 >= interval[0] and p1 < interval[1] and p2 > interval[1]: # desired overlaps with second border of cached data
                self.cache_notify(3, interval)
                data = self.cache[interval][p1-interval[0]:]
                self.skip_bytes(len(data))
                data += self.read_bytes(p2-interval[1])
            elif p1 < interval[0] and p2 > interval[1]: # cached is within desired
                self.cache_notify(4, interval)
                c = self.cache[interval]
                data = self.read_bytes(interval[0]-p1) + c
                self.skip_bytes(len(c))
                data += self.read_bytes(p2-interval[1])
            else:
                continue

            return data

        return self.f.read(n)
    def read(self, chunks=1):
        return self.read_bytes(chunks*self.chunk)

    def read_all(self, from_=0, to=-1):
        old_pos = self.pos
        self.f.seek(from_)
        data = self.f.read(to - from_)
        self.f.seek(old_pos)
        return data
    def read_all_chunks(self, from_=0, to=-1):
        return self.read_all(from_*self.chunk, to*(self.chunk if to > -1 else 1))

    def close(self):
        self.f.close()

if __name__ == "__main__":
    f = BinaryStream('CHANGELOG', chunk=3)
    f.load(2, 4)
    for chunk in f:
        print(chunk)