from datetime import datetime, timedelta

from forum.models import Question, Action
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django import template
from forum.actions import *
from forum import settings

register = template.Library()

@register.inclusion_tag('node/vote_buttons.html')
def vote_buttons(post, user):
    context = dict(post=post, user_vote='none')

    if user.is_authenticated():
        context['user_vote'] = {1: 'up', -1: 'down', None: 'none'}[VoteAction.get_for(user, post)]

    return context

@register.inclusion_tag('node/accept_button.html')
def accept_button(answer, user):
    return {
        'can_accept': user.is_authenticated() and user.can_accept_answer(answer),
        'answer': answer,
        'user': user
    }

@register.inclusion_tag('node/favorite_mark.html')
def favorite_mark(question, user):
    try:
        FavoriteAction.objects.get(node=question, user=user)
        favorited = True
    except:
        favorited = False

    return {'favorited': favorited, 'favorite_count': question.favorite_count, 'question': question}

def post_control(text, url, command=False, withprompt=False, title=""):
    return {'text': text, 'url': url, 'command': command, 'withprompt': withprompt ,'title': title}

@register.inclusion_tag('node/post_controls.html')
def post_controls(post, user):
    controls = []

    if user.is_authenticated():
        post_type = (post.__class__ is Question) and 'question' or 'answer'

        if post_type == "answer":
            controls.append(post_control(_('permanent link'), '#%d' % post.id, title=_("answer permanent link")))

        edit_url = reverse('edit_' + post_type, kwargs={'id': post.id})
        if user.can_edit_post(post):
            controls.append(post_control(_('edit'), edit_url))
        elif post_type == 'question' and user.can_retag_questions():
            controls.append(post_control(_('retag'), edit_url))

        if post_type == 'question':
            if post.closed and user.can_reopen_question(post):
                controls.append(post_control(_('reopen'), reverse('reopen', kwargs={'id': post.id}), command=True))
            elif not post.closed and user.can_close_question(post):
                controls.append(post_control(_('close'), reverse('close', kwargs={'id': post.id}), command=True, withprompt=True))

        if user.can_flag_offensive(post):
            label = _('report')
            
            if user.can_view_offensive_flags(post):
                label =  "%s (%d)" % (label, post.flag_count)

            controls.append(post_control(label, reverse('flag_post', kwargs={'id': post.id}),
                    command=True, withprompt=True, title=_("report as offensive (i.e containing spam, advertising, malicious text, etc.)")))

        if user.can_delete_post(post):
            if post.deleted:
                controls.append(post_control(_('undelete'), reverse('delete_post', kwargs={'id': post.id}),
                        command=True))
            else:
                controls.append(post_control(_('delete'), reverse('delete_post', kwargs={'id': post.id}),
                        command=True))

    return {'controls': controls}

@register.inclusion_tag('node/comments.html')
def comments(post, user):
    all_comments = post.comments.filter(deleted=None).order_by('added_at')

    if len(all_comments) <= 5:
        top_scorers = all_comments
    else:
        top_scorers = sorted(all_comments, lambda c1, c2: c2.score - c1.score)[0:5]

    comments = []
    showing = 0
    for c in all_comments:
        context = {
            'can_delete': user.can_delete_comment(c),
            'can_like': user.can_like_comment(c),
            'can_edit': user.can_edit_comment(c)
        }

        if c in top_scorers or c.is_reply_to(user):
            context['top_scorer'] = True
            showing += 1
        
        if context['can_like']:
            context['likes'] = VoteAction.get_for(user, c) == 1

        context['user'] = c.user
        context['comment'] = c.comment
        context.update(dict(c.__dict__))
        comments.append(context)

    return {
        'comments': comments,
        'post': post,
        'can_comment': user.can_comment(post),
        'max_length': settings.FORM_MAX_COMMENT_BODY,
        'min_length': settings.FORM_MIN_COMMENT_BODY,
        'show_gravatar': settings.FORM_GRAVATAR_IN_COMMENTS,
        'showing': showing,
        'total': len(all_comments),
        'user': user,
    }
