"""
Usage:

 - userfunctions.py -
import channeller
osc = channeller.osc

 - main.py -
import channeller
channeller._update_objects(cm.locals)
"""

class _TempObject:
    objects = []
    ignore = object()

    def __init__(self, name):
        self.name = name
        self.references: [_TempObject] = []

        # Note that TempObjects might ALSO be called, so we need to be able to handle that...
        self.args = ()
        self.kwargs = {}
        self.call_me = False

    def __repr__(self):
        return '<Uninitialized Object "%s" at %s' % (self.name, id(self))

    def __call__(self, *args, **kwargs):  # If it's treated like a function
        self.call_me = True
        self.args = args
        self.kwargs = kwargs
        return self  # We can return our placeholder

    def notify(self, object: object=None):
        if object is _TempObject.ignore:
            return
        elif object is None:
            self.__dict__.clear()
            t = type('None', (), {})
            t.__repr__ = lambda: None
            t.__eq__ = lambda o: o is None
            t.__ne__ = lambda o: o is not None
            t.__bool__ = lambda: False
            self.__class__ = t
            return
        elif callable(object):
            if self.call_me:
                returned = object(*self.args, **self.kwargs)
                self.notify(returned)
                return

        for ref in self.references:  # Call functions that were waiting to be called
            if ref.call_me:
                returned = getattr(object, ref.name)(*ref.args, **ref.kwargs)
                ref.notify(returned)
            else:
                ref.notify(getattr(object, ref.name))

        self.__dict__.clear()
        self.__dict__.update(object.__dict__)
        self.__class__ = type(object)

    def __getattr__(self, item):
        self.references.append(ref := _TempObject(item))
        return ref


def _import(dictionary):
    for obj in _TempObject.objects:
        obj.notify(dictionary.get(obj.name, _TempObject.ignore))
    globals().update(dictionary)


def __getattr__(name):
    if (v := globals().get(name, _TempObject.ignore)) is _TempObject.ignore:
        _TempObject.objects.append(obj := _TempObject(name))
        return obj
    return v
