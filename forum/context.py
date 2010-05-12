from forum import settings
from django.conf import settings as djsettings

def application_settings(context):
    my_settings = {
        'APP_TITLE' : settings.APP_TITLE,
        'APP_SHORT_NAME' : settings.APP_SHORT_NAME,
        'SHOW_WELCOME_BOX' : settings.SHOW_WELCOME_BOX,
        'APP_URL'   : settings.APP_URL,
        'APP_KEYWORDS' : settings.APP_KEYWORDS,
        'APP_DESCRIPTION' : settings.APP_DESCRIPTION,
        'APP_INTRO' : settings.APP_INTRO,
        'APP_LOGO' : settings.APP_LOGO,
        'EMAIL_VALIDATION': 'off',
        'FEEDBACK_SITE_URL': settings.FEEDBACK_SITE_URL,
        'FORUM_SCRIPT_ALIAS': djsettings.FORUM_SCRIPT_ALIAS,
        'LANGUAGE_CODE': djsettings.LANGUAGE_CODE,
        'GOOGLE_SITEMAP_CODE':settings.GOOGLE_SITEMAP_CODE,
        'GOOGLE_ANALYTICS_KEY':settings.GOOGLE_ANALYTICS_KEY,
        'WIKI_ON':settings.WIKI_ON,
        'OSQA_SKIN':djsettings.OSQA_DEFAULT_SKIN,
        'APP_FAVICON':settings.APP_FAVICON,
        'OSQA_VERSION': settings.OSQA_VERSION,
        'ADMIN_MEDIA_PREFIX': djsettings.ADMIN_MEDIA_PREFIX,
        'SVN_REVISION': settings.SVN_REVISION,
        }
    return {'settings':my_settings}

def auth_processor(request):
    """
    Returns context variables required by apps that use Django's authentication
    system.

    If there is no 'user' attribute in the request, uses AnonymousUser (from
    django.contrib.auth).
    """
    if hasattr(request, 'user'):
        user = request.user
        if user.is_authenticated():
            messages = user.message_set.all()
        else:
            messages = None
    else:
        from django.contrib.auth.models import AnonymousUser
        user = AnonymousUser()
        messages = None

    from django.core.context_processors import PermWrapper
    return {
        'user': user,
        'messages': messages,
        'perms': PermWrapper(user),
    }
