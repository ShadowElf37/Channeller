class OSCDevice:
    device_counter = 0

    def __init__(self, server, host, port=8000):
        self.server = server
        self.name = '{}{}'.format(self.__class__.__name__, self.device_counter)
        self.device_counter += 1
        self.host = host
        self.port = port
        server.add_client(self.name, host, port)

    def _send(self, method, *args):
        self.server.send_msg(self.name, method, *args)
        return method, *args

    def interface(self, **fdict):
        return type('OSCDeviceInterface', (), {k: (lambda *args: self._send(v % args)) if isinstance(v, str) else (lambda *args: self._send(v[0], *v[1:], *args)) for k,v in fdict.items()})


class EOSIonXe(OSCDevice):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server.bind_handler('/eos/out/ping', lambda: print(f'{self.name} pong'))

    def send_cmd(self, string: str, clear_console=False):
        self._send('/eos/%scmd' % ('new' if clear_console else ''), string.title())
    send=send_cmd

    def cue(self, i, list_no=1):
        return self.interface(fire=(go := f'/eos/cue/{list_no}/{i}/fire'),
                              go=go,
                              select=f'/eos/cue/{list_no}/{i}')

    def preset(self, i):
        return self.interface(recall=f'/eos/preset/{i}/fire',
                              select=f'/eos/preset/{i}')

    def macro(self, i):
        return self.interface(fire=f'/eos/macro/{i}/fire',
                              select=f'/eos/macro/{i}')

    def key(self, name):
        name = name.lower()
        return self.interface(down=(f'/eos/key/{name}', 1.0),
                              up=(f'/eos/key/{name}', 0.0),
                              press=f'/eos/key/{name}')

    def chan(self, i):
        pref = f'/eos/chan/{i}/'
        return self.interface(out=pref+'out',
                              home=pref+'home',
                              remdim=pref+'remdim',
                              level=pref+'level',
                              full=pref+'full',
                              min=pref+'min',
                              max=pref+'max',
                              at=(pref+'at',))

    def active(self):
        pref = '/eos/at'
        return self.interface(out=pref + '/out',
                              home=pref + '/home',
                              remdim=pref + '/remdim',
                              level=pref + '/level',
                              full=pref + '/full',
                              min=pref + '/min',
                              max=pref + '/max',
                              at=(pref,))

    def ping(self):
        self._send('/eos/ping')
        print(f'{self.name}: ping')


import pipe
class ProsceniumClient:
    def __init__(self, ip='localhost', port=38051):
        self.pipe = pipe.Pipe(ip=ip, at=port)
        self.pipe.open(blocking=False)

    def put(self, msg):
        self.pipe.write(msg)
    def get(self):
        return self.pipe.read()


if __name__ == "__main__":
    import osc
    server = osc.Server()
    server.init()
    eos = EOSIonXe(server, 'localhost', server.port)
    print(eos.chan(1).at(50))
