import inspect

class DecoratableObject(object):
    def __init__(self, fn):
        self._callable = fn

    def decorate(self, fn, needs_origin):
        origin = self._callable

        if needs_origin:
            self._callable = lambda *args, **kwargs: fn(origin, *args, **kwargs)
        else:
            self._callable = lambda *args, **kwargs: fn(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self._callable(*args, **kwargs)


def decoratable(fn):
    return DecoratableObject(fn)

def decoratable_method(fn):
    obj = DecoratableObject(fn)
    def decorated(self, *args, **kwargs):
        return obj(self, *args, **kwargs)

    decorated.__obj = obj
    return decorated

decoratable.method = decoratable_method

def decorate(origin, needs_origin=True):
    if not isinstance(origin, DecoratableObject):
        if hasattr(origin, '__obj'):
            def decorator(fn):
                origin.__obj.decorate(fn, needs_origin)
                return origin
            return decorator

        raise Exception('Not an decoratable function: %s' % origin.name)

    def decorator(fn):
        origin.decorate(fn, needs_origin)
        return origin

    return decorator







