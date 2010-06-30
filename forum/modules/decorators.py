import inspect

class DecoratableObject(object):
    MODE_OVERRIDE = 0
    MODE_PARAMS = 1
    MODE_RESULT = 2

    def __init__(self, fn):
        a = inspect.getargspec(fn)
        self._callable = fn
        self._params_decoration = None
        self._result_decoration = None

    def _decorate(self, fn, needs_origin, method=False):
        origin = self._callable

        if needs_origin:
            if method:
                self._callable = lambda inst, *args, **kwargs: fn(inst, origin, *args, **kwargs)
            else:
                self._callable = lambda *args, **kwargs: fn(origin, *args, **kwargs)
        else:
            self._callable = fn

    def _decorate_params(self, fn):
        if not self._params_decoration:
            self._params_decoration = []

        self._params_decoration.append(fn)

    def _decorate_result(self, fn):
        if not self._result_decoration:
            self._result_decoration = []

        self._result_decoration.append(fn)

    def __call__(self, *args, **kwargs):
        if self._params_decoration:
            for dec in self._params_decoration:
                args, kwargs = dec(*args, **kwargs)

        res = self._callable(*args, **kwargs)

        if self._result_decoration:
            for dec in self._result_decoration:
                res = dec(res)

        return res


def _create_decorator(origin, needs_origin, mode, method=False):
    def decorator(fn):
        if mode == DecoratableObject.MODE_OVERRIDE:
            origin._decorate(fn, needs_origin, method=method)
        elif mode == DecoratableObject.MODE_PARAMS:
            origin._decorate_params(fn)
        elif mode == DecoratableObject.MODE_RESULT:
            origin._decorate_result(fn)

        return fn

    return decorator


def _decorate_method(origin, needs_origin, mode):
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

    return _create_decorator(decoratable, needs_origin, mode, method=True)

def _decorate_function(origin, needs_origin, mode):
    if not isinstance(origin, DecoratableObject):
        mod = inspect.getmodule(origin)

        name = origin.__name__
        origin = DecoratableObject(origin)
        setattr(mod, name, origin)

    return _create_decorator(origin, needs_origin, mode)


def decorate(origin, needs_origin=True, mode=DecoratableObject.MODE_OVERRIDE):
    if inspect.ismethod(origin):
        return _decorate_method(origin, needs_origin, mode)

    if inspect.isfunction(origin) or isinstance(origin, DecoratableObject):
        return _decorate_function(origin, needs_origin, mode)

    def decorator(fn):
        return fn

    return decorator


def _decorate_params(origin):
    return decorate(origin, mode=DecoratableObject.MODE_PARAMS)

decorate.params = _decorate_params

def _decorate_result(origin):
    return decorate(origin, mode=DecoratableObject.MODE_RESULT)

decorate.result = _decorate_result

def _decorate_with(fn):
    def decorator(origin):
        if not isinstance(origin, DecoratableObject):
            decoratable = DecoratableObject(origin)
        else:
            decoratable = origin

        decoratable._decorate(fn, True, False)
        return decoratable
    return decorator


decorate.withfn = _decorate_with