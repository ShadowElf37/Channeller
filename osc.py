from oscpy.server import OSCThreadServer as _OSCThreadServer
from time import sleep

ENC = 'utf-8'
def b(obj):
    # converts strings and lists to bytes; recursive too!
    if type(obj) in (list, tuple):
        return type(obj)([b(s) for s in obj])
    elif type(obj) is str:
        return bytes(obj, ENC)
    return obj

class Server:
    def __init__(self, host='0.0.0.0', port=57120, encoding='', timeout=0.01):
        self.osc = _OSCThreadServer(encoding=encoding, timeout=timeout)
        self.host = host
        self.port = port
        self.socket = None
        self.clients = {}

    def gaddr(self):
        return self.host, self.port

    def init(self):
        self.socket = self.osc.listen(*self.gaddr(), default=True)

    def bind_handler(self, addr, callback):
        self.osc.bind(b(addr), callback)

    def add_client(self, name, host, port):
        self.clients[name] = host, port
    def get_client(self, name):
        return self.clients.get(name)

    def send_msg(self, client_name, method, *msg):
        try:
            return self.osc.send_message(b(method), b(msg), *self.clients[client_name])
        except RuntimeError:
            raise ConnectionError('init() needs to be called on OSC server')
    def send(self, client_name, method, *msg):
        self.send_msg(client_name, method, *msg)

    def _send_msg_obj(self, client_name, msg):
        return self.send_msg(client_name, msg.method, *msg.contents)
    def _send_bundle_obj(self, client_name, bundle):
        return self.osc.send_bundle(bundle.unwrap(), *self.clients[client_name])

    def send_obj(self, client_name, obj):
        if isinstance(obj, Message):
            return self._send_msg_obj(client_name, obj)
        return self._send_bundle_obj(client_name, obj)

    def stop(self):
        self.osc.stop_all()


class Message:
    def __init__(self, method: str, *contents: [str]):
        self.method = method
        self.contents = contents

class Bundle:
    def __init__(self, *messages: [Message]):
        self.msgs = list(messages)
    def add(self, msg):
        self.msgs.append(msg)

    def unwrap(self):
        return [(m.method, m.contents) for m in self.msgs]


if __name__ == "__main__":
    s = Server()
    c = Server(port=57121)
    s.init()
    c.init()
    s.add_client('client', 'localhost', 57121)
    c.bind_handler('/test', print)
    s.send_msg('client', '/test', 'hey', 'how are you')
    sleep(1)
