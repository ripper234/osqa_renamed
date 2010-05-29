from datetime import datetime, timedelta
import time

from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, Http404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.utils import simplejson
from django.db.models import Sum
from forum.settings.base import Setting
from forum.settings.forms import SettingsSetForm, MaintenanceModeForm

from forum.models import Question, Answer, User, Node, Action
from forum import settings

def super_user_required(fn):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.is_superuser:
            return fn(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    return wrapper

def admin_page(fn):
    @super_user_required
    def wrapper(request, *args, **kwargs):
        res = fn(request, *args, **kwargs)
        if isinstance(res, tuple):
            template, context = res
            context['basetemplate'] = settings.DJSTYLE_ADMIN_INTERFACE and "osqaadmin/djstyle_base.html" or "osqaadmin/base.html"
            context['allsets'] = Setting.sets
            context['othersets'] = sorted(
                    [s for s in Setting.sets.values() if not s.name in
                    ('basic', 'users', 'email', 'paths', 'extkeys', 'repgain', 'minrep', 'voting', 'badges', 'about', 'faq', 'sidebar',
                    'form', 'moderation')]
                    , lambda s1, s2: s1.weight - s2.weight)
            return render_to_response(template, context, context_instance=RequestContext(request))
        else:
            return res

    return wrapper

@admin_page
def dashboard(request):
    return ('osqaadmin/dashboard.html', {
        'settings_pack': unicode(settings.SETTINGS_PACK),
        'statistics': get_statistics(),
        'recent_activity': get_recent_activity(),
        'flagged_posts': get_flagged_posts(),
    })

@super_user_required
def interface_switch(request):
    if request.GET and request.GET.get('to', None) and request.GET['to'] in ('default', 'djstyle'):
        settings.DJSTYLE_ADMIN_INTERFACE.set_value(request.GET['to'] == 'djstyle')

    return HttpResponseRedirect(reverse('admin_index'))

@admin_page
def statistics(request):
    today = datetime.now()
    last_month = today - timedelta(days=30)

    last_month_questions = Question.objects.filter_state(deleted=False).filter(added_at__gt=last_month
                                                  ).order_by('added_at').values_list('added_at', flat=True)

    last_month_n_questions = Question.objects.filter_state(deleted=False).filter(added_at__lt=last_month).count()
    qgraph_data = simplejson.dumps([
            (time.mktime(d.timetuple()) * 1000, i + last_month_n_questions)
            for i, d in enumerate(last_month_questions)
    ])

    last_month_users = User.objects.filter(date_joined__gt=last_month
                                                  ).order_by('date_joined').values_list('date_joined', flat=True)

    last_month_n_users = User.objects.filter(date_joined__lt=last_month).count()

    ugraph_data = simplejson.dumps([
            (time.mktime(d.timetuple()) * 1000, i + last_month_n_users)
            for i, d in enumerate(last_month_users)
    ])

    return 'osqaadmin/statistics.html', {
        'graphs': [
            {
                'id': 'questions_graph',
                'caption': _("Questions Graph"),
                'data': qgraph_data
            },{
                'id': 'userss_graph',
                'caption': _("Users Graph"),
                'data': ugraph_data
            }
        ]
    }


@admin_page
def settings_set(request, set_name):
    set = Setting.sets.get(set_name, None)

    if set is None:
        raise Http404

    if request.POST:
        form = SettingsSetForm(set, data=request.POST, files=request.FILES)

        if form.is_valid():
            form.save()
            request.user.message_set.create(message=_("'%s' settings saved succesfully") % set_name)

            if set_name in ('minrep', 'badges', 'repgain'):
                settings.SETTINGS_PACK.set_value("custom")

            return HttpResponseRedirect(reverse('admin_set', args=[set_name]))
    else:
        form = SettingsSetForm(set)

    return 'osqaadmin/set.html', {
        'form': form,
        'markdown': set.markdown,
    }

@super_user_required
def get_default(request, set_name, var_name):
    set = Setting.sets.get(set_name, None)
    if set is None: raise Http404

    setting = dict([(s.name, s) for s in set]).get(var_name, None)
    if setting is None: raise Http404

    setting.to_default()

    if request.is_ajax():
        return HttpResponse(setting.default)
    else:
        return HttpResponseRedirect(reverse('admin_set', kwargs={'set_name': set_name}))


def get_recent_activity():
    return Action.objects.order_by('-action_date')[0:30]

def get_flagged_posts():
    return Action.objects.filter(canceled=False, action_type="flag").order_by('-action_date')[0:30]

def get_statistics():
    return {
        'total_users': User.objects.all().count(),
        'users_last_24': User.objects.filter(date_joined__gt=(datetime.now() - timedelta(days=1))).count(),
        'total_questions': Question.objects.filter_state(deleted=False).count(),
        'questions_last_24': Question.objects.filter_state(deleted=False).filter(added_at__gt=(datetime.now() - timedelta(days=1))).count(),
        'total_answers': Answer.objects.filter_state(deleted=False).count(),
        'answers_last_24': Answer.objects.filter_state(deleted=False).filter(added_at__gt=(datetime.now() - timedelta(days=1))).count(),
    }

@super_user_required
def go_bootstrap(request):
    #todo: this is the quick and dirty way of implementing a bootstrap mode
    try:
        from forum_modules.default_badges import settings as dbsets
        dbsets.POPULAR_QUESTION_VIEWS.set_value(100)
        dbsets.NOTABLE_QUESTION_VIEWS.set_value(200)
        dbsets.FAMOUS_QUESTION_VIEWS.set_value(300)
        dbsets.NICE_ANSWER_VOTES_UP.set_value(2)
        dbsets.NICE_QUESTION_VOTES_UP.set_value(2)
        dbsets.GOOD_ANSWER_VOTES_UP.set_value(4)
        dbsets.GOOD_QUESTION_VOTES_UP.set_value(4)
        dbsets.GREAT_ANSWER_VOTES_UP.set_value(8)
        dbsets.GREAT_QUESTION_VOTES_UP.set_value(8)
        dbsets.FAVORITE_QUESTION_FAVS.set_value(1)
        dbsets.STELLAR_QUESTION_FAVS.set_value(3)
        dbsets.DISCIPLINED_MIN_SCORE.set_value(3)
        dbsets.PEER_PRESSURE_MAX_SCORE.set_value(-3)
        dbsets.CIVIC_DUTY_VOTES.set_value(15)
        dbsets.PUNDIT_COMMENT_COUNT.set_value(10)
        dbsets.SELF_LEARNER_UP_VOTES.set_value(2)
        dbsets.STRUNK_AND_WHITE_EDITS.set_value(10)
        dbsets.ENLIGHTENED_UP_VOTES.set_value(2)
        dbsets.GURU_UP_VOTES.set_value(4)
        dbsets.NECROMANCER_UP_VOTES.set_value(2)
        dbsets.NECROMANCER_DIF_DAYS.set_value(30)
        dbsets.TAXONOMIST_USE_COUNT.set_value(5)
    except:
        pass

    settings.REP_TO_VOTE_UP.set_value(0)
    settings.REP_TO_VOTE_DOWN.set_value(15)
    settings.REP_TO_FLAG.set_value(15)
    settings.REP_TO_COMMENT.set_value(0)
    settings.REP_TO_LIKE_COMMENT.set_value(0)
    settings.REP_TO_UPLOAD.set_value(0)
    settings.REP_TO_CREATE_TAGS.set_value(0)
    settings.REP_TO_CLOSE_OWN.set_value(60)
    settings.REP_TO_REOPEN_OWN.set_value(120)
    settings.REP_TO_RETAG.set_value(150)
    settings.REP_TO_EDIT_WIKI.set_value(200)
    settings.REP_TO_EDIT_OTHERS.set_value(400)
    settings.REP_TO_CLOSE_OTHERS.set_value(600)
    settings.REP_TO_DELETE_COMMENTS.set_value(400)
    settings.REP_TO_VIEW_FLAGS.set_value(30)

    settings.INITIAL_REP.set_value(1)
    settings.MAX_REP_BY_UPVOTE_DAY.set_value(300)
    settings.REP_GAIN_BY_UPVOTED.set_value(15)
    settings.REP_LOST_BY_DOWNVOTED.set_value(1)
    settings.REP_LOST_BY_DOWNVOTING.set_value(0)
    settings.REP_GAIN_BY_ACCEPTED.set_value(25)
    settings.REP_GAIN_BY_ACCEPTING.set_value(5)
    settings.REP_LOST_BY_FLAGGED.set_value(2)
    settings.REP_LOST_BY_FLAGGED_3_TIMES.set_value(30)
    settings.REP_LOST_BY_FLAGGED_5_TIMES.set_value(100)

    settings.SETTINGS_PACK.set_value("bootstrap")

    request.user.message_set.create(message=_('Bootstrap mode enabled'))
    return HttpResponseRedirect(reverse('admin_index'))

@super_user_required
def go_defaults(request):
    for setting in Setting.sets['badges']:
        setting.to_default()
    for setting in Setting.sets['minrep']:
        setting.to_default()
    for setting in Setting.sets['repgain']:
        setting.to_default()

    settings.SETTINGS_PACK.set_value("default")

    request.user.message_set.create(message=_('All values reverted to defaults'))
    return HttpResponseRedirect(reverse('admin_index'))


@super_user_required
def recalculate_denormalized(request):
    for n in Node.objects.all():
        n = n.leaf
        n.score = n.votes.aggregate(score=Sum('value'))['score']
        if not n.score: n.score = 0
        n.save()

    for u in User.objects.all():
        u.reputation = u.reputes.aggregate(reputation=Sum('value'))['reputation']
        u.save()

    request.user.message_set.create(message=_('All values recalculated'))
    return HttpResponseRedirect(reverse('admin_index'))

@admin_page
def maintenance(request):
    if request.POST:
        if 'close' in request.POST or 'adjust' in request.POST:
            form = MaintenanceModeForm(request.POST)

            if form.is_valid():
                settings.MAINTAINANCE_MODE.set_value({
                    'allow_ips': form.cleaned_data['ips'],
                    'message': form.cleaned_data['message']})

                if 'close' in request.POST:
                    message = _('Maintenance mode enabled')
                else:
                    message = _('Settings adjusted')

                request.user.message_set.create(message=message)

                return HttpResponseRedirect(reverse('admin_maintenance'))
        elif 'open' in request.POST:
            settings.MAINTAINANCE_MODE.set_value(None)
            request.user.message_set.create(message=_("Your site is now running normally"))
            return HttpResponseRedirect(reverse('admin_maintenance'))
    else:
        form = MaintenanceModeForm(initial={'ips': request.META['REMOTE_ADDR'],
                                            'message': _('Currently down for maintenance. We\'ll be back soon')})

    return ('osqaadmin/maintenance.html', {'form': form, 'in_maintenance': settings.MAINTAINANCE_MODE.value is not None})


@admin_page
def flagged_posts(request):
    return ('osqaadmin/flagged_posts.html', {
        'flagged_posts': get_flagged_posts(),
    })


