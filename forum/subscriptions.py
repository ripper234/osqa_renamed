import os
import re
import datetime
from forum.models import User, Question, Comment, QuestionSubscription, SubscriptionSettings, Answer
from forum.utils.mail import send_email
from django.utils.translation import ugettext as _
from forum.actions import AskAction, AnswerAction, CommentAction, AcceptAnswerAction, UserJoinsAction, QuestionViewAction
from django.conf import settings
from django.db.models import Q, F

def create_subscription_if_not_exists(question, user):
    try:
        subscription = QuestionSubscription.objects.get(question=question, user=user)
    except:
        subscription = QuestionSubscription(question=question, user=user)
        subscription.save()

def apply_default_filters(queryset, excluded_id):
    return queryset.values('email', 'username').exclude(id=excluded_id)

def create_recipients_dict(usr_list):
    return [(s['username'], s['email'], {'username': s['username']}) for s in usr_list]

def question_posted(action, new):
    question = action.node

    subscribers = User.objects.values('email', 'username').filter(
            Q(subscription_settings__enable_notifications=True, subscription_settings__new_question='i') |
            (Q(subscription_settings__new_question_watched_tags='i') &
              Q(marked_tags__name__in=question.tagnames.split(' ')) &
              Q(tag_selections__reason='good'))
    ).exclude(id=question.author.id).distinct()

    recipients = create_recipients_dict(subscribers)

    send_email(settings.EMAIL_SUBJECT_PREFIX + _("New question on %(app_name)s") % dict(app_name=settings.APP_SHORT_NAME),
               recipients, "notifications/newquestion.html", {
        'question': question,
    })

    if question.author.subscription_settings.questions_asked:
        subscription = QuestionSubscription(question=question, user=question.author)
        subscription.save()

    new_subscribers = User.objects.filter(
            Q(subscription_settings__all_questions=True) |
            Q(subscription_settings__all_questions_watched_tags=True,
                    marked_tags__name__in=question.tagnames.split(' '),
                    tag_selections__reason='good'))

    for user in new_subscribers:
        create_subscription_if_not_exists(question, user)

AskAction.hook(question_posted)


def answer_posted(action, new):
    answer = action.node
    question = answer.question

    subscribers = question.subscribers.values('email', 'username').filter(
            subscription_settings__enable_notifications=True,
            subscription_settings__notify_answers=True,
            subscription_settings__subscribed_questions='i'
    ).exclude(id=answer.author.id).distinct()
    recipients = create_recipients_dict(subscribers)

    send_email(settings.EMAIL_SUBJECT_PREFIX + _("New answer to '%(question_title)s'") % dict(question_title=question.title),
               recipients, "notifications/newanswer.html", {
        'question': question,
        'answer': answer
    }, threaded=False)

    if answer.author.subscription_settings.questions_answered:
        create_subscription_if_not_exists(question, answer.author)

AnswerAction.hook(answer_posted)


def comment_posted(action, new):
    comment = action.node
    post = comment.content_object

    if post.__class__ == Question:
        question = post
    else:
        question = post.question

    subscribers = question.subscribers.values('email', 'username')

    q_filter = Q(subscription_settings__notify_comments=True) | Q(subscription_settings__notify_comments_own_post=True, id=post.author.id)

    #inreply = re.search('@\w+', comment.comment)
    #if inreply is not None:
    #    q_filter = q_filter | Q(subscription_settings__notify_reply_to_comments=True,
    #                            username__istartswith=inreply.group(0)[1:],
    ##                            comments__object_id=post.id,
    #                            comments__content_type=ContentType.objects.get_for_model(post.__class__)
    #                            )

    subscribers = subscribers.filter(
            q_filter, subscription_settings__subscribed_questions='i', subscription_settings__enable_notifications=True
    ).exclude(id=comment.user.id).distinct()

    recipients = create_recipients_dict(subscribers)

    send_email(settings.EMAIL_SUBJECT_PREFIX + _("New comment on %(question_title)s") % dict(question_title=question.title),
               recipients, "notifications/newcomment.html", {
                'comment': comment,
                'post': post,
                'question': question,
    }, threaded=False)

    if comment.user.subscription_settings.questions_commented:
        create_subscription_if_not_exists(question, comment.user)

CommentAction.hook(comment_posted)


def answer_accepted(action, new):
    question = action.node.question

    subscribers = question.subscribers.values('email', 'username').filter(
            subscription_settings__enable_notifications=True,
            subscription_settings__notify_accepted=True,
            subscription_settings__subscribed_questions='i'
    ).exclude(id=instance.accepted_by.id).distinct()
    recipients = create_recipients_dict(subscribers)

    send_email(settings.EMAIL_SUBJECT_PREFIX + _("An answer to '%(question_title)s' was accepted") % dict(question_title=question.title),
               recipients, "notifications/answeraccepted.html", {
        'question': question,
        'answer': action.node
    }, threaded=False)

AcceptAnswerAction.hook(answer_accepted)


def member_joined(action, new):
    subscribers = User.objects.values('email', 'username').filter(
            subscription_settings__enable_notifications=True,
            subscription_settings__member_joins='i'
    ).exclude(id=action.user.id).distinct()

    recipients = create_recipients_dict(subscribers)

    send_email(settings.EMAIL_SUBJECT_PREFIX + _("%(username)s is a new member on %(app_name)s") % dict(username=instance.username, app_name=settings.APP_SHORT_NAME),
               recipients, "notifications/newmember.html", {
        'newmember': action.user,
    }, threaded=False)

UserJoinsAction.hook(member_joined)

def question_viewed(action, new):
    if not action.viewuser.is_authenticated():
        return

    try:
        subscription = QuestionSubscription.objects.get(question=action.question, user=action.viewuser)
        subscription.last_view = datetime.datetime.now()
        subscription.save()
    except:
        if action.viewuser.subscription_settings.questions_viewed:
            subscription = QuestionSubscription(question=action.question, user=action.viewuser)
            subscription.save()

QuestionViewAction.hook(question_viewed)


#todo: translate this
#record_answer_event_re = re.compile("You have received (a|\d+) .*new response.*")
#def record_answer_event(instance, created, **kwargs):
#    if created:
#        q_author = instance.question.author
#        found_match = False
#        #print 'going through %d messages' % q_author.message_set.all().count()
#        for m in q_author.message_set.all():
##            #print m.message
# #           match = record_answer_event_re.search(m.message)
#            if match:
#                found_match = True
#                try:
#                    cnt = int(match.group(1))
#                except:
#                    cnt = 1
##                m.message = u"You have received %d <a href=\"%s?sort=responses\">new responses</a>."\
# #                           % (cnt+1, q_author.get_profile_url())
#
#                m.save()
#                break
#        if not found_match:
#            msg = u"You have received a <a href=\"%s?sort=responses\">new response</a>."\
#                    % q_author.get_profile_url()
#
#            q_author.message_set.create(message=msg)
#
#post_save.connect(record_answer_event, sender=Answer)