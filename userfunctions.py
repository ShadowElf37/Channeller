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


# eos = EOSIonXe(channeller.osc, '0.0.0.0')
