from datetime import datetime, timedelta
from django.core.management.base import NoArgsCommand
from django.utils.translation import ugettext as _
from django.template import loader, Context, Template
from django.core.mail import EmailMultiAlternatives
from django.utils import translation
from django.conf import settings
from forum import settings
from forum.settings.email import EMAIL_DIGEST_CONTROL
from forum import actions
from forum.models import KeyValue, Action, User, QuestionSubscription
from forum.utils.mail import send_email
import logging

class QuestionRecord:
    def __init__(self, question):
        self.question = question
        self.records = []

    def log_activity(self, activity):
        self.records.append(activity)

    def get_activity_since(self, since):
        activity = [r for r in self.records if r.action_date > since]
        answers = [a for a in activity if a.action_type == "answer"]
        comments = [a for a in activity if a.activity_type == "comment"]

        accepted = [a for a in activity if a.activity_type == "accept_answer"]

        if len(accepted):
            accepted = accepted[-1:][0]
        else:
            accepted = None

        return {
        'answers': answers,
        'comments': comments,
        'accepted': accepted,
        }


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        try:
            translation.activate(settings.LANGUAGE_CODE)
        except:
            logging.error("Unable to set the locale in the send emails cron job")

        digest_control = EMAIL_DIGEST_CONTROL.value

        if digest_control is None:
            digest_control = KeyValue(key='DIGEST_CONTROL', value={
            'LAST_DAILY': datetime.now() - timedelta(days=1),
            'LAST_WEEKLY': datetime.now() - timedelta(days=1),
            })

        self.send_digest('daily', 'd', digest_control.value['LAST_DAILY'])
        digest_control.value['LAST_DAILY'] = datetime.now()

        if digest_control.value['LAST_WEEKLY'] + timedelta(days=7) <= datetime.now():
            self.send_digest('weekly', 'w', digest_control.value['LAST_WEEKLY'])
            digest_control.value['LAST_WEEKLY'] = datetime.now()

        EMAIL_DIGEST_CONTROL.set_value(digest_control)


    def send_digest(self, name, char_in_db, control_date):
        new_questions, question_records = self.prepare_activity(control_date)
        new_users = User.objects.filter(date_joined__gt=control_date)

        digest_subject = settings.EMAIL_SUBJECT_PREFIX + _('Daily digest')

        users = User.objects.filter(subscription_settings__enable_notifications=True)

        msgs = []

        for u in users:
            context = {
            'user': u,
            'digest_type': name,
            }

            if u.subscription_settings.member_joins == char_in_db:
                context['new_users'] = new_users
            else:
                context['new_users'] = False

            if u.subscription_settings.subscribed_questions == char_in_db:
                activity_in_subscriptions = []

                for id, r in question_records.items():
                    try:
                        subscription = QuestionSubscription.objects.get(question=r.question, user=u)

                        record = r.get_activity_since(subscription.last_view)

                        if not u.subscription_settings.notify_answers:
                            del record['answers']

                        if not u.subscription_settings.notify_comments:
                            if u.subscription_settings.notify_comments_own_post:
                                record.comments = [a for a in record.comments if a.user == u]
                                record['own_comments_only'] = True
                            else:
                                del record['comments']

                        if not u.subscription_settings.notify_accepted:
                            del record['accepted']

                        if record.get('answers', False) or record.get('comments', False) or record.get('accepted', False
                                                                                                       ):
                            activity_in_subscriptions.append({'question': r.question, 'activity': record})
                    except:
                        pass

                context['activity_in_subscriptions'] = activity_in_subscriptions
            else:
                context['activity_in_subscriptions'] = False

            if u.subscription_settings.new_question == char_in_db:
                context['new_questions'] = new_questions
                context['watched_tags_only'] = False
            elif u.subscription_settings.new_question_watched_tags == char_in_db:
                context['new_questions'] = [q for q in new_questions if
                                            q.tags.filter(id__in=u.marked_tags.filter(user_selections__reason='good')
                                                          ).count() > 0]
                context['watched_tags_only'] = True
            else:
                context['new_questions'] = False

            if context['new_users'] or context['activity_in_subscriptions'] or context['new_questions']:
                send_email(digest_subject, [(u.username, u.email)], "notifications/digest.html", context, threaded=False
                           )


    def prepare_activity(self, since):
        all_activity = Action.objects.filter(canceled=False, action_date__gt=since, action_type__in=(
        actions.AskAction.get_type(), actions.AnswerAction.get_type(),
        actions.CommentAction.get_type(), actions.AcceptAnswerAction.get_type()
        )).order_by('action_date')

        question_records = {}
        new_questions = []

        for activity in all_activity:
            try:
                question = activity.node.abs_parent

                if not question.id in question_records:
                    question_records[question.id] = QuestionRecord(question)

                question_records[question.id].log_activity(activity)

                if activity.action_type == "ask":
                    new_questions.append(question)
            except:
                pass

        return new_questions, question_records

