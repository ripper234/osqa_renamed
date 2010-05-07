from django.utils.translation import ugettext as _
from utils import PickledObjectField
from threading import Thread
from base import *
import re

class ActionManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        qs = super(ActionManager, self).get_query_set().filter(canceled=False)

        if self.model is not Action:
            return qs.filter(action_type=self.model.get_type())
        else:
            return qs

    def get(self, *args, **kwargs):
        action = super(ActionManager, self).get(*args, **kwargs)
        if self.model == Action:
            return action.leaf()
        return action

    def get_for_types(self, types, *args, **kwargs):
        kwargs['action_type__in'] = [t.get_type() for t in types]
        return self.get(*args, **kwargs)

        

class Action(models.Model):
    user = models.ForeignKey('User', related_name="actions")
    ip   = models.CharField(max_length=16)
    node = models.ForeignKey('Node', null=True, related_name="actions")
    action_type = models.CharField(max_length=16)
    action_date = models.DateTimeField(default=datetime.datetime.now)

    extra = PickledObjectField()

    canceled = models.BooleanField(default=False)
    canceled_by = models.ForeignKey('User', null=True, related_name="canceled_actions")
    canceled_at = models.DateTimeField(null=True)
    canceled_ip = models.CharField(max_length=16)

    hooks = {}

    objects = ActionManager()

    @property
    def at(self):
        return self.action_date

    @property
    def by(self):
        return self.user

    def repute_users(self):
        pass

    def process_data(self, **data):
        pass

    def process_action(self):
        pass

    def cancel_action(self):
        pass

    def describe(self, viewer=None):
        return ""

    def repute(self, user, value):
        repute = ActionRepute(action=self, user=user, value=value)
        repute.save()
        return repute

    def cancel_reputes(self):
        for repute in self.reputes.all():
            cancel = ActionRepute(action=self, user=repute.user, value=(-repute.value), by_canceled=True)
            cancel.save()

    def leaf(self):
        leaf_cls = ActionProxyMetaClass.types.get(self.action_type, None)

        if leaf_cls is None:
            return self

        leaf = leaf_cls()
        leaf.__dict__ = self.__dict__
        return leaf

    @classmethod
    def get_type(cls):
        return re.sub(r'action$', '', cls.__name__.lower())

    def save(self, data=None, *args, **kwargs):
        isnew = False

        if not self.id:
            self.action_type = self.__class__.get_type()
            isnew = True

        if data:
            self.process_data(**data)

        super(Action, self).save(*args, **kwargs)

        if isnew:
            if (self.node is None) or (not self.node.wiki):
                self.repute_users()
            self.process_action()
            self.trigger_hooks(True)

        return self

    def delete(self):
        self.cancel_action()
        super(Action, self).delete()

    def cancel(self, user=None, ip=None):
        if not self.canceled:
            self.canceled = True
            self.canceled_at = datetime.datetime.now()
            self.canceled_by = (user is None) and self.user or user
            if ip:
                self.canceled_ip = ip
            self.save()
            self.cancel_reputes()
            self.cancel_action()
            #self.trigger_hooks(False)

    @classmethod
    def get_current(cls, **kwargs):
        kwargs['canceled'] = False

        try:
            return cls.objects.get(**kwargs)
        except cls.MultipleObjectsReturned:
            logging.error("Got multiple values for action %s with args %s", cls.__name__,
                          ", ".join(["%s='%s'" % i for i in kwargs.items()]))
            raise
        except cls.DoesNotExist:
            return None

    @classmethod
    def hook(cls, fn):
        if not Action.hooks.get(cls, None):
            Action.hooks[cls] = []

        Action.hooks[cls].append(fn)

    def trigger_hooks(self, new=True):
        thread = Thread(target=trigger_hooks_threaded,  args=[self, Action.hooks, new])
        thread.setDaemon(True)
        thread.start()

    class Meta:
        app_label = 'forum'

def trigger_hooks_threaded(action, hooks, new):
    for cls, hooklist in hooks.items():
        if isinstance(action, cls):
            for hook in hooklist:
                try:
                    hook(action=action, new=new)
                except Exception, e:
                    logging.error("Error in %s hook: %s" % (cls.__name__, str(e)))

class ActionProxyMetaClass(models.Model.__metaclass__):
    types = {}

    def __new__(cls, *args, **kwargs):
        new_cls = super(ActionProxyMetaClass, cls).__new__(cls, *args, **kwargs)
        cls.types[new_cls.get_type()] = new_cls

        class Meta:
            proxy = True

        new_cls.Meta = Meta
        return new_cls

class ActionProxy(Action):
    __metaclass__ = ActionProxyMetaClass

    def friendly_username(self, viewer, user):
        return (viewer == user) and _('You') or user.username

    def friendly_ownername(self, owner, user):
        return (owner == user) and _('your') or user.username

    def hyperlink(self, url, title, **attrs):
        return '<a href="%s" %s>%s</a>' % (url, " ".join('%s="%s"' % i for i in attrs.items()), title)

    def describe_node(self, viewer, node):
        node_link = self.hyperlink(node.get_absolute_url(), node.headline)

        if node.parent:
            node_desc = _("on %(link)s") % {'link': node_link}
        else:
            node_desc = node_link

        return _("%(user)s %(node_name)s %(node_desc)s") % {
            'user': self.hyperlink(node.author.get_profile_url(), self.friendly_ownername(viewer, node.author)),
            'node_name': node.friendly_name, 'node_desc': node_desc,
        }
    
    class Meta:
        proxy = True

class DummyActionProxy(Action):
    __metaclass__ = ActionProxyMetaClass

    hooks = []

    def process_data(self, **data):
        pass

    def process_action(self):
        pass

    def save(self, data=None):
        self.process_action()

        if data:
            self.process_data(**data)

        for hook in self.__class__.hooks:
            hook(self, True)

    @classmethod
    def get_type(cls):
        return re.sub(r'action$', '', cls.__name__.lower())

    @classmethod
    def hook(cls, fn):
        cls.hooks.append(fn)



class ActionRepute(models.Model):
    action = models.ForeignKey(Action, related_name='reputes')
    date = models.DateTimeField(default=datetime.datetime.now)
    user = models.ForeignKey('User', related_name='reputes')
    value = models.IntegerField(default=0)
    by_canceled = models.BooleanField(default=False)

    @property
    def positive(self):
        if self.value > 0: return self.value
        return 0

    @property
    def negative(self):
        if self.value < 0: return self.value
        return 0

    def save(self, *args, **kwargs):
        super(ActionRepute, self).save(*args, **kwargs)
        self.user.reputation = models.F('reputation') + self.value
        self.user.save()

    def delete(self):
        self.user.reputation = models.F('reputation') - self.value
        self.user.save()
        super(ActionRepute, self).delete()

    class Meta:
        app_label = 'forum'

