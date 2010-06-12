from django.http import HttpResponse
from django.template.loader import render_to_string

from forum import settings

class HttpResponseServiceUnavailable(HttpResponse):
    def __init__(self, message):
        super(HttpResponseServiceUnavailable, self).__init__(content=render_to_string('503.html', {
        'message': message,
        'app_logo': settings.APP_LOGO,
        'app_title': settings.APP_TITLE
        }), status=503)

class HttpResponseUnauthorized(HttpResponse):
    pass