import os
import types
import logging

from forum.utils.mixed import Proxy

MODULES_PACKAGE = 'forum_modules'

MODULE_LIST = []


def init_modules_engine(site_src_root, disabled_modules):
    modules_folder = os.path.join(site_src_root, MODULES_PACKAGE)

    MODULE_LIST.extend(filter(lambda m: getattr(m, 'CAN_USE', True), [
            __import__('forum_modules.%s' % f, globals(), locals(), ['forum_modules'])
            for f in os.listdir(modules_folder)
            if os.path.isdir(os.path.join(modules_folder, f)) and
               os.path.exists(os.path.join(modules_folder, "%s/__init__.py" % f)) and
               not f in disabled_modules
    ]))

    get_modules_folder.value = modules_folder

def get_modules_folder():
    return get_modules_folder.value

def get_modules_script(script_name):
    all = []

    for m in MODULE_LIST:
        if hasattr(m, script_name):
            all.append(getattr(m, script_name))
            continue

        try:
            all.append(__import__('%s.%s' % (m.__name__, script_name), globals(), locals(), [m.__name__]))
        except ImportError, e:
            #print repr(type(e)) + m.__name__ + ":" + str(e)
            pass
        except:
            import traceback
            msg = "Error importing %s from module %s: \n %s" % (
                script_name, m, traceback.format_exc()
            )
            logging.error(msg)

    return all

def get_modules_script_implementations(script_name, impl_class):
    scripts = get_modules_script(script_name)
    all_impls = {}

    for script in scripts:
        all_impls.update(dict([
            (n, i) for (n, i) in [(n, getattr(script, n)) for n in dir(script)]
            if isinstance(i, impl_class)
        ]))

    return all_impls

def get_modules_script_classes(script_name, base_class):
    scripts = get_modules_script(script_name)
    all_classes = {}

    for script in scripts:
        all_classes.update(dict([
            (n, c) for (n, c) in [(n, getattr(script, n)) for n in dir(script)]
            if isinstance(c, (type, types.ClassType)) and issubclass(c, base_class)
        ]))

    return all_classes

def get_all_handlers(name):
     handler_files = get_modules_script('handlers')

     return [
        h for h in [
            getattr(f, name) for f in handler_files
            if hasattr(f, name)
        ]

        if callable(h)
     ]

def call_all_handlers(name, *args, **kwargs):
    all = get_all_handlers(name)

    ret = []

    for handler in all:
        ret.append(handler(*args, **kwargs))

    return ret

def get_handler(name, default):
    all = get_all_handlers(name)
    return len(all) and all[0] or default

from decorators import decorate, ReturnImediatelyException
