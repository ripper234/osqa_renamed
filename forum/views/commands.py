import datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import simplejson
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ungettext, ugettext as _
from django.template import RequestContext
from forum.models import *
from forum.forms import CloseForm
from forum.actions import *
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from forum.utils.decorators import ajax_method, ajax_login_required
from decorators import command, CommandException
from forum import settings
import logging

class NotEnoughRepPointsException(CommandException):
    def __init__(self, action):
        super(NotEnoughRepPointsException, self).__init__(
            _("""
            Sorry, but you don't have enough reputation points to %(action)s.<br />
            Please check the <a href'%(faq_url)s'>faq</a>
            """ % {'action': action, 'faq_url': reverse('faq')})
        )

class CannotDoOnOwnException(CommandException):
    def __init__(self, action):
        super(CannotDoOnOwnException, self).__init__(
            _("""
            Sorry but you cannot %(action)s your own post.<br />
            Please check the <a href'%(faq_url)s'>faq</a>
            """ % {'action': action, 'faq_url': reverse('faq')})
        )

class AnonymousNotAllowedException(CommandException):
    def __init__(self, action):
        super(AnonymousNotAllowedException, self).__init__(
            _("""
            Sorry but anonymous users cannot %(action)s.<br />
            Please login or create an account <a href'%(signin_url)s'>here</a>.
            """ % {'action': action, 'signin_url': reverse('auth_signin')})
        )

class SpamNotAllowedException(CommandException):
    def __init__(self, action = "comment"):
        super(SpamNotAllowedException, self).__init__(
            _("""Your %s has been marked as spam.""" % action)
        )

class NotEnoughLeftException(CommandException):
    def __init__(self, action, limit):
        super(NotEnoughLeftException, self).__init__(
            _("""
            Sorry, but you don't have enough %(action)s left for today..<br />
            The limit is %(limit)s per day..<br />
            Please check the <a href'%(faq_url)s'>faq</a>
            """ % {'action': action, 'limit': limit, 'faq_url': reverse('faq')})
        )

class CannotDoubleActionException(CommandException):
    def __init__(self, action):
        super(CannotDoubleActionException, self).__init__(
            _("""
            Sorry, but you cannot %(action)s twice the same post.<br />
            Please check the <a href'%(faq_url)s'>faq</a>
            """ % {'action': action, 'faq_url': reverse('faq')})
        )


@command
def vote_post(request, id, vote_type):
    post = get_object_or_404(Node, id=id).leaf
    user = request.user

    if not user.is_authenticated():
        raise AnonymousNotAllowedException(_('vote'))

    if user == post.author:
        raise CannotDoOnOwnException(_('vote'))

    if not (vote_type == 'up' and user.can_vote_up() or user.can_vote_down()):
        raise NotEnoughRepPointsException(vote_type == 'up' and _('upvote') or _('downvote'))

    user_vote_count_today = user.get_vote_count_today()

    if user_vote_count_today >= int(settings.MAX_VOTES_PER_DAY):
        raise NotEnoughLeftException(_('votes'), str(settings.MAX_VOTES_PER_DAY))

    new_vote_cls = (vote_type == 'up') and VoteUpAction or VoteDownAction
    score_inc = 0

    try:
        old_vote = Action.objects.get_for_types((VoteUpAction, VoteDownAction), node=post, user=user)

        if old_vote.action_date < datetime.datetime.now() - datetime.timedelta(days=int(settings.DENY_UNVOTE_DAYS)):
            raise CommandException(
                    _("Sorry but you cannot cancel a vote after %(ndays)d %(tdays)s from the original vote") %
                    {'ndays': int(settings.DENY_UNVOTE_DAYS), 'tdays': ungettext('day', 'days', int(settings.DENY_UNVOTE_DAYS))}
            )

        old_vote.cancel(ip=request.META['REMOTE_ADDR'])
        score_inc += (old_vote.__class__ == VoteDownAction) and 1 or -1
    except ObjectDoesNotExist:
        old_vote = None

    if old_vote.__class__ != new_vote_cls:
        new_vote_cls(user=user, node=post, ip=request.META['REMOTE_ADDR']).save()
        score_inc += (new_vote_cls == VoteUpAction) and 1 or -1
    else:
        vote_type = "none"

    response = {
        'commands': {
            'update_post_score': [id, score_inc],
            'update_user_post_vote': [id, vote_type]
        }
    }

    votes_left = (int(settings.MAX_VOTES_PER_DAY) - user_vote_count_today) + (vote_type == 'none' and -1 or 1)

    if int(settings.START_WARN_VOTES_LEFT) >= votes_left:
        response['message'] = _("You have %(nvotes)s %(tvotes)s left today.") % \
                    {'nvotes': votes_left, 'tvotes': ungettext('vote', 'votes', votes_left)}

    return response

@command
def flag_post(request, id):
    if not request.POST:
        return render_to_response('node/report.html', {'types': settings.FLAG_TYPES})

    post = get_object_or_404(Node, id=id)
    user = request.user

    if not user.is_authenticated():
        raise AnonymousNotAllowedException(_('flag posts'))

    if user == post.author:
        raise CannotDoOnOwnException(_('flag'))

    if not (user.can_flag_offensive(post)):
        raise NotEnoughRepPointsException(_('flag posts'))

    user_flag_count_today = user.get_flagged_items_count_today()

    if user_flag_count_today >= int(settings.MAX_FLAGS_PER_DAY):
        raise NotEnoughLeftException(_('flags'), str(settings.MAX_FLAGS_PER_DAY))

    try:
        current = FlagAction.objects.get(user=user, node=post)
        raise CommandException(_("You already flagged this post with the following reason: %(reason)s") % {'reason': current.extra})
    except ObjectDoesNotExist:
        reason = request.POST.get('prompt', '').strip()

        if not len(reason):
            raise CommandException(_("Reason is empty"))

        FlagAction(user=user, node=post, extra=reason, ip=request.META['REMOTE_ADDR']).save()

    return {'message': _("Thank you for your report. A moderator will review your submission shortly.")}
        
@command
def like_comment(request, id):
    comment = get_object_or_404(Comment, id=id)
    user = request.user

    if not user.is_authenticated():
        raise AnonymousNotAllowedException(_('like comments'))

    if user == comment.user:
        raise CannotDoOnOwnException(_('like'))

    if not user.can_like_comment(comment):
        raise NotEnoughRepPointsException( _('like comments'))    

    try:
        like = VoteUpCommentAction.objects.get(node=comment, user=user)
        like.cancel(ip=request.META['REMOTE_ADDR'])
        likes = False
    except ObjectDoesNotExist:
        VoteUpCommentAction(node=comment, user=user, ip=request.META['REMOTE_ADDR']).save()
        likes = True

    return {
        'commands': {
            'update_post_score': [comment.id, likes and 1 or -1],
            'update_user_post_vote': [comment.id, likes and 'up' or 'none']
        }
    }

@command
def delete_comment(request, id):
    comment = get_object_or_404(Comment, id=id)
    user = request.user

    if not user.is_authenticated():
        raise AnonymousNotAllowedException(_('delete comments'))

    if not user.can_delete_comment(comment):
        raise NotEnoughRepPointsException( _('delete comments'))

    if not comment.deleted:
        DeleteAction(node=comment, user=user, ip=request.META['REMOTE_ADDR']).save()

    return {
        'commands': {
            'remove_comment': [comment.id],
        }
    }

@command
def mark_favorite(request, id):
    question = get_object_or_404(Question, id=id)

    if not request.user.is_authenticated():
        raise AnonymousNotAllowedException(_('mark a question as favorite'))

    try:
        favorite = FavoriteAction.objects.get(node=question, user=request.user)
        favorite.cancel(ip=request.META['REMOTE_ADDR'])
        added = False
    except ObjectDoesNotExist:
        FavoriteAction(node=question, user=request.user, ip=request.META['REMOTE_ADDR']).save()
        added = True

    return {
        'commands': {
            'update_favorite_count': [added and 1 or -1],
            'update_favorite_mark': [added and 'on' or 'off']
        }
    }

@command
def comment(request, id):
    post = get_object_or_404(Node, id=id)
    user = request.user

    if not user.is_authenticated():
        raise AnonymousNotAllowedException(_('comment'))

    if not request.method == 'POST':
        raise CommandException(_("Invalid request"))

    comment_text = request.POST.get('comment', '').strip()

    if not len(comment_text):
        raise CommandException(_("Comment is empty"))

    if len(comment_text) < settings.FORM_MIN_COMMENT_BODY:
        raise CommandException(_("At least %d characters required on comment body.") % settings.FORM_MIN_COMMENT_BODY)

    if len(comment_text) > settings.FORM_MAX_COMMENT_BODY:
        raise CommandException(_("No more than %d characters on comment body.") % settings.FORM_MAX_COMMENT_BODY)

    data = {
        "user_ip":request.META["REMOTE_ADDR"],
        "user_agent":request.environ['HTTP_USER_AGENT'],
        "comment_author":request.user.username,
        "comment_author_email":request.user.email,
        "comment_author_url":request.user.website,
        "comment":comment_text
    }
    if Node.isSpam(comment_text, data):
        raise SpamNotAllowedException()

    if 'id' in request.POST:
        comment = get_object_or_404(Comment, id=request.POST['id'])

        if not user.can_edit_comment(comment):
            raise NotEnoughRepPointsException( _('edit comments'))

        comment = ReviseAction(user=user, node=comment, ip=request.META['REMOTE_ADDR']).save(data=dict(text=comment_text)).node
    else:
        if not user.can_comment(post):
            raise NotEnoughRepPointsException( _('comment'))

        comment = CommentAction(user=user, ip=request.META['REMOTE_ADDR']).save(data=dict(text=comment_text, parent=post)).node

    if comment.active_revision.revision == 1:
        return {
            'commands': {
                'insert_comment': [
                    id, comment.id, comment.comment, user.username, user.get_profile_url(),
                        reverse('delete_comment', kwargs={'id': comment.id}), reverse('node_markdown', kwargs={'id': comment.id})
                ]
            }
        }
    else:
        return {
            'commands': {
                'update_comment': [comment.id, comment.comment]
            }
        }

@command
def node_markdown(request, id):
    user = request.user

    if not user.is_authenticated():
        raise AnonymousNotAllowedException(_('accept answers'))

    node = get_object_or_404(Node, id=id)
    return HttpResponse(node.body, mimetype="text/plain")


@command
def accept_answer(request, id):
    user = request.user

    if not user.is_authenticated():
        raise AnonymousNotAllowedException(_('accept answers'))

    answer = get_object_or_404(Answer, id=id)
    question = answer.question

    if not user.can_accept_answer(answer):
        raise CommandException(_("Sorry but only the question author can accept an answer"))

    commands = {}

    if answer.accepted:
        answer.accepted.cancel(user, ip=request.META['REMOTE_ADDR'])
        commands['unmark_accepted'] = [answer.id]
    else:
        if question.answer_accepted:
            accepted = question.accepted_answer
            accepted.accepted.cancel(user, ip=request.META['REMOTE_ADDR'])
            commands['unmark_accepted'] = [accepted.id]

        AcceptAnswerAction(node=answer, user=user, ip=request.META['REMOTE_ADDR']).save()
        commands['mark_accepted'] = [answer.id]

    return {'commands': commands}

@command    
def delete_post(request, id):
    post = get_object_or_404(Node, id=id)
    user = request.user

    if not user.is_authenticated():
        raise AnonymousNotAllowedException(_('delete posts'))

    if not (user.can_delete_post(post)):
        raise NotEnoughRepPointsException(_('delete posts'))

    ret = {'commands': {}}

    if post.deleted:
        post.deleted.cancel(user, ip=request.META['REMOTE_ADDR'])
        ret['commands']['unmark_deleted'] = [post.node_type, id]
    else:
        DeleteAction(node=post, user=user, ip=request.META['REMOTE_ADDR']).save()

        ret['commands']['mark_deleted'] = [post.node_type, id]

    return ret

@command
def close(request, id, close):
    if close and not request.POST:
        return render_to_response('node/report.html', {'types': settings.CLOSE_TYPES})

    question = get_object_or_404(Question, id=id)
    user = request.user

    if not user.is_authenticated():
        raise AnonymousNotAllowedException(_('close questions'))

    if question.extra_action:
        if not user.can_reopen_question(question):
            raise NotEnoughRepPointsException(_('reopen questions'))

        question.extra_action.cancel(user, ip=request.META['REMOTE_ADDR'])
    else:
        if not request.user.can_close_question(question):
            raise NotEnoughRepPointsException(_('close questions'))

        reason = request.POST.get('prompt', '').strip()

        if not len(reason):
            raise CommandException(_("Reason is empty"))

        CloseAction(node=question, user=user, extra=reason, ip=request.META['REMOTE_ADDR']).save()

    return {
        'commands': {
            'refresh_page': []
        }
    }

@command
def subscribe(request, id):
    question = get_object_or_404(Question, id=id)

    try:
        subscription = QuestionSubscription.objects.get(question=question, user=request.user)
        subscription.delete()
        subscribed = False
    except:
        subscription = QuestionSubscription(question=question, user=request.user, auto_subscription=False)
        subscription.save()
        subscribed = True

    return {
        'commands': {
                'set_subscription_button': [subscribed and _('unsubscribe me') or _('subscribe me')],
                'set_subscription_status': ['']
            }
    }

#internally grouped views - used by the tagging system
@ajax_login_required
def mark_tag(request, tag=None, **kwargs):#tagging system
    action = kwargs['action']
    ts = MarkedTag.objects.filter(user=request.user, tag__name=tag)
    if action == 'remove':
        logging.debug('deleting tag %s' % tag)
        ts.delete()
    else:
        reason = kwargs['reason']
        if len(ts) == 0:
            try:
                t = Tag.objects.get(name=tag)
                mt = MarkedTag(user=request.user, reason=reason, tag=t)
                mt.save()
            except:
                pass
        else:
            ts.update(reason=reason)
    return HttpResponse(simplejson.dumps(''), mimetype="application/json")

def matching_tags(request):
    if len(request.GET['q']) == 0:
       raise CommandException(_("Invalid request"))

    possible_tags = Tag.objects.filter(name__istartswith = request.GET['q'])
    tag_output = ''
    for tag in possible_tags:
        tag_output += (tag.name + "|" + tag.name + "." + tag.used_count.__str__() + "\n")
        
    return HttpResponse(tag_output, mimetype="text/plain")







