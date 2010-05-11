from django.utils.translation import ugettext as _
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.shortcuts import render_to_response
from forum.modules.decorators import decorate
from forum import views
from lib.akismet import Akismet
from forum.settings import APP_URL, OSQA_VERSION, REP_TO_FOR_NO_SPAM_CHECK
from forum.models.user import User

import settings


def check_spam(param, comment_type):
    def wrapper(origin, request, *args, **kwargs):
        if request.POST and request.POST.get(param, None) and settings.WORDPRESS_API_KEY:
            comment = request.POST[param]
            user = request.user

            data = {
                "user_ip":request.META["REMOTE_ADDR"],
                "user_agent":request.environ['HTTP_USER_AGENT'],
                "comment_type": comment_type,
                "comment":comment
            }

            if user.is_authenticated():
                data.update({
                    "comment_author":request.user.username,
                    "comment_author_email":request.user.email,
                    "comment_author_url":request.user.website,    
                })

            api = Akismet(settings.WORDPRESS_API_KEY, APP_URL, "OSQA/%s" % OSQA_VERSION)
            if not user.is_authenticated() or (user.reputation < settings.REP_TO_FOR_NO_SPAM_CHECK and not user.is_staff and not user.is_superuser):
                if api.comment_check(comment, data):
                    if request.is_ajax():
                        response = {
                            'success': False,
                            'error_message': _("Sorry, but akismet thinks your %s is spam.") % comment_type
                        }
                        return HttpResponse(simplejson.dumps(response), mimetype="application/json")
                    else:
                        return render_to_response('modules/akismet/foundspam.html', {
                            'action_name': comment_type
                        })
                    
        return origin(request, *args, **kwargs)
    return wrapper
            

decorate(views.writers.ask)(check_spam('text', _('question')))
decorate(views.writers.answer)(check_spam('text', _('answer')))
decorate(views.commands.comment)(check_spam('comment', _('comment')))


