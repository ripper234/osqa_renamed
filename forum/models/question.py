from base import *
from tag import Tag
from django.utils.translation import ugettext as _

question_view = django.dispatch.Signal(providing_args=['instance', 'user'])

class Question(Node):
    class Meta(Node.Meta):
        proxy = True

    answer_count = DenormalizedField("children", node_type="answer", deleted=None)
    favorite_count = DenormalizedField("actions", action_type="favorite", canceled=False)

    friendly_name = _("question")

    @property   
    def closed(self):
        return self.extra_action

    @property    
    def view_count(self):
        return self.extra_count

    @property
    def headline(self):
        if self.marked:
            return _('[closed] ') + self.title

        if self.deleted:
            return _('[deleted] ') + self.title

        return self.title

    @property
    def answer_accepted(self):
        return self.extra_ref is not None

    @property
    def accepted_answer(self):
        return self.extra_ref

    @models.permalink    
    def get_absolute_url(self):
        return ('question', (), {'id': self.id, 'slug': django_urlquote(slugify(self.title))})

    def get_revision_url(self):
        return reverse('question_revisions', args=[self.id])

    def get_related_questions(self, count=10):
        cache_key = '%s.related_questions:%d:%d' % (settings.APP_URL, count, self.id)
        related_list = cache.get(cache_key)

        if related_list is None:
            related_list = Question.objects.values('id').filter(tags__id__in=[t.id for t in self.tags.all()]
            ).exclude(id=self.id).filter(deleted=None).annotate(frequency=models.Count('id')).order_by('-frequency')[:count]
            cache.set(cache_key, related_list, 60 * 60)

        return [Question.objects.get(id=r['id']) for r in related_list]


def question_viewed(instance, **kwargs):
    instance.extra_count += 1
    instance.save()

question_view.connect(question_viewed)


class QuestionSubscription(models.Model):
    user = models.ForeignKey(User)
    question = models.ForeignKey(Node)
    auto_subscription = models.BooleanField(default=True)
    last_view = models.DateTimeField(default=datetime.datetime.now())

    class Meta:
        app_label = 'forum'


class QuestionRevision(NodeRevision):
    class Meta:
        proxy = True
        
