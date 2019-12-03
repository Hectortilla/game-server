import os
from celery import Celery

from environment import environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.%s' % environment)

from django.conf import settings

app = Celery('worker')

app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
