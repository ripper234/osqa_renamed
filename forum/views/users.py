from django.contrib.auth.decorators import login_required
from forum.models import User
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.template.defaultfilters import slugify
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, Http404
from django.utils.translation import ugettext as _
from django.utils.http import urlquote_plus
from django.utils.html import strip_tags
from django.utils import simplejson
from django.core.urlresolvers import reverse
from forum.forms import *
from forum.utils.html import sanitize_html
from datetime import date
import decorators
from forum.actions import EditProfileAction, FavoriteAction

import time

USERS_PAGE_SIZE = 35# refactor - move to some constants file

def users(request):
    is_paginated = True
    sortby = request.GET.get('sort', 'reputation')
    suser = request.REQUEST.get('q',  "")
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    if suser == "":
        if sortby == "newest":
            objects_list = Paginator(User.objects.all().order_by('-date_joined'), USERS_PAGE_SIZE)
        elif sortby == "last":
            objects_list = Paginator(User.objects.all().order_by('date_joined'), USERS_PAGE_SIZE)
        elif sortby == "user":
            objects_list = Paginator(User.objects.all().order_by('username'), USERS_PAGE_SIZE)
        # default
        else:
            objects_list = Paginator(User.objects.all().order_by('-reputation'), USERS_PAGE_SIZE)
        base_url = reverse('users') + '?sort=%s&' % sortby
    else:
        sortby = "reputation"
        objects_list = Paginator(User.objects.filter(username__icontains=suser).order_by('-reputation'), USERS_PAGE_SIZE)
        base_url = reverse('users') + '?name=%s&sort=%s&' % (suser, sortby)

    try:
        users = objects_list.page(page)
    except (EmptyPage, InvalidPage):
        users = objects_list.page(objects_list.num_pages)

    return render_to_response('users/users.html', {
                                "users" : users,
                                "suser" : suser,
                                "keywords" : suser,
                                "tab_id" : sortby,
                                "context" : {
                                    'is_paginated' : is_paginated,
                                    'pages': objects_list.num_pages,
                                    'page': page,
                                    'has_previous': users.has_previous(),
                                    'has_next': users.has_next(),
                                    'previous': users.previous_page_number(),
                                    'next': users.next_page_number(),
                                    'base_url' : base_url
                                }

                                }, context_instance=RequestContext(request))

def set_new_email(user, new_email, nomessage=False):
    if new_email != user.email:
        user.email = new_email
        user.email_isvalid = False
        user.save()
        #if settings.EMAIL_VALIDATION == 'on':
        #    send_new_email_key(user,nomessage=nomessage)    

@login_required
def edit_user(request, id):
    user = get_object_or_404(User, id=id)
    if request.user != user:
        raise Http404
    if request.method == "POST":
        form = EditUserForm(user, request.POST)
        if form.is_valid():
            new_email = sanitize_html(form.cleaned_data['email'])

            set_new_email(user, new_email)

            #user.username = sanitize_html(form.cleaned_data['username'])
            user.real_name = sanitize_html(form.cleaned_data['realname'])
            user.website = sanitize_html(form.cleaned_data['website'])
            user.location = sanitize_html(form.cleaned_data['city'])
            user.date_of_birth = sanitize_html(form.cleaned_data['birthday'])
            if user.date_of_birth == "None":
                user.date_of_birth = '1900-01-01'
            user.about = sanitize_html(form.cleaned_data['about'])

            user.save()
            EditProfileAction(user=user, ip=request.META['REMOTE_ADDR']).save()

            return HttpResponseRedirect(user.get_profile_url())
    else:
        form = EditUserForm(user)
    return render_to_response('users/edit.html', {
                                                'form' : form,
                                                'gravatar_faq_url' : reverse('faq') + '#gravatar',
                                    }, context_instance=RequestContext(request))



def user_view(template, tab_name, tab_description, page_title, private=False):
    def decorator(fn):
        def decorated(request, id, slug=None):
            user = get_object_or_404(User, id=id)
            if private and not user == request.user:
                return HttpResponseForbidden()
            context = fn(request, user)
            context.update({
                "tab_name" : tab_name,
                "tab_description" : tab_description,
                "page_title" : page_title,
            })
            return render_to_response(template, context, context_instance=RequestContext(request))
        return decorated
    return decorator


@user_view('users/stats.html', 'stats', _('user profile'), _('user profile overview'))
def user_stats(request, user):
    questions = Question.objects.filter(author=user, deleted=None).order_by('-added_at')
    answers = Answer.objects.filter(author=user, deleted=None).order_by('-added_at')

    up_votes = user.vote_up_count
    down_votes = user.vote_down_count
    votes_today = user.get_vote_count_today()
    votes_total = int(settings.MAX_VOTES_PER_DAY)

    user_tags = Tag.objects.filter(Q(nodes__author=user) | Q(nodes__children__author=user)) \
        .annotate(user_tag_usage_count=Count('name')).order_by('-user_tag_usage_count')

    awards = [(Badge.objects.get(id=b['id']), b['count']) for b in
            Badge.objects.filter(awards__user=user).values('id').annotate(count=Count('cls')).order_by('-count')]

    return {
            "view_user" : user,
            "questions" : questions,
            "answers" : answers,
            "up_votes" : up_votes,
            "down_votes" : down_votes,
            "total_votes": up_votes + down_votes,
            "votes_today_left": votes_total-votes_today,
            "votes_total_per_day": votes_total,
            "user_tags" : user_tags[:50],
            "awards": awards,
            "total_awards" : len(awards),
        }

@user_view('users/recent.html', 'recent', _('recent user activity'), _('profile - recent activity'))
def user_recent(request, user):
    activities = user.actions.exclude(action_type__in=("voteup", "votedown", "voteupcomment", "flag")).order_by('-action_date')[:USERS_PAGE_SIZE]

    return {"view_user" : user, "activities" : activities}


@user_view('users/votes.html', 'votes', _('user vote record'), _('profile - votes'), True)
def user_votes(request, user):
    votes = user.votes.filter(node__deleted=None).order_by('-voted_at')[:USERS_PAGE_SIZE]

    return {"view_user" : user, "votes" : votes}


@user_view('users/reputation.html', 'reputation', _('user reputation in the community'), _('profile - user reputation'))
def user_reputation(request, user):
    rep = list(user.reputes.order_by('date'))
    values = [r.value for r in rep]
    redux = lambda x, y: x+y     

    graph_data = simplejson.dumps([
            (time.mktime(rep[i].date.timetuple()) * 1000, reduce(redux, values[:i], 0))
            for i in range(len(values))
    ])

    return {"view_user": user, "reputation": reversed(rep), "graph_data": graph_data}

@user_view('users/questions.html', 'favorites', _('favorite questions'),  _('profile - favorite questions'))
def user_favorites(request, user):
    favorites = FavoriteAction.objects.filter(user=user)

    return {"favorites" : favorites, "view_user" : user}

@user_view('users/subscriptions.html', 'subscriptions', _('subscription settings'), _('profile - subscriptions'), True)
def user_subscriptions(request, user):
    if request.method == 'POST':
        form = SubscriptionSettingsForm(request.POST)

        if 'notswitch' in request.POST:
            user.subscription_settings.enable_notifications = not user.subscription_settings.enable_notifications
            user.subscription_settings.save()

            if user.subscription_settings.enable_notifications:
                request.user.message_set.create(message=_('Notifications are now enabled'))
            else:
                request.user.message_set.create(message=_('Notifications are now disabled'))
        else:
            form.is_valid()
            for k,v in form.cleaned_data.items():
                setattr(user.subscription_settings, k, v)

            user.subscription_settings.save()
            request.user.message_set.create(message=_('New subscription settings are now saved'))
    else:
        form = SubscriptionSettingsForm(user.subscription_settings.__dict__)

    notificatons_on = user.subscription_settings.enable_notifications

    return {'view_user':user, 'notificatons_on': notificatons_on, 'form':form}

@login_required
def account_settings(request):
    logging.debug('')
    msg = request.GET.get('msg', '')
    is_openid = False

    return render_to_response('account_settings.html', {
        'msg': msg,
        'is_openid': is_openid
        }, context_instance=RequestContext(request))

