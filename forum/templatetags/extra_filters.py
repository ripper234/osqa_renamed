from django import template
from django.utils.safestring import mark_safe
import logging

register = template.Library()

@template.defaultfilters.stringfilter
@register.filter
def collapse(input):
    return ' '.join(input.split())


@register.filter
def can_edit_post(user, post):
    return user.can_edit_post(post)


@register.filter
def decorated_int(number, cls="thousand"):
    try:
        if number > 999:
            if number > 9999:
                s = str(number)[:-3]
            else:
                s = str(number)
                s = "%s.%s" % (s[0], s[1])

            return mark_safe("<span class=\"%s\">%sk</span>" % (cls, s))
        return number
    except:
        return number

@register.filter
def or_preview(setting, request):
    if request.user.is_superuser:
        previewing = request.session.get('previewing_settings', {})
        if setting.name in previewing:
            return previewing[setting.name]

    return setting.value

@register.filter
def getval(map, key):
    return map and map.get(key, None) or None


@register.filter
def contained_in(item, container):
    return item in container