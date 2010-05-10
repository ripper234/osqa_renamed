from forum.settings.base import Setting
from forum.settings.extkeys import EXT_KEYS_SET
from django.utils.translation import ugettext_lazy as _

WORDPRESS_API_KEY = Setting('WORDPRESS_API_KEY', '', EXT_KEYS_SET, dict(
label = _("Wordpress API key"),
help_text = _("Your Wordpress API key. You can get one at <a href='http://wordpress.com/'>http://wordpress.com/</a>"),
required=False))
