from forum.settings import MAINTAINANCE_MODE, APP_LOGO, APP_TITLE
from django.http import HttpResponseGone
from django.template.loader import render_to_string


class RequestUtils(object):
    def __init__(self):
        self.request = None

    def set_sort_method(self, sort):
        self.request.session['questions_sort_method'] = sort

    def sort_method(self, default):
        sort = self.request.REQUEST.get('sort', None)
        if sort is None:
            return self.request.session.get('questions_sort_method', default)
        else:
            self.set_sort_method(sort)
            return sort

    def page_size(self, default):
        pagesize = self.request.REQUEST.get('pagesize', None)
        if pagesize is None:
            return int(self.request.session.get('questions_pagesize', default))
        else:
            self.request.session['questions_pagesize'] = pagesize
            return int(pagesize)

    def process_request(self, request):
        if MAINTAINANCE_MODE.value is not None and isinstance(MAINTAINANCE_MODE.value.get('allow_ips', None), list):
            ip = request.META['REMOTE_ADDR']

            if not ip in MAINTAINANCE_MODE.value['allow_ips']:
                return HttpResponseGone(render_to_string('410.html', {
                    'message': MAINTAINANCE_MODE.value.get('message', ''),
                    'app_logo': APP_LOGO,
                    'app_title': APP_TITLE
                }))

        self.request = request
        request.utils = self
        return None