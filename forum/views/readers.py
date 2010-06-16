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

from forum.utils.html import sanitize_html
from forum.utils.diff import textDiff as htmldiff
from forum.forms import *
from forum.models import *
from forum.forms import get_next_url
from forum.actions import QuestionViewAction
from forum.modules.decorators import decoratable
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

@decorators.render('index.html')
def index(request):
    return question_list(request,
                         Question.objects.all(),
                         sort=request.utils.set_sort_method('active'),
                         base_path=reverse('questions'))

@decorators.render('questions.html', 'unanswered')
def unanswered(request):
    return question_list(request,
                         Question.objects.filter(extra_ref=None),
                         _('open questions without an accepted answer'),
                         request.utils.set_sort_method('active'),
                         None,
                         _("Unanswered Questions"))

@decorators.render('questions.html', 'questions')
def questions(request):
    return question_list(request, Question.objects.all(), _('questions'), request.utils.set_sort_method('active'))

@decorators.render('questions.html')
def tag(request, tag):
    return question_list(request,
                         Question.objects.filter(tags__name=unquote(tag)),
                         mark_safe(_('questions tagged <span class="tag">%(tag)s</span>') % {'tag': tag}),
                         request.utils.set_sort_method('active'),
                         None,
                         mark_safe(_('Questions Tagged With <span class="tag">%(tag)s</span>') % {'tag': tag}),
                         False)

@decorators.list('questions', QUESTIONS_PAGE_SIZE)
def question_list(request, initial,
                  list_description=_('questions'),
                  sort=None,
                  base_path=None,
                  page_title=_("All Questions"),
                  allowIgnoreTags=True):

    questions = initial.filter_state(deleted=False)

    if request.user.is_authenticated() and allowIgnoreTags:
        questions = questions.filter(~Q(tags__id__in = request.user.marked_tags.filter(user_selections__reason = 'bad'))
                                     )

    if sort is not False:
        if sort is None:
            sort = request.utils.sort_method('latest')
        else:
            request.utils.set_sort_method(sort)

        view_dic = {"latest":"-added_at", "active":"-last_activity_at", "hottest":"-extra_count", "mostvoted":"-score" }

        questions=questions.order_by(view_dic.get(sort, '-added_at'))

    if page_title is None:
        page_title = _("Questions")

    keywords =  ""
    if request.GET.get("q"):
        keywords = request.GET.get("q").strip()

    answer_count = Answer.objects.filter_state(deleted=False).filter(parent__in=questions).count()
    answer_description = _("answers")

    return {
    "questions" : questions,
    "questions_count" : questions.count(),
    "answer_count" : answer_count,
    "keywords" : keywords,
    #"tags_autocomplete" : _get_tags_cache_json(),
    "list_description": list_description,
    "answer_description": answer_description,
    "base_path" : base_path,
    "page_title" : page_title,
    "tab" : "questions",
    }


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
    initial = Question.objects.search(keywords)

    return question_list(request, initial,
                         _("questions matching '%(keywords)s'") % {'keywords': keywords},
                         False,
                         "%s?t=question&q=%s" % (reverse('search'),django_urlquote(keywords)),
                         _("questions matching '%(keywords)s'") % {'keywords': keywords})


def tags(request):#view showing a listing of available tags - plain list
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

    return render_to_response('tags.html', {
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
    }, context_instance=RequestContext(request))

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
        rev_ctx.append(dict(inst=revision, html=REVISION_TEMPLATE.render(template.Context({
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

    return render_to_response('revisions.html', {
    'post': post,
    'revisions': rev_ctx,
    }, context_instance=RequestContext(request))



