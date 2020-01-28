import userfunctions, builtins

class Cue:
    def __init__(self, code, desc):
        self.code = code
        self.desc = desc

    def execute(self, **locals_):
        exec(self.code, {**builtins.__dict__, **userfunctions.__dict__}, locals_)

class CueManager:
    CUE_OFFSET = 0
    SKIP_EMPTY_CUES = True
    def __init__(self, channel_manager=None):
        self.m = channel_manager
        self.cues: [Cue] = []
        self.i = 0
        self.locals = {}

    def load_file(self, fp):
        for line in open(fp).readlines():
            s = line.split('#')
            if len(s) == 1:
                c = d = s[0]
            else:
                c, d = s
            self.cue(c.strip(), (d or c).strip())

    def check_i(self, i):
        return len(self.cues) > i > -1

    def cue(self, code, desc):
        self.cues.append(Cue(code, desc))
    def delete(self, i):
        if self.check_i(i):
            del self.cues[i]

    def _next(self):
        if self.check_i(self.i + 1):
            self.i += 1
            return True
        return False
    def _back(self):
        if self.check_i(self.i - 1):  # Needs to be allowed to go to -1
            self.i -= 1
            return True
        return False

    def next(self):
        if self.SKIP_EMPTY_CUES:
            self._next()
            while not self.cues[self.i].code:
                if not self._next(): break
                # This will break as soon as _next() returns False (i.e. we're at the end of the cue list) OR when there's a cue with code in it
        else:
            self._next()

    def back(self):
        if self.SKIP_EMPTY_CUES:
            self._back()
            while not self.cues[self.i].code:
                if not self._back(): break
                # This will break as soon as _back() returns False (i.e. we're at the front of the cue list) OR when there's a cue with code in it
        else:
            self._back()

    def goto(self, i, offset=False):
        OFFSET = self.CUE_OFFSET if offset else 0
        if self.check_i(i - OFFSET):
            self.i = i - OFFSET
            return True
        return False

    def do(self):
        self.get(self.i).execute(**self.locals)

    def go(self):
        self.do()
        self.next()

    def get(self, i) -> Cue:
        if self.check_i(i) and i != -1:
            return self.cues[i]
        return NULLCUE


NULLCUE = Cue('', 'None')
