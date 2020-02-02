class OSCDevice:
    device_counter = 0

    def __init__(self, server, host, port=8000):
        self.server = server
        self.name = '{}{}'.format(self.__class__.__name__, self.device_counter)
        self.device_counter += 1
        self.host = host
        self.port = port
        server.add_client(self.name, host, port)

    def send(self, method, *args):
        self.server.send_msg(self.name, method, *args)


class EOSIonXe(OSCDevice):
    def send_cmd(self, string: str):
        self.send('/eos/cmd', string.title())