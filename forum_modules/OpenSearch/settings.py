from forum.settings.base import Setting, SettingSet
from django.forms.widgets import Textarea
from forum import settings as django_settings

OPEN_SEARCH_SET = SettingSet('OpenSearch', 'OpenSearch', "Set up the open_search.xml file.", 3000)

OPEN_SEARCH_FILE = Setting('OPEN_SEARCH_FILE',
("""
<?xml version="1.0" encoding="UTF-8"?>
 <OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
   <ShortName>%s Web Search</ShortName>
   <Description>Use %s to search the Web.</Description>
   <Tags>%s</Tags>
   <Url type="application/rss+xml"
        template="%s/?q={searchTerms}&pw={startPage?}"/>
 </OpenSearchDescription>
""" % (django_settings.APP_SHORT_NAME, django_settings.APP_URL, django_settings.APP_KEYWORDS, django_settings.APP_URL)),
OPEN_SEARCH_SET,
dict(label = "open_search.xml file",
     help_text = "The open_search.xml file.",
     widget=Textarea(attrs={'rows': '20', 'cols' : '70'})))