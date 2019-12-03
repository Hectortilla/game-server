import os

import django
from channels.routing import get_default_application

from environment import environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.%s" % environment)
django.setup()
application = get_default_application()
