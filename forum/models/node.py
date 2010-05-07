from forum.akismet import *
from base import *
from tag import Tag

import markdown
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.html import strip_tags
from forum.utils.html import sanitize_html

class NodeContent(models.Model):
    title      = models.CharField(max_length=300)
    tagnames   = models.CharField(max_length=125)
    author     = models.ForeignKey(User, related_name='%(class)ss')
    body       = models.TextField()

    @property
    def user(self):
        return self.author

    @property
    def html(self):
        return self.as_markdown()

    def as_markdown(self, *extensions):
        return mark_safe(sanitize_html(markdown.markdown(self.body, extensions=extensions)))

    @property
    def headline(self):
        return self.title

    def tagname_list(self):
        if self.tagnames:
            return [name for name in self.tagnames.split(u' ')]
        else:
            return []

    def tagname_meta_generator(self):
        return u','.join([unicode(tag) for tag in self.tagname_list()])

    class Meta:
        abstract = True
        app_label = 'forum'

class NodeMetaClass(BaseMetaClass):
    types = {}

    def __new__(cls, *args, **kwargs):
        new_cls = super(NodeMetaClass, cls).__new__(cls, *args, **kwargs)

        if not new_cls._meta.abstract and new_cls.__name__ is not 'Node':
            NodeMetaClass.types[new_cls.get_type()] = new_cls

        return new_cls

    @classmethod
    def setup_relations(cls):
        for node_cls in NodeMetaClass.types.values():
            NodeMetaClass.setup_relation(node_cls)        

    @classmethod
    def setup_relation(cls, node_cls):
        name = node_cls.__name__.lower()

        def children(self):
            return node_cls.objects.filter(parent=self)

        def parent(self):
            p = self.__dict__.get('_%s_cache' % name, None)

            if p is None and (self.parent is not None) and self.parent.node_type == name:
                p = self.parent.leaf
                self.__dict__['_%s_cache' % name] = p

            return p

        Node.add_to_class(name + 's', property(children))
        Node.add_to_class(name, property(parent))


class NodeManager(CachedManager):
    use_for_related_fields = True

    def get_query_set(self):
        qs = super(NodeManager, self).get_query_set()

        if self.model is not Node:
            return qs.filter(node_type=self.model.get_type())
        else:
            return qs

    def get(self, *args, **kwargs):
        node = super(NodeManager, self).get(*args, **kwargs)
        cls = NodeMetaClass.types.get(node.node_type, None)

        if cls and node.__class__ is not cls:
            return node.leaf
        return node

    def get_for_types(self, types, *args, **kwargs):
        kwargs['node_type__in'] = [t.get_type() for t in types]
        return self.get(*args, **kwargs)


class Node(BaseModel, NodeContent):
    __metaclass__ = NodeMetaClass

    node_type            = models.CharField(max_length=16, default='node')
    parent               = models.ForeignKey('Node', related_name='children', null=True)
    abs_parent           = models.ForeignKey('Node', related_name='all_children', null=True)

    added_at             = models.DateTimeField(default=datetime.datetime.now)
    score                 = models.IntegerField(default=0)

    deleted               = models.ForeignKey('Action', null=True, unique=True, related_name="deleted_node")
    in_moderation         = models.ForeignKey('Action', null=True, unique=True, related_name="moderated_node")
    last_edited           = models.ForeignKey('Action', null=True, unique=True, related_name="edited_node")

    last_activity_by       = models.ForeignKey(User, null=True)
    last_activity_at       = models.DateTimeField(null=True, blank=True)

    tags                 = models.ManyToManyField('Tag', related_name='%(class)ss')
    active_revision       = models.OneToOneField('NodeRevision', related_name='active', null=True)

    extra_ref = models.ForeignKey('Node', null=True)
    extra_count = models.IntegerField(default=0)
    extra_action = models.ForeignKey('Action', null=True, related_name="extra_node")
    
    marked = models.BooleanField(default=False)
    wiki = models.BooleanField(default=False)

    comment_count = DenormalizedField("children", node_type="comment", canceled=False)
    flag_count = DenormalizedField("flags")

    friendly_name = _("post")

    objects = NodeManager()

    @classmethod
    def cache_key(cls, pk):
        return '%s.node:%s' % (settings.APP_URL, pk)

    @classmethod
    def get_type(cls):
        return cls.__name__.lower()

    @property
    def leaf(self):
        leaf_cls = NodeMetaClass.types.get(self.node_type, None)

        if leaf_cls is None:
            return self

        leaf = leaf_cls()
        leaf.__dict__ = self.__dict__
        return leaf

    @property    
    def absolute_parent(self):
        if not self.abs_parent_id:
            return self.leaf

        return self.abs_parent.leaf

    @property
    def summary(self):
        return strip_tags(self.html)[:300]

    def update_last_activity(self, user):
        self.last_activity_by = user
        self.last_activity_at = datetime.datetime.now()

        if self.parent:
            self.parent.update_last_activity(user)

    def _create_revision(self, user, number, **kwargs):
        revision = NodeRevision(author=user, revision=number, node=self, **kwargs)
        revision.save()
        return revision

    def create_revision(self, user, action=None, **kwargs):
        number = self.revisions.aggregate(last=models.Max('revision'))['last'] + 1
        revision = self._create_revision(user, number, **kwargs)
        self.activate_revision(user, revision, action)
        return revision

    def activate_revision(self, user, revision, action=None):
        self.title = revision.title
        self.tagnames = revision.tagnames
        self.body = revision.body

        self.active_revision = revision
        self.update_last_activity(user)

        if action:
            self.last_edited = action

        self.save()

    def get_tag_list_if_changed(self):
        dirty = self.get_dirty_fields()
        active_user = self.last_edited and self.last_edited.by or self.author

        if 'tagnames' in dirty:
            new_tags = self.tagname_list()
            old_tags = dirty['tagnames']

            if old_tags is None or not old_tags:
                old_tags = []
            else:
                old_tags = [name for name in dirty['tagnames'].split(u' ')]

            tag_list = []

            for name in new_tags:
                try:
                    tag = Tag.objects.get(name=name)
                except:
                    tag = Tag.objects.create(name=name, created_by=active_user or self.author)

                tag_list.append(tag)

                if not name in old_tags:
                    tag.used_count = tag.used_count + 1
                    if tag.deleted:
                        tag.unmark_deleted()
                    tag.save()

            for name in [n for n in old_tags if not n in new_tags]:
                tag = Tag.objects.get(name=name)
                tag.used_count = tag.used_count - 1
                if tag.used_count == 0:
                    tag.mark_deleted(active_user)
                tag.save()

            return tag_list

        return None

    def save(self, *args, **kwargs):
        if not self.id:
            self.node_type = self.get_type()
            super(BaseModel, self).save(*args, **kwargs)
            self.active_revision = self._create_revision(self.author, 1, title=self.title, tagnames=self.tagnames, body=self.body)
            self.update_last_activity(self.author)

        if self.parent_id and not self.abs_parent_id:
            self.abs_parent = self.parent.absolute_parent
        
        tags = self.get_tag_list_if_changed()
        super(Node, self).save(*args, **kwargs)
        if tags is not None: self.tags = tags

    @staticmethod
    def isSpam(comment, data):
        api = Akismet()

        if not api.key:
            return False
        else:
            if api.comment_check(comment, data):
                return True
            else:
                return False
        return data

    class Meta:
        app_label = 'forum'


class NodeRevision(BaseModel, NodeContent):
    node       = models.ForeignKey(Node, related_name='revisions')
    summary    = models.CharField(max_length=300)
    revision   = models.PositiveIntegerField()
    revised_at = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        unique_together = ('node', 'revision')
        app_label = 'forum'


