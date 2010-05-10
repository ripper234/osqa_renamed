from forms import CommaStringListWidget
from base import Setting, SettingSet
from django.utils.translation import ugettext as _

USERS_SET = SettingSet('users', _('Users settings'), _("General settings for the OSQA users."), 20)

EDITABLE_SCREEN_NAME = Setting('EDITABLE_SCREEN_NAME', False, USERS_SET, dict(
label = _("Editable screen name"),
help_text = _("Allow users to alter their screen name."),
required=False))

MIN_USERNAME_LENGTH = Setting('MIN_USERNAME_LENGTH', 3, USERS_SET, dict(
label = _("Minimum username length"),
help_text = _("The minimum length (in character) of a username.")))

RESERVED_USERNAMES = Setting('RESERVED_USERNAMES',
[_('fuck'), _('shit'), _('ass'), _('sex'), _('add'), _('edit'), _('save'), _('delete'), _('manage'), _('update'), _('remove'), _('new')]
, USERS_SET, dict(
label = _("Disabled usernames"),
help_text = _("A comma separated list of disabled usernames (usernames not allowed during a new user registration)."),
widget=CommaStringListWidget))

EMAIL_UNIQUE = Setting('EMAIL_UNIQUE', True, USERS_SET, dict(
label = _("Force unique email"),
help_text = _("Should each user have an unique email.")))

