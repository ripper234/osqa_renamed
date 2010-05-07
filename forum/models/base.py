import datetime
import re
from urllib import quote_plus, urlencode
from django.db import models, IntegrityError, connection, transaction
from django.utils.http import urlquote  as django_urlquote
from django.utils.html import strip_tags
from django.core.urlresolvers import reverse
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.template.defaultfilters import slugify
from django.db.models.signals import post_delete, post_save, pre_save, pre_delete
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.contrib.sitemaps import ping_google
import django.dispatch
from django.conf import settings
from forum import const
import logging

from forum.const import *

class LazyQueryList(object):
    def __init__(self, model, items):
        self.model = model
        self.items = items

    def __getitem__(self, k):
        return self.model.objects.get(id=self.items[k])

    def __iter__(self):
        for id in self.items:
            yield self.model.objects.get(id=id)

    def __len__(self):
        return len(self.items)

class CachedQuerySet(models.query.QuerySet):
    def lazy(self):
        if len(self.query.extra) == 0:
            return LazyQueryList(self.model, list(self.values_list('id', flat=True)))
        else:
            return self

from action import Action

class CachedManager(models.Manager):
    use_for_related_fields = True
    int_cache_re = re.compile('^_[\w_]+cache$')

    def get_query_set(self):
        return CachedQuerySet(self.model)

    def cache_obj(self, obj):
        int_cache_keys = [k for k in obj.__dict__.keys() if self.int_cache_re.match(k)]
        d = obj.__dict__
        for k in int_cache_keys:
            if not isinstance(obj.__dict__[k], Action):
                del obj.__dict__[k]

        cache.set(self.model.cache_key(obj.id), obj, 60 * 60)

    def get(self, *args, **kwargs):
        try:
            pk = [v for (k,v) in kwargs.items() if k in ('pk', 'pk__exact', 'id', 'id__exact'
                            ) or k.endswith('_ptr__pk') or k.endswith('_ptr__id')][0]
        except:
            pk = None

        if pk is not None:
            key = self.model.cache_key(pk)
            obj = cache.get(key)

            if obj is None:
                obj = super(CachedManager, self).get(*args, **kwargs)
                self.cache_obj(obj)
            else:
                d = obj.__dict__

            return obj
        
        return super(CachedManager, self).get(*args, **kwargs)

    def get_or_create(self, *args, **kwargs):
        try:
            return self.get(*args, **kwargs)
        except:
            return super(CachedManager, self).get_or_create(*args, **kwargs)


class DenormalizedField(object):
    def __init__(self, manager, **kwargs):
        self.manager = manager
        self.filter = kwargs

    def setup_class(self, cls, name):
        dict_name = '_%s_cache_' % name

        def getter(inst):
            val = inst.__dict__.get(dict_name, None)

            if val is None:
                val = getattr(inst, self.manager).filter(**self.filter).count()
                inst.__dict__[dict_name] = val
                inst.__class__.objects.cache_obj(inst)

            return val

        def reset_cache(inst):
            inst.__dict__.pop(dict_name, None)
            inst.__class__.objects.cache_obj(inst)

        cls.add_to_class(name, property(getter))
        cls.add_to_class("reset_%s_cache" % name, reset_cache)


class BaseMetaClass(models.Model.__metaclass__):
    to_denormalize = []

    def __new__(cls, *args, **kwargs):
        new_cls = super(BaseMetaClass, cls).__new__(cls, *args, **kwargs)

        BaseMetaClass.to_denormalize.extend(
            [(new_cls, name, field) for name, field in new_cls.__dict__.items() if isinstance(field, DenormalizedField)]
        )

        return new_cls

    @classmethod
    def setup_denormalizes(cls):
        for new_cls, name, field in BaseMetaClass.to_denormalize:
            field.setup_class(new_cls, name)


class BaseModel(models.Model):
    __metaclass__ = BaseMetaClass

    objects = CachedManager()

    class Meta:
        abstract = True
        app_label = 'forum'

    def __init__(self, *args, **kwargs):
        super(BaseModel, self).__init__(*args, **kwargs)
        self._original_state = dict([(k, v) for k,v in self.__dict__.items() if not k in kwargs])

    @classmethod
    def cache_key(cls, pk):
        return '%s.%s:%s' % (settings.APP_URL, cls.__name__, pk)

    def get_dirty_fields(self):
        missing = object()
        return dict([(k, self._original_state.get(k, None)) for k,v in self.__dict__.items()
                 if self._original_state.get(k, missing) == missing or self._original_state[k] != v])

    def save(self, *args, **kwargs):
        put_back = [k for k, v in self.__dict__.items() if isinstance(v, models.expressions.ExpressionNode)]
        super(BaseModel, self).save()

        if put_back:
            try:
                self.__dict__.update(
                    self.__class__.objects.filter(id=self.id).values(*put_back)[0]
                )
            except:
                logging.error("Unable to read %s from %s" % (", ".join(put_back), self.__class__.__name__))
                self.uncache()

        self._original_state = dict(self.__dict__)
        self.cache()

    def cache(self):
        self.__class__.objects.cache_obj(self)

    def uncache(self):
        cache.delete(self.cache_key(self.pk))

    def delete(self):
        self.uncache()
        super(BaseModel, self).delete()


class ActiveObjectManager(models.Manager):
    use_for_related_fields = True
    def get_query_set(self):
        return super(ActiveObjectManager, self).get_query_set().filter(canceled=False)

class UndeletedObjectManager(models.Manager):
    def get_query_set(self):
        return super(UndeletedObjectManager, self).get_query_set().filter(deleted=False)

class GenericContent(models.Model):
    content_type   = models.ForeignKey(ContentType)
    object_id      = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    class Meta:
        abstract = True
        app_label = 'forum'

class MetaContent(BaseModel):
    node = models.ForeignKey('Node', null=True, related_name='%(class)ss')

    def __init__(self, *args, **kwargs):
        if 'content_object' in kwargs:
            kwargs['node'] = kwargs['content_object']
            del kwargs['content_object']

        super (MetaContent, self).__init__(*args, **kwargs)
    
    @property
    def content_object(self):
        return self.node.leaf

    class Meta:
        abstract = True
        app_label = 'forum'

from user import User

class UserContent(models.Model):
    user = models.ForeignKey(User, related_name='%(class)ss')

    class Meta:
        abstract = True
        app_label = 'forum'


class DeletableContent(models.Model):
    deleted     = models.BooleanField(default=False)
    deleted_at  = models.DateTimeField(null=True, blank=True)
    deleted_by  = models.ForeignKey(User, null=True, blank=True, related_name='deleted_%(class)ss')

    active = UndeletedObjectManager()

    class Meta:
        abstract = True
        app_label = 'forum'

    def mark_deleted(self, user):
        if not self.deleted:
            self.deleted = True
            self.deleted_at = datetime.datetime.now()
            self.deleted_by = user
            self.save()
            return True
        else:
            return False

    def unmark_deleted(self):
        if self.deleted:
            self.deleted = False
            self.save()
            return True
        else:
            return False

mark_canceled = django.dispatch.Signal(providing_args=['instance'])

class CancelableContent(models.Model):
    canceled = models.BooleanField(default=False)

    def cancel(self):
        if not self.canceled:
            self.canceled = True
            self.save()
            mark_canceled.send(sender=self.__class__, instance=self)
            return True
            
        return False

    class Meta:
        abstract = True
        app_label = 'forum'


from node import Node, NodeRevision





