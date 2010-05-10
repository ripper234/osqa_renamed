from django.utils.translation import ugettext as _
from django.db.models import F
from forum.models.action import ActionProxy
from forum.models import Award
from forum import settings

class UserJoinsAction(ActionProxy):
    def repute_users(self):
        self.repute(self.user, int(settings.INITIAL_REP))

class EditProfileAction(ActionProxy):
    pass

class AwardAction(ActionProxy):
    def process_data(self, badge, trigger):
        self.__dict__['_badge'] = badge
        self.__dict__['_trigger'] = trigger

    def process_action(self):
        badge = self.__dict__['_badge']
        trigger = self.__dict__['_trigger']

        award = Award(user=self.user, badge=badge, trigger=trigger, action=self)
        if self.node:
            award.node = self.node

        award.save()
        award.badge.awarded_count = F('awarded_count') + 1
        award.badge.save()
        self.user.message_set.create(message=_("""Congratulations, you have received a badge '%(badge_name)s'
                                     Check out <a href=\"%(profile_url)s\">your profile</a>.""") %
                                     dict(badge_name=award.badge.name, profile_url=self.user.get_profile_url()))

    def cancel_action(self):
        award = self.award
        badge = award.badge
        badge.awarded_count = F('awarded_count') - 1
        badge.save()
        award.delete()

    @classmethod
    def get_for(cls, user, badge, node=False):
        try:
            if node is False:
                return Award.objects.get(user=user, badge=badge).action
            else:
                return Award.objects.get(user=user, node=node, badge=badge).action
        except:
            return None

    def describe(self, viewer=None):
        return _("%(user)s %(were_was)s awarded the %(badge_name)s badge") % {
            'user': self.hyperlink(self.user.get_profile_url(), self.friendly_username(viewer, self.user)),
            'were_was': self.viewer_or_user_verb(viewer, self.user, _('were'), _('was')),
            'badge_name': self.award.badge.name,
        }