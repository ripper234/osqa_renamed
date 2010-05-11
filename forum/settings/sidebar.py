from base import Setting, SettingSet
from django.forms.widgets import Textarea

SIDEBAR_SET = SettingSet('sidebar', 'Sidebar content', "Enter contents to display in the sidebar. You can use markdown and some basic html tags.", 10, True)

SIDEBAR_UPPER_SHOW = Setting('SIDEBAR_UPPER_SHOW', True, SIDEBAR_SET, dict(
label = "Show Upper Block",
help_text = "Check if your pages should display the upper sidebar block.",
required=False))


SIDEBAR_UPPER_TEXT = Setting('SIDEBAR_UPPER_TEXT',
u"""
## [Try WebFaction](http://www.webfaction.com?affiliate=osqa)

We recommend [**WebFaction**](http://www.webfaction.com?affiliate=osqa) \
for hosting OSQA. Their affordable, reliable servers have everything you need! \
[Step-by-step instructions...](http://wiki.osqa.net/display/docs/Installing+OSQA+on+WebFaction)
""", SIDEBAR_SET, dict(
label = "Upper Block Content",
help_text = " The upper sidebar block. ",
widget=Textarea(attrs={'rows': '10'})))


SIDEBAR_LOWER_SHOW = Setting('SIDEBAR_LOWER_SHOW', True, SIDEBAR_SET, dict(
label = "Show Lower Block",
help_text = "Check if your pages should display the lower sidebar block.",
required=False))

SIDEBAR_LOWER_TEXT = Setting('SIDEBAR_LOWER_TEXT',
u"""
## Learn more about OSQA

The [**OSQA website**](http://www.osqa.net/) and [**OSQA wiki**](http://wiki.osqa.net/) \
are also great resources to help you learn more about the OSQA open source Q&A system!
""", SIDEBAR_SET, dict(
label = "Lower Block Content",
help_text = " The lower sidebar block. ",
widget=Textarea(attrs={'rows': '10'})))