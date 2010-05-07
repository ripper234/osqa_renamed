from django.db import models
from django.core.cache import cache
from django.conf import settings
from django.utils.encoding import force_unicode

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps

from copy import deepcopy
from base64 import b64encode, b64decode
from zlib import compress, decompress


class PickledObject(str):
    pass

def dbsafe_encode(value, compress_object=True):
    if not compress_object:
        value = b64encode(dumps(deepcopy(value)))
    else:
        value = b64encode(compress(dumps(deepcopy(value))))
    return PickledObject(value)

def dbsafe_decode(value, compress_object=True):
    if not compress_object:
        value = loads(b64decode(value))
    else:
        value = loads(decompress(b64decode(value)))
    return value

class PickledObjectField(models.Field):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        self.compress = kwargs.pop('compress', True)
        self.protocol = kwargs.pop('protocol', 2)
        kwargs.setdefault('null', True)
        kwargs.setdefault('editable', False)
        super(PickledObjectField, self).__init__(*args, **kwargs)

    def get_default(self):
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default

        return super(PickledObjectField, self).get_default()

    def to_python(self, value):
        if value is not None:
            try:
                value = dbsafe_decode(value, self.compress)
            except:
                if isinstance(value, PickledObject):
                    raise
        return value

    def get_db_prep_value(self, value):
        if value is not None and not isinstance(value, PickledObject):
            value = force_unicode(dbsafe_encode(value, self.compress))
        return value

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

    def get_internal_type(self):
        return 'TextField'

    def get_db_prep_lookup(self, lookup_type, value):
        if lookup_type not in ['exact', 'in', 'isnull']:
            raise TypeError('Lookup type %s is not supported.' % lookup_type)
        return super(PickledObjectField, self).get_db_prep_lookup(lookup_type, value)


class KeyValueManager(models.Manager):

    def create_cache_key(self, key):
        return "%s:keyvalue:%s" % (settings.APP_URL, key)

    def save_to_cache(self, instance):
        cache.set(self.create_cache_key(instance.key), instance, 2592000)

    def remove_from_cache(self, instance):
        cache.delete(self.create_cache_key(instance.key))

    def get(self, **kwargs):
        if 'key' in kwargs:
            instance = cache.get(self.create_cache_key(kwargs['key']))

            if instance is None:
                instance = super(KeyValueManager, self).get(**kwargs)
                self.save_to_cache(instance)

            return instance

        else:
            return super(KeyValueManager, self).get(**kwargs)

class KeyValue(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = PickledObjectField()

    objects = KeyValueManager()

    class Meta:
        app_label = 'forum'

    def save(self, *args, **kwargs):
        super(KeyValue, self).save(*args, **kwargs)
        KeyValue.objects.save_to_cache(self)

    def delete(self):
        KeyValue.objects.remove_from_cache(self)
        super(KeyValue, self).delete()
