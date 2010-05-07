# encoding:utf-8
import os.path
import time, datetime, random
import logging
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, Http404
from django.template import RequestContext
from django.utils.html import *
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied

from forum.actions import AskAction, AnswerAction, ReviseAction, RollbackAction, RetagAction
from forum.forms import *
from forum.models import *
from forum.const import *
from forum.utils.forms import get_next_url
from forum.views.commands import SpamNotAllowedException


def upload(request):#ajax upload file to a question or answer
    class FileTypeNotAllow(Exception):
        pass
    class FileSizeNotAllow(Exception):
        pass
    class UploadPermissionNotAuthorized(Exception):
        pass

    #<result><msg><![CDATA[%s]]></msg><error><![CDATA[%s]]></error><file_url>%s</file_url></result>
    xml_template = "<result><msg><![CDATA[%s]]></msg><error><![CDATA[%s]]></error><file_url>%s</file_url></result>"

    try:
        f = request.FILES['file-upload']
        # check upload permission
        if not request.user.can_upload_files():
            raise UploadPermissionNotAuthorized()

        # check file type
        file_name_suffix = os.path.splitext(f.name)[1].lower()

        if not file_name_suffix in ('.jpg', '.jpeg', '.gif', '.png', '.bmp', '.tiff', '.ico'):
            raise FileTypeNotAllow()

        storage = FileSystemStorage(str(settings.UPFILES_FOLDER), str(settings.UPFILES_ALIAS))
        new_file_name = storage.save(f.name, f)
        # check file size
        # byte
        size = storage.size(new_file_name)

        if size > float(settings.ALLOW_MAX_FILE_SIZE) * 1024 * 1024:
            storage.delete(new_file_name)
            raise FileSizeNotAllow()

        result = xml_template % ('Good', '', str(settings.UPFILES_ALIAS) + new_file_name)
    except UploadPermissionNotAuthorized:
        result = xml_template % ('', _('uploading images is limited to users with >60 reputation points'), '')
    except FileTypeNotAllow:
        result = xml_template % ('', _("allowed file types are 'jpg', 'jpeg', 'gif', 'bmp', 'png', 'tiff'"), '')
    except FileSizeNotAllow:
        result = xml_template % ('', _("maximum upload file size is %sM") % settings.ALLOW_MAX_FILE_SIZE, '')
    except Exception, e:
        result = xml_template % ('', _('Error uploading file. Please contact the site administrator. Thank you. %s' % e), '')

    return HttpResponse(result, mimetype="application/xml")


def ask(request):
    if request.method == "POST" and "text" in request.POST:
        form = AskForm(request.POST)
        if form.is_valid():
            if request.user.is_authenticated():
                data = {
                    "user_ip":request.META["REMOTE_ADDR"],
                    "user_agent":request.environ['HTTP_USER_AGENT'],
                    "comment_author":request.user.username,
                    "comment_author_email":request.user.email,
                    "comment_author_url":request.user.website,
                    "comment":request.POST['text']
                }
                if Node.isSpam(request.POST['text'], data):
                    raise SpamNotAllowedException("question")

                question = AskAction(user=request.user).save(data=form.cleaned_data).node
                return HttpResponseRedirect(question.get_absolute_url())
            else:
                return HttpResponseRedirect(reverse('auth_action_signin', kwargs={'action': 'newquestion'}))
    elif request.method == "POST" and "go" in request.POST:
        form = AskForm({'title': request.POST['q']})
    else:
        form = AskForm()

    #tags = _get_tags_cache_json()
    return render_to_response('ask.html', {
        'form' : form,
        #'tags' : tags,
        'email_validation_faq_url':reverse('faq') + '#validate',
        }, context_instance=RequestContext(request))

@login_required
def edit_question(request, id):
    question = get_object_or_404(Question, id=id)
    if question.deleted and not request.user.can_view_deleted_post(question):
        raise Http404
    if request.user.can_edit_post(question):
        return _edit_question(request, question)
    elif request.user.can_retag_questions():
        return _retag_question(request, question)
    else:
        raise Http404

def _retag_question(request, question):
    if request.method == 'POST':
        form = RetagQuestionForm(question, request.POST)
        if form.is_valid():
            if form.has_changed():
                RetagAction(user=request.user, node=question).save(data=dict(tagnames=form.cleaned_data['tags']))

            return HttpResponseRedirect(question.get_absolute_url())
    else:
        form = RetagQuestionForm(question)
    return render_to_response('question_retag.html', {
        'question': question,
        'form' : form,
        #'tags' : _get_tags_cache_json(),
    }, context_instance=RequestContext(request))

def _edit_question(request, question):
    if request.method == 'POST':
        revision_form = RevisionForm(question, data=request.POST)
        revision_form.is_valid()
        revision = question.revisions.get(revision=revision_form.cleaned_data['revision'])

        if 'select_revision' in request.POST:
            form = EditQuestionForm(question, revision)
        else:
            form = EditQuestionForm(question, revision, data=request.POST)

        if not 'select_revision' in request.POST and form.is_valid():
            if form.has_changed():
                ReviseAction(user=request.user, node=question).save(data=form.cleaned_data)
            else:
                if not revision == question.active_revision:
                    RollbackAction(user=request.user, node=question).save(data=dict(activate=revision))

            return HttpResponseRedirect(question.get_absolute_url())
    else:
        revision_form = RevisionForm(question)
        form = EditQuestionForm(question)

    return render_to_response('question_edit.html', {
        'question': question,
        'revision_form': revision_form,
        'form' : form,
        #'tags' : _get_tags_cache_json()
    }, context_instance=RequestContext(request))

@login_required
def edit_answer(request, id):
    answer = get_object_or_404(Answer, id=id)
    if answer.deleted and not request.user.can_view_deleted_post(answer):
        raise Http404
    elif not request.user.can_edit_post(answer):
        raise Http404

    if request.method == "POST":
        revision_form = RevisionForm(answer, data=request.POST)
        revision_form.is_valid()
        revision = answer.revisions.get(revision=revision_form.cleaned_data['revision'])

        if 'select_revision' in request.POST:
            form = EditAnswerForm(answer, revision)
        else:
            form = EditAnswerForm(answer, revision, data=request.POST)

        if not 'select_revision' in request.POST and form.is_valid():
            if form.has_changed():
                ReviseAction(user=request.user, node=answer).save(data=form.cleaned_data)
            else:
                if not revision == answer.active_revision:
                    RollbackAction(user=request.user, node=answer).save(data=dict(activate=revision))

            return HttpResponseRedirect(answer.get_absolute_url())

    else:
        revision_form = RevisionForm(answer)
        form = EditAnswerForm(answer)
    return render_to_response('answer_edit.html', {
                              'answer': answer,
                              'revision_form': revision_form,
                              'form': form,
                              }, context_instance=RequestContext(request))

def answer(request, id):
    question = get_object_or_404(Question, id=id)
    if request.method == "POST":
        form = AnswerForm(question, request.POST)
        if form.is_valid():
            if request.user.is_authenticated():
                data = {
                    "user_ip":request.META["REMOTE_ADDR"],
                    "user_agent":request.environ['HTTP_USER_AGENT'],
                    "comment_author":request.user.username,
                    "comment_author_email":request.user.email,
                    "comment_author_url":request.user.website,
                    "comment":request.POST['text']
                }
                if Node.isSpam(request.POST['text'], data):
                    raise SpamNotAllowedException("answer")

                answer = AnswerAction(user=request.user).save(dict(question=question, **form.cleaned_data)).node
                return HttpResponseRedirect(answer.get_absolute_url())
            else:
                return HttpResponseRedirect(reverse('auth_action_signin', kwargs={'action': 'newquestion'}))

    return HttpResponseRedirect(question.get_absolute_url())

