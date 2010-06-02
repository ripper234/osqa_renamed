# encoding:utf-8
# Django settings for lanai project.
import os.path
import sys

SITE_ID = 1

ADMIN_MEDIA_PREFIX = '/admin_media/'
SECRET_KEY = '$oo^&_m&qwbib=(_4m_n*zn-d=g#s0he5fx9xonnym#8p6yigm'
# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'forum.modules.module_templates_loader',
    'forum.skins.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = [
    #'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.locale.LocaleMiddleware',
    #'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    #'django.middleware.cache.FetchFromCacheMiddleware',
    'forum.middleware.extended_user.ExtendedUser',
    #'django.middleware.sqlprint.SqlPrintingMiddleware',
    'forum.middleware.anon_user.ConnectToSessionMessagesMiddleware',
    'forum.middleware.request_utils.RequestUtils',
    'forum.middleware.cancel.CancelActionMiddleware',
    #'recaptcha_django.middleware.ReCaptchaMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
]

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'forum.context.application_settings',
    #'django.core.context_processors.i18n',
    'forum.user_messages.context_processors.user_messages',#must be before auth
    'django.core.context_processors.auth', #this is required for admin
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__),'forum','skins').replace('\\','/'),
)

#UPLOAD SETTINGS
FILE_UPLOAD_TEMP_DIR = os.path.join(os.path.dirname(__file__), 'tmp').replace('\\','/')
FILE_UPLOAD_HANDLERS = ("django.core.files.uploadhandler.MemoryFileUploadHandler",
 "django.core.files.uploadhandler.TemporaryFileUploadHandler",)
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
# for user upload
ALLOW_FILE_TYPES = ('.jpg', '.jpeg', '.gif', '.bmp', '.png', '.tiff')
# unit byte
ALLOW_MAX_FILE_SIZE = 1024 * 1024



def check_local_setting(name, value):
    local_vars = locals()
    if name in local_vars and local_vars[name] == value:
        return True
    else:
        return False

SITE_SRC_ROOT = os.path.dirname(__file__)
LOG_FILENAME = 'django.osqa.log'

#for logging
import logging
logging.basicConfig(
    filename=os.path.join(SITE_SRC_ROOT, 'log', LOG_FILENAME),
    level=logging.ERROR,
    format='%(pathname)s TIME: %(asctime)s MSG: %(filename)s:%(funcName)s:%(lineno)d %(message)s',
)

#ADMINS and MANAGERS
ADMINS = (('Forum Admin', 'forum@example.com'),)
MANAGERS = ADMINS

DEBUG = True
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': True
}
TEMPLATE_DEBUG = DEBUG
INTERNAL_IPS = ('127.0.0.1',)

if True:

    DATABASE_NAME =  'meta_rep'          # Or path to database file if using sqlite3.
    DATABASE_USER = 'postgres'               # Not used with sqlite3.
    DATABASE_PASSWORD = 'postgres'               # Not used with sqlite3.
    DATABASE_ENGINE = 'postgresql_psycopg2'  #mysql, etc
    DATABASE_HOST = 'localhost'
    DATABASE_PORT = ''
else:
    DATABASE_NAME =  'd:/stuff/sxtest.db'#'sxtest2rep'          # Or path to database file if using sqlite3.
    DATABASE_USER = ''               # Not used with sqlite3.
    DATABASE_PASSWORD = ''               # Not used with sqlite3.
    DATABASE_ENGINE = 'sqlite3'  #mysql, etc
    DATABASE_HOST = ''
    DATABASE_PORT = ''

#CACHE_BACKEND = 'file://%s' % os.path.join(os.path.dirname(__file__),'cache').replace('\\','/')
#CACHE_BACKEND = 'dummy://'
CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

APP_URL = 'http://' #used by email notif system and RSS

#LOCALIZATIONS
TIME_ZONE = 'America/New_York'

###########################
#
#   this will allow running your forum with url like http://site.com/forum
#
#   FORUM_SCRIPT_ALIAS = 'forum/'
#
FORUM_SCRIPT_ALIAS = '' #no leading slash, default = '' empty string


#OTHER SETTINGS

USE_I18N = False
LANGUAGE_CODE = 'en'

EMAIL_VALIDATION = 'off' #string - on|off

DJANGO_VERSION = 1.1
RESOURCE_REVISION=4
OSQA_DEFAULT_SKIN = 'default'

DISABLED_MODULES = ['books', 'recaptcha', 'project_badges']


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    'django.contrib.markup',
    'forum',
]

if DEBUG:
    try:
        import debug_toolbar
        MIDDLEWARE_CLASSES.append('debug_toolbar.middleware.DebugToolbarMiddleware')
        INSTALLED_APPS.append('debug_toolbar')
    except:
        pass

try:
    import south
    INSTALLED_APPS.append('south')
except:
    pass

if not DEBUG:
    try:
        import rosetta
        INSTALLED_APPS.append('rosetta')
    except:
        pass

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend',]



