from django.core.urlresolvers import reverse
from forum.utils import html

class UiObjectUserLevelBase(object):
    def show_to(self, user):
        return True

class SuperuserUiObject(UiObjectUserLevelBase):
    def show_to(self, user):
        return user.is_superuser

class StaffUiObject(UiObjectUserLevelBase):
    def show_to(self, user):
        return user.is_staff or user.is_superuser

class ReputedUserUiObject(UiObjectUserLevelBase):
    def __init__(self, min_rep):
        self.min_rep = min_rep

    def show_to(self, user):
        return user.is_authenticated() and user.reputation >= int(self.min_rep)

class LoggedInUserUiObject(UiObjectUserLevelBase):
    def show_to(self, user):
        return user.is_authenticated()

class PublicUiObject(UiObjectUserLevelBase):
    pass



class UiObjectArgument(object):
    def __init__(self, argument):
        self.argument = argument

    def __call__(self, context):
        if callable(self.argument):
            return self.argument(context)
        else:
            return self.argument


class UiObjectBase(object):
    def __init__(self, user_level=None, weight=500):
        self.user_level = user_level or PublicUiObject()
        self.weight = weight

    def can_render(self, context):
        return self.user_level.show_to(context['request'].user)

    def render(self, context):
        return ''

class UiLoopObjectBase(UiObjectBase):
    def update_context(self, context):
        pass



class UiLinkObject(UiObjectBase):
    def __init__(self, text, url, attrs=None, pre_code='', post_code='', user_level=None, weight=500):
        super(UiLinkObject, self).__init__(user_level, weight)
        self.text = UiObjectArgument(text)
        self.url = UiObjectArgument(url)
        self.attrs = UiObjectArgument(attrs or {})
        self.pre_code = UiObjectArgument(pre_code)
        self.post_code = UiObjectArgument(post_code)

    def render(self, context):
        return "%s %s %s" % (self.pre_code(context),
            html.hyperlink(self.url(context), self.text(context), **self.attrs(context)),
            self.post_code(context))


class UiLoopContextObject(UiLoopObjectBase):
    def __init__(self, loop_context, user_level=None, weight=500):
        super(UiLoopContextObject, self).__init__(user_level, weight)
        self.loop_context = UiObjectArgument(loop_context)

    def update_context(self, context):
        context.update(self.loop_context(context))


class UiTopPageTabObject(UiLoopObjectBase):
    def __init__(self, tab_name, tab_title, url_pattern, weight):
        super(UiTopPageTabObject, self).__init__(weight=weight)
        self.tab_name = tab_name
        self.tab_title = tab_title
        self.url_pattern = url_pattern

    def update_context(self, context):
        context.update(dict(
            tab_name=self.tab_name,
            tab_title=self.tab_title,
            tab_url=reverse(self.url_pattern)
        ))
