"""
I don't like the multiprocessing.Value() interface – it's a little shallow and not very easy to port to
The abstraction here adds automatic I/O locking, a simpler way to handle the datatypes, and support for most common operations and type conversions
Containers and Strings are not supported whatsoever, but new simple primitives can be subclassed at the bottom with relative ease; just find the relevant ctype and copy from above

Basic interface
s = SharedObject()
s.set(x) OR s.value = x
s.get() OR s.value

The lock can be accessed manually with s.lock
The C-object itself can be accessed with s.cobj
There is no reason to access the interval Value()
"""
from multiprocessing import Value
import ctypes

class SharedObject:
    """
    This is a wrapper for Value() that implements lots of ease-of-port features and allows for subclassing into "types"
    Value() itself is a function that generates an object which cannot be inherited easily – hence, a wrapper is used
    """
    NULL = object()
    def __init__(self, type_, value, lock=True):
        self.type = type_
        if value != self.NULL:
            self._cobj = Value(type_, value, lock=lock)
        else:
            self._cobj = Value(type_, lock=lock)

    def __repr__(self):
        return "<Shared %s=%s object at %s>" % (self.__class__.__name__, self.value, hex(id(self)))

    @property
    def lock(self):
        return self._cobj.get_lock()

    @property
    def cobj(self):
        return self._cobj.get_obj()

    @property
    def value(self):
        return self._cobj.value
    @value.setter
    def value(self, other):
        with self.lock:
            self._cobj.value = other

    def set(self, v):
        self.value = v
        return v
    def get(self):
        return self.value

    def __bool__(self):
        return bool(self.value)
    def __str__(self):
        return str(self.value)
    def __int__(self):
        return int(self.value)
    def __float__(self):
        return float(self.value)
    def __long__(self):
        return self.value.__long__()
    def __abs__(self):
        return abs(self.value)

    def __neg__(self):
        return -self.value
    def __pos__(self):
        return +self.value

    def __add__(self, other):
        return self.value + other
    def __sub__(self, other):
        return - self.value + other
    def __mul__(self, other):
        return self.value * other
    def __truediv__(self, other):
        return self.value / other
    def __floordiv__(self, other):
        return self.value // other
    def __pow__(self, power):
        return self.value ** power

    __radd__ = __add__
    __rsub__ = __sub__
    __rmul__ = __mul__

    def __coerce__(self, other):
        return self, type(other)(self.value)

    def __lt__(self, other):
        return self.value < other
    def __gt__(self, other):
        return self.value > other
    def __le__(self, other):
        return self.value <= other
    def __ge__(self, other):
        return self.value >= other
    def __eq__(self, other):
        return self.value == other
    def __ne__(self, other):
        return self.value != other

    def __iadd__(self, other):
        with self.lock:
            self.value += other
        return self
    def __isub__(self, other):
        with self.lock:
            self.value -= other
        return self
    def __imul__(self, other):
        with self.lock:
            self.value *= other
        return self
    def __idiv__(self, other):
        with self.lock:
            self.value /= other
        return self

    def __index__(self):
        return self.__int__()
    def __floor__(self):
        return self.value // 1
    def __ceil__(self):
        return self.value // 1 + 1



class Bool(SharedObject):
    def __init__(self, value=False):
        super().__init__(ctypes.c_bool, bool(value), lock=True)

class Float(SharedObject):
    def __init__(self, value=0.):
        super().__init__(ctypes.c_float, float(value), lock=True)

class Int(SharedObject):
    def __init__(self, value=0):
        super().__init__(ctypes.c_int, int(value), lock=True)

class Char(SharedObject):
    def __init__(self, value=chr(0)):
        super().__init__(ctypes.c_char, str(value), lock=True)

class Null(SharedObject):
    def __init__(self):
        super().__init__(ctypes.c_void_p, self.NULL, lock=True)


if __name__ == "__main__":
    v = Null()
    print(v)
