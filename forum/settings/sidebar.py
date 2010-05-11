from base import Setting, SettingSet
from django.forms.widgets import Textarea

SIDEBAR_SET = SettingSet('sidebar', 'Sidebar content', "Enter contents to display in the sidebar. You can use markdown and some basic html tags.", 1000, True)

SIDEBAR_UPPER_SHOW = Setting('SIDEBAR_UPPER_SHOW', False, SIDEBAR_SET, dict(
label = "Include Upper Sidebar Block",
help_text = "Check if your pages should include the upper sidebar block.",
required=False))


SIDEBAR_UPPER_TEXT = Setting('SIDEBAR_UPPER_TEXT',
u"""
## Host your own OSQA at WebFaction

We recommend WebFaction for hosting OSQA. Their affordable,
reliable servers have everything you need!
""", SIDEBAR_SET, dict(
label = "Sidebar (Upper)",
help_text = " The upper sidebar block. ",
widget=Textarea(attrs={'rows': '10'})))


SIDEBAR_LOWER_SHOW = Setting('SIDEBAR_LOWER_SHOW', False, SIDEBAR_SET, dict(
label = "Include Lower Sidebar Block",
help_text = "Check if your pages should include the lower sidebar block.",
required=False))


SIDEBAR_LOWER_TEXT = Setting('SIDEBAR_LOWER_TEXT',
u"""
## Learn more about OSQA

The OSQA website and wiki are also great resources to help you
learn more about the OSQA open source Q&A system!
""", SIDEBAR_SET, dict(
label = "Sidebar (Lower)",
help_text = " The lower sidebar block. ",
widget=Textarea(attrs={'rows': '10'})))