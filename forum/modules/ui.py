

class Registry(list):
    def add(self, register):
        for i, r in enumerate(self):
            if r.weight > register.weight:
                self.insert(i, register)
                return

        self.append(register)

"""Links next in the very top of the page"""
HEADER_LINKS = 'HEADER_LINKS'

"""The tabs next to the top of the page"""
PAGE_TOP_TABS = 'PAGE_TOP_TABS'


__CONTAINER = {
    HEADER_LINKS: Registry(),
    PAGE_TOP_TABS: Registry()
}


def register(registry, ui_object):
    if not registry in __CONTAINER:
        raise('unknown registry')

    __CONTAINER[registry].add(ui_object)

def register_multi(registry, *ui_objects):
    for ui_object in ui_objects:
        register(registry, ui_object)


def get_registry_by_name(name):
    name = name.upper()

    if not name in __CONTAINER:
        raise('unknown registry')

    return __CONTAINER[name]



from ui_objects import *

