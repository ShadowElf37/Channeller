import channeller
from extensions import ProsceniumClient

pc = ProsceniumClient()

def after(duration, f=(lambda *args, **kwargs: None), *args, **kwargs):
    from time import sleep
    from threading import Thread
    def exec(*args, **kwargs):
        sleep(duration)
        f(*args, **kwargs)
    Thread(target=exec, args=args, kwargs=kwargs, daemon=True).start()


def fade_out(channel, duration):
    original_gain = channel.gain
    channel.fade_gain(-20, duration)
    after(duration, channel.stop_all)
    after(duration+0.1, channel.fade_gain, original_gain, 0)

# eos = EOSIonXe(channeller.osc, '0.0.0.0')
