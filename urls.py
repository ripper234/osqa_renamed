from django.conf.urls.defaults import *
from django.utils.translation import ugettext as _
from django.conf import settings

urlpatterns = patterns('',
    (r'^qa/', include('forum.urls')),
)

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^rosetta/', include('rosetta.urls')),
    )

