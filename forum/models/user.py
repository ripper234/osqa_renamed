from base import *
from forum import const
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User as DjangoUser, AnonymousUser as DjangoAnonymousUser
from django.db.models import Q
try:
    from hashlib import md5
except:
    from md5 import new as md5

import string
from random import Random

from django.utils.translation import ugettext as _
import django.dispatch


QUESTIONS_PER_PAGE_CHOICES = (
   (10, u'10'),
   (30, u'30'),
   (50, u'50'),
)

class UserManager(CachedManager):
    def get_site_owner(self):
        return self.all().order_by('date_joined')[0]

class AnonymousUser(DjangoAnonymousUser):
    def get_visible_answers(self, question):
        return question.answers.filter(deleted=None)

    def can_view_deleted_post(self, post):
        return False

    def can_vote_up(self):
        return False

    def can_vote_down(self):
        return False

    def can_flag_offensive(self, post=None):
        return False

    def can_view_offensive_flags(self, post=None):
        return False

    def can_comment(self, post):
        return False

    def can_like_comment(self, comment):
        return False

    def can_edit_comment(self, comment):
        return False

    def can_delete_comment(self, comment):
        return False

    def can_accept_answer(self, answer):
        return False

    def can_edit_post(self, post):
        return False

    def can_retag_questions(self):
        return False

    def can_close_question(self, question):
        return False

    def can_reopen_question(self, question):
        return False

    def can_delete_post(self, post):
        return False

    def can_upload_files(self):
        return False

def true_if_is_super_or_staff(fn):
    def decorated(self, *args, **kwargs):
        return self.is_superuser or self.is_staff or fn(self, *args, **kwargs)
    return decorated

class User(BaseModel, DjangoUser):
    is_approved = models.BooleanField(default=False)
    email_isvalid = models.BooleanField(default=False)

    reputation = models.PositiveIntegerField(default=0)
    gold = models.PositiveIntegerField(default=0)
    silver = models.PositiveIntegerField(default=0)
    bronze = models.PositiveIntegerField(default=0)
    
    last_seen = models.DateTimeField(default=datetime.datetime.now)
    real_name = models.CharField(max_length=100, blank=True)
    website = models.URLField(max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    about = models.TextField(blank=True)

    subscriptions = models.ManyToManyField('Node', related_name='subscribers', through='QuestionSubscription')

    vote_up_count = DenormalizedField("actions", canceled=False, action_type="voteup")
    vote_down_count = DenormalizedField("actions", canceled=False, action_type="votedown")
   
    objects = UserManager()

    @property
    def gravatar(self):
        return md5(self.email).hexdigest()

    def save(self, *args, **kwargs):
        if self.reputation < 0:
            self.reputation = 0

        new = not bool(self.id)

        super(User, self).save(*args, **kwargs)

        if new:
            sub_settings = SubscriptionSettings(user=self)
            sub_settings.save()

    def get_absolute_url(self):
        return self.get_profile_url()

    def get_messages(self):
        messages = []
        for m in self.message_set.all():
            messages.append(m.message)
        return messages

    def delete_messages(self):
        self.message_set.all().delete()

    def get_profile_url(self):
        return "/%s%d/%s" % (_('users/'), self.id, slugify(self.username))

    def get_profile_link(self):
        profile_link = u'<a href="%s">%s</a>' % (self.get_profile_url(),self.username)
        return mark_safe(profile_link)

    def get_visible_answers(self, question):
        return question.answers.filter(deleted=None, in_moderation=None)

    def get_vote_count_today(self):
        today = datetime.date.today()
        return self.actions.filter(canceled=False, action_type__in=("voteup", "votedown"),
                action_date__range=(today - datetime.timedelta(days=1), today)).count()

    def get_reputation_by_upvoted_today(self):
        today = datetime.datetime.now()
        sum = self.reputes.filter(
                models.Q(reputation_type=TYPE_REPUTATION_GAIN_BY_UPVOTED) |
                models.Q(reputation_type=TYPE_REPUTATION_LOST_BY_UPVOTE_CANCELED),
                reputed_at__range=(today - datetime.timedelta(days=1), today)).aggregate(models.Sum('value'))

        if sum.get('value__sum', None) is not None: return sum['value__sum']
        return 0

    def get_flagged_items_count_today(self):
        today = datetime.date.today()
        return self.actions.filter(canceled=False, action_type="flag",
                action_date__range=(today - datetime.timedelta(days=1), today)).count()

    @true_if_is_super_or_staff
    def can_view_deleted_post(self, post):
        return post.author == self

    @true_if_is_super_or_staff
    def can_vote_up(self):
        return self.reputation >= int(settings.REP_TO_VOTE_UP)

    @true_if_is_super_or_staff
    def can_vote_down(self):
        return self.reputation >= int(settings.REP_TO_VOTE_DOWN)

    def can_flag_offensive(self, post=None):
        if post is not None and post.author == self:
            return False
        return self.is_superuser or self.is_staff or self.reputation >= int(settings.REP_TO_FLAG)

    @true_if_is_super_or_staff
    def can_view_offensive_flags(self, post=None):
        if post is not None and post.author == self:
            return True
        return self.reputation >= int(settings.REP_TO_VIEW_FLAGS)

    @true_if_is_super_or_staff
    def can_comment(self, post):
        return self == post.author or self.reputation >= int(settings.REP_TO_COMMENT
        ) or (post.__class__.__name__ == "Answer" and self == post.question.author)

    @true_if_is_super_or_staff
    def can_like_comment(self, comment):
        return self != comment.author and (self.reputation >= int(settings.REP_TO_LIKE_COMMENT))

    @true_if_is_super_or_staff
    def can_edit_comment(self, comment):
        return (comment.author == self and comment.added_at >= datetime.datetime.now() - datetime.timedelta(minutes=60)
        ) or self.is_superuser

    @true_if_is_super_or_staff
    def can_delete_comment(self, comment):
        return self == comment.author or self.reputation >= int(settings.REP_TO_DELETE_COMMENTS)

    @true_if_is_super_or_staff
    def can_accept_answer(self, answer):
        return self == answer.question.author

    @true_if_is_super_or_staff
    def can_edit_post(self, post):
        return self == post.author or self.reputation >= int(settings.REP_TO_EDIT_OTHERS
        ) or (post.wiki and self.reputation >= int(settings.REP_TO_EDIT_WIKI))

    @true_if_is_super_or_staff
    def can_retag_questions(self):
        return self.reputation >= int(settings.REP_TO_RETAG)

    @true_if_is_super_or_staff
    def can_close_question(self, question):
        return (self == question.author and self.reputation >= int(settings.REP_TO_CLOSE_OWN)
        ) or self.reputation >= int(settings.REP_TO_CLOSE_OTHERS)

    @true_if_is_super_or_staff
    def can_reopen_question(self, question):
        return self == question.author and self.reputation >= settings.REP_TO_REOPEN_OWN

    @true_if_is_super_or_staff
    def can_delete_post(self, post):
        if post.node_type == "comment":
            return self.can_delete_comment(post)
            
        return (self == post.author and (post.__class__.__name__ == "Answer" or
            not post.answers.exclude(author=self).count()))

    @true_if_is_super_or_staff
    def can_upload_files(self):
        return self.reputation >= int(settings.REP_TO_UPLOAD)

    class Meta:
        app_label = 'forum'

class SubscriptionSettings(models.Model):
    user = models.OneToOneField(User, related_name='subscription_settings')

    enable_notifications = models.BooleanField(default=True)

    #notify if
    member_joins = models.CharField(max_length=1, default='n', choices=const.NOTIFICATION_CHOICES)
    new_question = models.CharField(max_length=1, default='d', choices=const.NOTIFICATION_CHOICES)
    new_question_watched_tags = models.CharField(max_length=1, default='i', choices=const.NOTIFICATION_CHOICES)
    subscribed_questions = models.CharField(max_length=1, default='i', choices=const.NOTIFICATION_CHOICES)
    
    #auto_subscribe_to
    all_questions = models.BooleanField(default=False)
    all_questions_watched_tags = models.BooleanField(default=False)
    questions_asked = models.BooleanField(default=True)
    questions_answered = models.BooleanField(default=True)
    questions_commented = models.BooleanField(default=False)
    questions_viewed = models.BooleanField(default=False)

    #notify activity on subscribed
    notify_answers = models.BooleanField(default=True)
    notify_reply_to_comments = models.BooleanField(default=True)
    notify_comments_own_post = models.BooleanField(default=True)
    notify_comments = models.BooleanField(default=False)
    notify_accepted = models.BooleanField(default=False)

    class Meta:
        app_label = 'forum'

from forum.utils.time import one_day_from_now

class ValidationHashManager(models.Manager):
    def _generate_md5_hash(self, user, type, hash_data, seed):
        return md5("%s%s%s%s" % (seed, "".join(map(str, hash_data)), user.id, type)).hexdigest()

    def create_new(self, user, type, hash_data=[], expiration=None):
        seed = ''.join(Random().sample(string.letters+string.digits, 12))
        hash = self._generate_md5_hash(user, type, hash_data, seed)

        obj = ValidationHash(hash_code=hash, seed=seed, user=user, type=type)

        if expiration is not None:
            obj.expiration = expiration

        try:
            obj.save()
        except:
            return None
            
        return obj

    def validate(self, hash, user, type, hash_data=[]):
        try:
            obj = self.get(hash_code=hash)
        except:
            return False

        if obj.type != type:
            return False

        if obj.user != user:
            return False

        valid = (obj.hash_code == self._generate_md5_hash(obj.user, type, hash_data, obj.seed))

        if valid:
            if obj.expiration < datetime.datetime.now():
                obj.delete()
                return False
            else:
                obj.delete()
                return True

        return False

class ValidationHash(models.Model):
    hash_code = models.CharField(max_length=255,unique=True)
    seed = models.CharField(max_length=12)
    expiration = models.DateTimeField(default=one_day_from_now)
    type = models.CharField(max_length=12)
    user = models.ForeignKey(User)

    objects = ValidationHashManager()

    class Meta:
        unique_together = ('user', 'type')
        app_label = 'forum'

    def __str__(self):
        return self.hash_code

class AuthKeyUserAssociation(models.Model):
    key = models.CharField(max_length=255,null=False,unique=True)
    provider = models.CharField(max_length=64)
    user = models.ForeignKey(User, related_name="auth_keys")
    added_at = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        app_label = 'forum'
