from forms import CommaStringListWidget
from django.forms import CheckboxSelectMultiple
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

SHOW_STATUS_DIAMONDS = Setting('SHOW_STATUS_DIAMONDS', True, USERS_SET, dict(
label=_("Show status diamonds"),
help_text = _("Show status \"diamonds\" next to moderators or superusers usernames."),
required=False,
))

EMAIL_UNIQUE = Setting('EMAIL_UNIQUE', True, USERS_SET, dict(
label = _("Force unique email"),
help_text = _("Should each user have an unique email.")))

REQUIRE_EMAIL_VALIDATION_TO = Setting('REQUIRE_EMAIL_VALIDATION_TO', [], USERS_SET, dict(
label = _("Require email validation to..."),
help_text = _("Which actions in this site, users without a valid email will be prevented from doing."),
widget=CheckboxSelectMultiple,
choices=(("ask", _("ask questions")), ("answer", _("provide answers")), ("comment", _("make comments")), ("flag", _("report posts"))),
required=False,
))

DONT_NOTIFY_UNVALIDATED = Setting('DONT_NOTIFY_UNVALIDATED', True, USERS_SET, dict(
label = _("Don't notify to invalid emails"),
help_text = _("Do not notify users with unvalidated emails."),
required=False))

HOLD_PENDING_POSTS_MINUTES = Setting('HOLD_PENDING_POSTS_MINUTES', 120, USERS_SET, dict(
label=_("Hold pending posts for X minutes"),
help_text=_("How much time in minutes a post should be kept in session until the user logs in or validates the email.")
))

WARN_PENDING_POSTS_MINUTES = Setting('WARN_PENDING_POSTS_MINUTES', 15, USERS_SET, dict(
label=_("Warn about pending posts afer X minutes"),
help_text=_("How much time in minutes a user that just logged in or validated his email should be warned about a pending post instead of publishing it automatically.")
))

