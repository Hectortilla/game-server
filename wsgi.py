import os

from django.core.wsgi import get_wsgi_application
from environment import environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.%s" % environment)

application = get_wsgi_application()
