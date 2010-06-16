import inspect

class DecoratableObject(object):
    def __init__(self, fn):
        self._callable = fn

    def _decorate(self, fn, needs_origin):
        origin = self._callable

        if needs_origin:
            self._callable = lambda *args, **kwargs: fn(origin, *args, **kwargs)
        else:
            self._callable = lambda *args, **kwargs: fn(*args, **kwargs)

    def _decorate_method(self, fn, needs_origin):
        origin = self._callable

        if needs_origin:
            self._callable = lambda inst, *args, **kwargs: fn(inst, origin, *args, **kwargs)
        else:
            self._callable = lambda inst, *args, **kwargs: fn(inst, *args, **kwargs)


    def __call__(self, *args, **kwargs):
        return self._callable(*args, **kwargs)


def _decorate_method(origin, needs_origin):
    if not hasattr(origin, '_decoratable_obj'):
        name = origin.__name__
        cls = origin.im_class

        decoratable = DecoratableObject(origin)

        def decoratable_method(self, *args, **kwargs):
            return decoratable(self, *args, **kwargs)

        decoratable_method._decoratable_obj = decoratable
        setattr(cls, name, decoratable_method)
    else:
        decoratable = origin._decoratable_obj

    def decorator(fn):
        decoratable._decorate_method(fn, needs_origin)

    return decorator

def _decorate_function(origin, needs_origin):
    if not isinstance(origin, DecoratableObject):
        mod = inspect.getmodule(origin)

        name = origin.__name__
        origin = DecoratableObject(origin)
        setattr(mod, name, DecoratableObject(origin))

    def decorator(fn):
        origin._decorate(fn, needs_origin)

    return decorator


def decorate(origin, needs_origin=True):
    if inspect.ismethod(origin):
        return _decorate_method(origin, needs_origin)

    if inspect.isfunction(origin):
        return _decorate_function(origin, needs_origin)