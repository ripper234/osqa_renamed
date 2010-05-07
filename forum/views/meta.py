from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from forum.forms import FeedbackForm
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.db.models import Count
from forum.utils.forms import get_next_url
from forum.models import Badge, Award, User
from forum.badges.base import BadgesMeta
from forum import settings
from forum.utils.mail import send_email
from forum.settings.settingsmarkdown import SettingsExtension, markdown
import re

def favicon(request):
    return HttpResponseRedirect(str(settings.APP_FAVICON))

def about(request):
    return render_to_response('about.html', {'text': settings.ABOUT_PAGE_TEXT.value }, context_instance=RequestContext(request))

def faq(request):
    md = markdown.Markdown([SettingsExtension({})])
    text = md.convert(settings.FAQ_PAGE_TEXT.value)

    return render_to_response('faq.html', {'text' : text}, context_instance=RequestContext(request))

def feedback(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            context = {'user': request.user}

            if not request.user.is_authenticated:
                context['email'] = form.cleaned_data.get('email',None)
            context['message'] = form.cleaned_data['message']
            context['name'] = form.cleaned_data.get('name',None)

            recipients = [(adm.username, adm.email) for adm in User.objects.filter(is_superuser=True)]

            send_email(settings.EMAIL_SUBJECT_PREFIX + _("Feedback message from %(site_name)s") % {'site_name': settings.APP_SHORT_NAME},
                       recipients, "notifications/feedback.html", context)
            
            msg = _('Thanks for the feedback!')
            request.user.message_set.create(message=msg)
            return HttpResponseRedirect(get_next_url(request))
    else:
        form = FeedbackForm(initial={'next':get_next_url(request)})

    return render_to_response('feedback.html', {'form': form}, context_instance=RequestContext(request))
feedback.CANCEL_MESSAGE=_('We look forward to hearing your feedback! Please, give it next time :)')

def privacy(request):
    return render_to_response('privacy.html', context_instance=RequestContext(request))

def logout(request):
    return render_to_response('logout.html', {
        'next' : get_next_url(request),
    }, context_instance=RequestContext(request))

def badges(request):
    badges = [b.ondb for b in sorted(BadgesMeta.by_id.values(), lambda b1, b2: cmp(b1.name, b2.name))]
    
    if request.user.is_authenticated():
        my_badges = Award.objects.filter(user=request.user).values('badge_id').distinct()
    else:
        my_badges = []

    return render_to_response('badges.html', {
        'badges' : badges,
        'mybadges' : my_badges,
        'feedback_faq_url' : reverse('feedback'),
    }, context_instance=RequestContext(request))

def badge(request, id, slug):
    badge = Badge.objects.get(id=id)
    awards = Award.objects.filter(badge=badge).annotate(count=Count('user')).distinct('user').order_by('-count')

    return render_to_response('badge.html', {
        'awards' : awards,
        'badge' : badge,
    }, context_instance=RequestContext(request))

