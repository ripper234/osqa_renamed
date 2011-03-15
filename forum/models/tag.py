import datetime
from base import *

from django.utils.translation import ugettext as _

class ActiveTagManager(models.Manager):
    def get_query_set(self):
        qs = super(ActiveTagManager, self).get_query_set().exclude(used_count__lt=1)

        CurrentUserHolder = None

        # We try to import the moderation module and if the import is successful we make the filtration
        try:
            moderation_import = 'from %s.moderation.startup import CurrentUserHolder' % MODULES_PACKAGE
            exec moderation_import

            moderation_enabled= True
        except:
            moderation_enabled = False

        # If the moderation module has been enabled we make the filtration
        if CurrentUserHolder is not None and moderation_enabled:
            user = CurrentUserHolder.user

            try:
                filter_content = not user.is_staff and not user.is_superuser
            except:
                filter_content = True

            if filter_content:
                moderation_import = 'from %s.moderation.hooks import get_tag_ids' % MODULES_PACKAGE
                exec moderation_import
                qs = qs.exclude(id__in=get_tag_ids('deleted')).exclude(id__in=get_tag_ids('rejected')).exclude(
                    id__in=get_tag_ids('in_moderation')
                )

        return qs

class Tag(BaseModel):
    name            = models.CharField(max_length=255, unique=True)
    created_by      = models.ForeignKey(User, related_name='created_tags')
    created_at      = models.DateTimeField(default=datetime.datetime.now, blank=True, null=True)
    marked_by       = models.ManyToManyField(User, related_name="marked_tags", through="MarkedTag")
    # Denormalised data
    used_count = models.PositiveIntegerField(default=0)

    active = ActiveTagManager()
    objects = ActiveTagManager()

    class Meta:
        ordering = ('-used_count', 'name')
        app_label = 'forum'

    def __unicode__(self):
        return u'%s' % self.name

    def add_to_usage_count(self, value):
        if self.used_count + value < 0:
            self.used_count = 0
        else:
            self.used_count = models.F('used_count') + value

    @models.permalink
    def get_absolute_url(self):
        return ('tag_questions', (), {'tag': self.name})

class MarkedTag(models.Model):
    TAG_MARK_REASONS = (('good', _('interesting')), ('bad', _('ignored')))
    tag = models.ForeignKey(Tag, related_name='user_selections')
    user = models.ForeignKey(User, related_name='tag_selections')
    reason = models.CharField(max_length=16, choices=TAG_MARK_REASONS)

    class Meta:
        app_label = 'forum'

