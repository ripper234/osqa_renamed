# encoding:utf-8
import datetime
import logging
from urllib import unquote
from forum import settings as django_settings
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponsePermanentRedirect
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.template import RequestContext
from django import template
from django.utils.html import *
from django.utils import simplejson
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from django.utils.datastructures import SortedDict
from django.views.decorators.cache import cache_page
from django.utils.http import urlquote  as django_urlquote
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe

from forum.utils.html import sanitize_html, hyperlink
from forum.utils.diff import textDiff as htmldiff
from forum.utils import pagination
from forum.forms import *
from forum.models import *
from forum.forms import get_next_url
from forum.actions import QuestionViewAction
from forum.http_responses import HttpResponseUnauthorized
from forum.feed import RssQuestionFeed
import decorators

# used in index page
#refactor - move these numbers somewhere?
INDEX_PAGE_SIZE = 30
INDEX_AWARD_SIZE = 15
INDEX_TAGS_SIZE = 25
# used in tags list
DEFAULT_PAGE_SIZE = 60
# used in questions
QUESTIONS_PAGE_SIZE = 30
# used in answers
ANSWERS_PAGE_SIZE = 10

class QuestionListPaginatorContext(pagination.PaginatorContext):
    def __init__(self):
        super (QuestionListPaginatorContext, self).__init__('QUESTIONS_LIST', sort_methods=(
            (_('active'), pagination.SimpleSort(_('active'), '-last_activity_at', _("most recently updated questions"))),
            (_('newest'), pagination.SimpleSort(_('newest'), '-added_at', _("most recently asked questions"))),
            (_('hottest'), pagination.SimpleSort(_('hottest'), '-extra_count', _("hottest questions"))),
            (_('mostvoted'), pagination.SimpleSort(_('most voted'), '-score', _("most voted questions"))),
        ), pagesizes=(15, 30, 50))

def feed(request):
    return RssQuestionFeed(
                Question.objects.filter_state(deleted=False).order_by('-last_activity_at'),
                settings.APP_TITLE + _(' - ')+ _('latest questions'),
                settings.APP_DESCRIPTION,
                request)(request)


@decorators.render('index.html')
def index(request):
    return question_list(request,
                         Question.objects.all(),
                         sort=request.utils.set_sort_method('active'),
                         base_path=reverse('questions'),
                         feed_url=reverse('latest_questions_feed'))

@decorators.render('questions.html', 'unanswered', _('unanswered'), weight=400)
def unanswered(request):
    return question_list(request,
                         Question.objects.filter(extra_ref=None),
                         _('open questions without an accepted answer'),
                         request.utils.set_sort_method('active'),
                         None,
                         _("Unanswered Questions"))

@decorators.render('questions.html', 'questions', _('questions'), weight=0)
def questions(request):
    return question_list(request, Question.objects.all(), _('questions'), request.utils.set_sort_method('active'))

@decorators.render('questions.html')
def tag(request, tag):
    return question_list(request,
                         Question.objects.filter(tags__name=unquote(tag)),
                         mark_safe(_('questions tagged <span class="tag">%(tag)s</span>') % {'tag': tag}),
                         request.utils.set_sort_method('active'),
                         None,
                         mark_safe(_('Questions Tagged With %(tag)s') % {'tag': tag}),
                         False)

@decorators.render('questions.html', 'questions', tabbed=False)
def user_questions(request, mode, user, slug):
    user = get_object_or_404(User, id=user)

    if mode == _('asked-by'):
        questions = Question.objects.filter(author=user)
        description = _("Questions asked by %s")
    elif mode == _('answered-by'):
        questions = Question.objects.filter(children__author=user, children__node_type='answer').distinct()
        description = _("Questions answered by %s")
    elif mode == _('subscribed-by'):
        if not (request.user.is_superuser or request.user == user):
            return HttpResponseUnauthorized(request)
        questions = user.subscriptions

        if request.user == user:
            description = _("Questions you subscribed %s")
        else:
            description = _("Questions subscribed by %s")
    else:
        raise Http404


    return question_list(request, questions,
                         mark_safe(description % hyperlink(user.get_profile_url(), user.username)),
                         request.utils.set_sort_method('active'),
                         page_title=description % user.username)

def question_list(request, initial,
                  list_description=_('questions'),
                  sort=None,
                  base_path=None,
                  page_title=_("All Questions"),
                  allowIgnoreTags=True,
                  feed_url=None,
                  paginator_context=None):

    questions = initial.filter_state(deleted=False)

    if request.user.is_authenticated() and allowIgnoreTags:
        questions = questions.filter(~Q(tags__id__in = request.user.marked_tags.filter(user_selections__reason = 'bad')))

    if page_title is None:
        page_title = _("Questions")

    if request.GET.get('type', None) == 'rss':
        return RssQuestionFeed(questions, page_title, list_description, request)(request)

    keywords =  ""
    if request.GET.get("q"):
        keywords = request.GET.get("q").strip()

    answer_count = Answer.objects.filter_state(deleted=False).filter(parent__in=questions).count()
    answer_description = _("answers")

    if not feed_url:
        req_params = "&".join(["%s=%s" % (k, v) for k, v in request.GET.items() if not k in (_('page'), _('pagesize'), _('sort'))])
        if req_params:
            req_params = '&' + req_params

        feed_url = mark_safe(request.path + "?type=rss" + req_params)

    return pagination.paginated(request, 'questions', paginator_context or QuestionListPaginatorContext(), {
    "questions" : questions,
    "questions_count" : questions.count(),
    "answer_count" : answer_count,
    "keywords" : keywords,
    "list_description": list_description,
    "answer_description": answer_description,
    "base_path" : base_path,
    "page_title" : page_title,
    "tab" : "questions",
    'feed_url': feed_url,
    })


def search(request):
    if request.method == "GET" and "q" in request.GET:
        keywords = request.GET.get("q")
        search_type = request.GET.get("t")

        if not keywords:
            return HttpResponseRedirect(reverse(index))
        if search_type == 'tag':
            return HttpResponseRedirect(reverse('tags') + '?q=%s' % urlquote(keywords.strip()))
        elif search_type == "user":
            return HttpResponseRedirect(reverse('users') + '?q=%s' % urlquote(keywords.strip()))
        elif search_type == "question":
            return question_search(request, keywords)
    else:
        return render_to_response("search.html", context_instance=RequestContext(request))

@decorators.render('questions.html')
def question_search(request, keywords):
    can_rank, initial = Question.objects.search(keywords)

    if can_rank:
        paginator_context = QuestionListPaginatorContext()
        paginator_context.sort_methods[_('ranking')] = pagination.SimpleSort(_('ranking'), '-ranking', _("most relevant questions"))
    else:
        paginator_context = None

    return question_list(request, initial,
                         _("questions matching '%(keywords)s'") % {'keywords': keywords},
                         False,
                         "%s?t=question&q=%s" % (reverse('search'),django_urlquote(keywords)),
                         _("questions matching '%(keywords)s'") % {'keywords': keywords},
                         paginator_context=paginator_context)


@decorators.render('tags.html', 'tags', _('tags'), weight=100)
def tags(request):
    stag = ""
    is_paginated = True
    sortby = request.GET.get('sort', 'used')
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    if request.method == "GET":
        stag = request.GET.get("q", "").strip()
        if stag != '':
            objects_list = Paginator(Tag.active.filter(name__contains=stag), DEFAULT_PAGE_SIZE)
        else:
            if sortby == "name":
                objects_list = Paginator(Tag.active.order_by("name"), DEFAULT_PAGE_SIZE)
            else:
                objects_list = Paginator(Tag.active.order_by("-used_count"), DEFAULT_PAGE_SIZE)

    try:
        tags = objects_list.page(page)
    except (EmptyPage, InvalidPage):
        tags = objects_list.page(objects_list.num_pages)

    return {
        "tags" : tags,
        "stag" : stag,
        "tab_id" : sortby,
        "keywords" : stag,
        "context" : {
            'is_paginated' : is_paginated,
            'pages': objects_list.num_pages,
            'page': page,
            'has_previous': tags.has_previous(),
            'has_next': tags.has_next(),
            'previous': tags.previous_page_number(),
            'next': tags.next_page_number(),
            'base_url' : reverse('tags') + '?sort=%s&' % sortby
        }
    }

def get_answer_sort_order(request):
    view_dic = {"latest":"-added_at", "oldest":"added_at", "votes":"-score" }

    view_id = request.GET.get('sort', request.session.get('answer_sort_order', None))

    if view_id is None or not view_id in view_dic:
        view_id = "votes"

    if view_id != request.session.get('answer_sort_order', None):
        request.session['answer_sort_order'] = view_id

    return (view_id, view_dic[view_id])

def update_question_view_times(request, question):
    if not 'last_seen_in_question' in request.session:
        request.session['last_seen_in_question'] = {}

    last_seen = request.session['last_seen_in_question'].get(question.id, None)

    if (not last_seen) or last_seen < question.last_activity_at:
        QuestionViewAction(question, request.user, ip=request.META['REMOTE_ADDR']).save()
        request.session['last_seen_in_question'][question.id] = datetime.datetime.now()

    request.session['last_seen_in_question'][question.id] = datetime.datetime.now()

def match_question_slug(slug):
    slug_words = slug.split('-')
    qs = Question.objects.filter(title__istartswith=slug_words[0])

    for q in qs:
        if slug == urlquote(slugify(q.title)):
            return q

    return None

def question(request, id, slug):
    try:
        question = Question.objects.get(id=id)
    except:
        if slug:
            question = match_question_slug(slug)
            if question is not None:
                return HttpResponsePermanentRedirect(question.get_absolute_url())

        raise Http404()

    page = int(request.GET.get('page', 1))
    view_id, order_by = get_answer_sort_order(request)

    if question.nis.deleted and not request.user.can_view_deleted_post(question):
        raise Http404

    if request.POST:
        answer_form = AnswerForm(question, request.POST)
    else:
        answer_form = AnswerForm(question)

    answers = request.user.get_visible_answers(question)

    if answers is not None:
        answers = [a for a in answers.order_by("-marked", order_by)
                   if not a.nis.deleted or a.author == request.user]

    objects_list = Paginator(answers, ANSWERS_PAGE_SIZE)
    page_objects = objects_list.page(page)

    update_question_view_times(request, question)

    if request.user.is_authenticated():
        try:
            subscription = QuestionSubscription.objects.get(question=question, user=request.user)
        except:
            subscription = False
    else:
        subscription = False

    return render_to_response('question.html', {
    "question" : question,
    "answer" : answer_form,
    "answers" : page_objects.object_list,
    "tab_id" : view_id,
    "similar_questions" : question.get_related_questions(),
    "subscription": subscription,
    "context" : {
    'is_paginated' : True,
    'pages': objects_list.num_pages,
    'page': page,
    'has_previous': page_objects.has_previous(),
    'has_next': page_objects.has_next(),
    'previous': page_objects.previous_page_number(),
    'next': page_objects.next_page_number(),
    'base_url' : request.path + '?sort=%s&' % view_id,
    'extend_url' : "#sort-top"
    }
    }, context_instance=RequestContext(request))


REVISION_TEMPLATE = template.loader.get_template('node/revision.html')

def revisions(request, id):
    post = get_object_or_404(Node, id=id).leaf
    revisions = list(post.revisions.order_by('revised_at'))
    rev_ctx = []

    for i, revision in enumerate(revisions):
        rev_ctx.append(dict(inst=revision, html=template.loader.get_template('node/revision.html').render(template.Context({
        'title': revision.title,
        'html': revision.html,
        'tags': revision.tagname_list(),
        }))))

        if i > 0:
            rev_ctx[i]['diff'] = mark_safe(htmldiff(rev_ctx[i-1]['html'], rev_ctx[i]['html']))
        else:
            rev_ctx[i]['diff'] = mark_safe(rev_ctx[i]['html'])

        if not (revision.summary):
            rev_ctx[i]['summary'] = _('Revision n. %(rev_number)d') % {'rev_number': revision.revision}
        else:
            rev_ctx[i]['summary'] = revision.summary

    rev_ctx.reverse()

    return render_to_response('revisions.html', {
    'post': post,
    'revisions': rev_ctx,
    }, context_instance=RequestContext(request))



