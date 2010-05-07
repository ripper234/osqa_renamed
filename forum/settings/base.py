import django.dispatch
from django.utils.encoding import force_unicode

class SettingSet(list):
    def __init__(self, name, title, description, weight=1000, markdown=False):
        self.name = name
        self.title = title
        self.description = description
        self.weight = weight
        self.markdown = markdown
        

class BaseSetting(object):
    @classmethod
    def add_to_class(cls, name):
        def wrapper(self, *args, **kwargs):
            return self.value.__getattribute__(name)(*args, **kwargs)

        setattr(cls, name, wrapper)

    def __init__(self, name, default, set=None, field_context=None):
        self.name = name
        self.default = default
        self.field_context = field_context or {}

        if set is not None:
            if not set.name in Setting.sets:
                Setting.sets[set.name] = set

            Setting.sets[set.name].append(self)

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return unicode(self.value)

    @property
    def value(self):
        from forum.models import KeyValue

        try:
            kv = KeyValue.objects.get(key=self.name)
        except:
            kv = KeyValue(key=self.name, value=self._parse(self.default))
            kv.save()

        return kv.value

    def set_value(self, new_value):
        new_value = self._parse(new_value)
        self.save(new_value)

    def save(self, value):
        from forum.models import KeyValue

        try:
            kv = KeyValue.objects.get(key=self.name)
        except:
            kv = KeyValue(key=self.name)

        kv.value = value
        kv.save()

    def to_default(self):
        self.set_value(self.default)

    def _parse(self, value):
        return value


class Setting(object):
    emulators = {}
    sets = {}

    def __new__(cls, name, default, set=None, field_context=None):
        deftype = type(default)

        if deftype in Setting.emulators:
            emul = Setting.emulators[deftype]
        else:
            emul = type(deftype.__name__ + cls.__name__, (BaseSetting,), {})
            fns = [n for n, f in [(p, getattr(deftype, p)) for p in dir(deftype) if not p in dir(cls)] if callable(f)]

            for n in fns:
               emul.add_to_class(n)

            Setting.emulators[deftype] = emul

        return emul(name, default, set, field_context)


