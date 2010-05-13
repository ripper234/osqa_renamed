import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),'markdownext'))

import forum.views

import forum.badges
import forum.subscriptions

from forum.modules import get_modules_script

get_modules_script('settings')
get_modules_script('startup')