from os.path import join
import os

class Path:
    def __init__(self, *path):
        self._p = join(*path)

    def __add__(self, other):
        return join(self._p, other)

    def __str__(self):
        return self._p

    @property
    def path(self):
        return self._p


class NonceVar:
    def get(self, *args, **kwargs):
        pass
    def set(self, *args, **kwargs):
        pass


def get_lines_of_code(start_path='.'):
    total_lines = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            # skip if it is symbolic link
            if not os.path.islink(fp) and (os.path.splitext(fp)[1] or 'nope') in '.js .py .html .css':
                print('Counting', fp)
                with open(fp, 'rb') as f:
                    total_lines += sum([1 for l in f.readlines() if l.strip()])
    return total_lines

if __name__ == "__main__":
    print('Counted %s lines of code.' % get_lines_of_code())
