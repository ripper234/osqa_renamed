from django.conf.urls.defaults import *
from django.http import  HttpResponse
import settings

urlpatterns = patterns('',
    (r'^open_search.xml$',  lambda r: HttpResponse(settings.OPEN_SEARCH_FILE.value)),
)
