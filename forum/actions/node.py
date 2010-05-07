from django.utils.html import strip_tags
from django.utils.translation import ugettext as _
from forum.models.action import ActionProxy
from forum.models import Comment, Question, Answer, NodeRevision

class NodeEditAction(ActionProxy):
    def create_revision_data(self, initial=False, **data):
        revision_data = dict(summary=data.get('summary', (initial and _('Initial revision' or ''))), body=data['text'])

        if data.get('title', None):
            revision_data['title'] = strip_tags(data['title'].strip())

        if data.get('tags', None):
            revision_data['tagnames'] = data['tags'].strip()

        return revision_data

class AskAction(NodeEditAction):
    def process_data(self, **data):
        question = Question(author=self.user, **self.create_revision_data(True, **data))
        question.save()
        self.node = question

    def describe(self, viewer=None):
        return _("%(user)s asked %(question)s") % {
            'user': self.hyperlink(self.user.get_profile_url(), self.friendly_username(viewer, self.user)),
            'question': self.hyperlink(self.node.get_absolute_url(), self.node.title)
        }

class AnswerAction(NodeEditAction):
    def process_data(self, **data):
        answer = Answer(author=self.user, parent=data['question'], **self.create_revision_data(True, **data))
        answer.save()
        self.node = answer

    def process_action(self):
        self.node.question.reset_answer_count_cache()

    def describe(self, viewer=None):
        question = self.node.parent
        return _("%(user)s answered %(asker)s %(question)s") % {
            'user': self.hyperlink(self.user.get_profile_url(), self.friendly_username(viewer, self.user)),
            'asker': self.hyperlink(question.author.get_profile_url(), self.friendly_username(viewer, question.author)),
            'question': self.hyperlink(self.node.get_absolute_url(), question.title)
        }

class CommentAction(ActionProxy):
    def process_data(self, text='', parent=None):
        comment = Comment(author=self.user, parent=parent, body=text)
        comment.save()
        self.node = comment

    def describe(self, viewer=None):
        return _("%(user)s commented on %(post_desc)s") % {
            'user': self.hyperlink(self.node.author.get_profile_url(), self.friendly_username(viewer, self.node.author)),
            'post_desc': self.describe_node(viewer, self.node.parent)
        }

class ReviseAction(NodeEditAction):
    def process_data(self, **data):
        revision_data = self.create_revision_data(**data)
        revision = self.node.create_revision(self.user, action=self, **revision_data)
        self.extra = revision.revision

    def describe(self, viewer=None):
        return _("%(user)s edited %(post_desc)s") % {
            'user': self.hyperlink(self.user.get_profile_url(), self.friendly_username(viewer, self.user)),
            'post_desc': self.describe_node(viewer, self.node)
        }

class RetagAction(ActionProxy):
    def process_data(self, tagnames=''):
        active = self.node.active_revision
        revision_data = dict(summary=_('Retag'), title=active.title, tagnames=strip_tags(tagnames.strip()), body=active.body)
        self.node.create_revision(self.user, action=self, **revision_data)

    def describe(self, viewer=None):
        return _("%(user)s retagged %(post_desc)s") % {
            'user': self.hyperlink(self.user.get_profile_url(), self.friendly_username(viewer, self.user)),
            'post_desc': self.describe_node(viewer, self.node)
        }

class RollbackAction(ActionProxy):
    def process_data(self, activate=None):
        previous = self.node.active_revision
        self.node.activate_revision(self.user, activate, self)
        self.extra = "%d:%d" % (previous.revision, activate.revision)

    def describe(self, viewer=None):
        revisions = [NodeRevision.objects.get(node=self.node, revision=int(n)) for n in self.extra.split(':')]

        return _("%(user)s reverted %(post_desc)s from revision %(initial)d (%(initial_sum)s) to revision %(final)d (%(final_sum)s)") % {
            'user': self.hyperlink(self.user.get_profile_url(), self.friendly_username(viewer, self.user)),
            'post_desc': self.describe_node(viewer, self.node),
            'initial': revisions[0].revision, 'initial_sum': revisions[0].summary,
            'final': revisions[1].revision, 'final_sum': revisions[1].summary,
        }

class CloseAction(ActionProxy):
    def process_action(self):
        self.node.extra_action = self
        self.node.marked = True
        self.node.save()

    def cancel_action(self):
        self.node.extra_action = None
        self.node.marked = False
        self.node.save()

    def describe(self, viewer=None):
        return _("%(user)s closed %(post_desc)s: %(reason)s") % {
            'user': self.hyperlink(self.user.get_profile_url(), self.friendly_username(viewer, self.user)),
            'post_desc': self.describe_node(viewer, self.node),
            'reason': self.extra
        }