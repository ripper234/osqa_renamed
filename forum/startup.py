import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),'markdownext'))


from forum.modules import get_modules_script, ui

get_modules_script('settings')
get_modules_script('startup')


import forum.badges
import forum.subscriptions


from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from forum.templatetags.extra_tags import get_score_badge


ui.register_multi(ui.HEADER_LINKS,
            ui.UiLinkObject(_('faq'), 'faq', weight=400),
            ui.UiLinkObject(_('about'), 'about', weight=300),

            ui.UiLinkObject(
                    text=lambda c: c['request'].user.is_authenticated() and _('logout') or _('login'),
                    url=lambda c: c['request'].user.is_authenticated() and reverse('logout') or reverse('auth_signin'),
                    weight=200),

            ui.UiLinkObject(
                    user_level=ui.LoggedInUserUiObject(),
                    text=lambda c: c['request'].user.username,
                    url=lambda c: c['request'].user.get_profile_url(),
                    post_code=lambda c: get_score_badge(c['request'].user),
                    weight=100),

            ui.UiLinkObject(
                    user_level=ui.SuperuserUiObject(),
                    text=_('administration'),
                    url=lambda c: reverse('admin_index'),
                    weight=0)

)


ui.register_multi(ui.PAGE_TOP_TABS,
            ui.UiTopPageTabObject('questions', _('questions'), 'questions', weight=0),
            ui.UiTopPageTabObject('tags', _('tags'), 'tags', weight=100),
            ui.UiTopPageTabObject('users', _('users'), 'users', weight=200),
            ui.UiTopPageTabObject('badges', _('badges'), 'badges', weight=300),
            ui.UiTopPageTabObject('unanswered', _('unanswered questions'), 'unanswered', weight=400),
)

#register.header_link(lambda c: (_('faq'), reverse('faq')))



