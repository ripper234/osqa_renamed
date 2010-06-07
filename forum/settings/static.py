from base import Setting, SettingSet
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _

STATIC_PAGE_REGISTRY = Setting('STATIC_PAGE_REGISTRY', {})

CSS_SET = SettingSet('css', 'Custom CSS', "Define some custom css you can use to override the default css.", 2000)

USE_CUSTOM_CSS = Setting('USE_CUSTOM_CSS', False, CSS_SET, dict(
label = _("Use custom CSS"),
help_text = _("Do you want to use custom CSS."),
required=False))

CUSTOM_CSS = Setting('CUSTOM_CSS', '', CSS_SET, dict(
label = _("Custom CSS"),
help_text = _("Your custom CSS."),
widget=Textarea(attrs={'rows': '25'}),
required=False))

