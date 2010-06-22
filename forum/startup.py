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
from forum import settings


ui.register(ui.HEADER_LINKS,
            ui.Link(_('faq'), ui.Url('faq'), weight=400),
            ui.Link(_('about'), ui.Url('about'), weight=300),

            ui.Link(
                    text=lambda u, c: u.is_authenticated() and _('logout') or _('login'),
                    url=lambda u, c: u.is_authenticated() and reverse('logout') or reverse('auth_signin'),
                    weight=200),

            ui.Link(
                    visibility=ui.Visibility.AUTHENTICATED,
                    text=lambda u, c: u.username,
                    url=lambda u, c: u.get_profile_url(),
                    post_code=lambda u, c: get_score_badge(u),
                    weight=100),

            ui.Link(
                    visibility=ui.Visibility.SUPERUSER,
                    text=_('administration'),
                    url=lambda u, c: reverse('admin_index'),
                    weight=0)

)

class SupportLink(ui.Link):    
    def can_render(self, context):
        return bool(settings.SUPPORT_URL)


ui.register(ui.FOOTER_LINKS,
            ui.Link(
                    text=_('contact'),
                    url=lambda u, c: settings.CONTACT_URL and settings.CONTACT_URL or "%s?next=%s" % (reverse('feedback'), c['request'].path),
                    weight=400),
            SupportLink(_('support'), settings.SUPPORT_URL, attrs={'target': '_blank'}, weight=300),
            ui.Link(_('privacy'), ui.Url('privacy'), weight=200),
            ui.Link(_('faq'), ui.Url('faq'), weight=100),
            ui.Link(_('about'), ui.Url('about'), weight=0),
)





