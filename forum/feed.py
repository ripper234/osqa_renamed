try:
    from django.contrib.syndication.views import Feed, FeedDoesNotExist
    old_version = False
except:
    from django.contrib.syndication.feeds import Feed, FeedDoesNotExist
    old_version = True

from django.utils.translation import ugettext as _
from models import Question
from forum import settings


class RssQuestionFeed(Feed):
    copyright = settings.APP_COPYRIGHT

    def __init__(self, question_list, title, description, request):
        self._title = title
        self._description = description
        self._question_list = question_list
        self._url = request.path

        if old_version:
            super(Feed, self).__init__(request, '')

    def title(self):
        return self._title

    def link(self):
        return self._url

    def item_link(self, item):
        return item.get_absolute_url()

    def item_author_name(self, item):
        return item.author.username

    def item_author_link(self, item):
        return item.author.get_profile_url()

    def item_pubdate(self, item):
        return item.added_at

    def items(self, item):
       return self._question_list[:30]
