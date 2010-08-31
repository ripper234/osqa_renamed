from django import template
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
def cnprog_intword(number):
    try:
        if 1000 <= number < 10000:
            string = str(number)[0:1]
            return "<span class=""thousand"">%sk</span>" % string
        else:
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