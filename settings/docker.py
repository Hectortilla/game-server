import re

from settings import *

DEBUG = True
HOST = 'localhost'
PORT = '8080'
HOST_PORT = HOST + ':' + PORT
ALLOWED_HOSTS = [
    '127.0.0.1',
    HOST,
    'launch.playcanvas.com'
]

SECRET_KEY = 'foo'

CORS_ORIGIN_ALLOW_ALL = True

# for staging/production:
# ALLOWED_CIDR_NETS = ['10.20.0.0/16']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s module=%(module)s, '
                      'process_id=%(process)d, %(message)s'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'worker': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        },
    },
}

DATABASE_DEFAULT = {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'broadcaster',
    'USER': 'development',
    'PASSWORD': 'development',

    'HOST': 'mysql',
    'PORT': '3306',
    'OPTIONS': {
        'init_command': "SET sql_mode='STRICT_ALL_TABLES'",
        'charset': 'utf8mb4'
    }
}

DATABASES = {
    'default': DATABASE_DEFAULT
}

REDIS_HOST = 'redis'
REDIS_PORT = 6379
REDIS_ADDRESS = '{}:{}'.format(REDIS_HOST, REDIS_PORT)

DJANGO_REDIS_BACKEND_DB = 0
CELERY_REDIS_BACKEND_DB = 1

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{}/{}".format(
            REDIS_ADDRESS, DJANGO_REDIS_BACKEND_DB
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
            "channel_capacity": {
                "http.request": 200,
                "http.response!*": 10,
                re.compile(r"^websocket.send\!.+"): 150
            }
        }
    }
}
BROKER_URL = 'redis://{}/{}'.format(REDIS_ADDRESS, CELERY_REDIS_BACKEND_DB)
CELERY_RESULT_BACKEND = 'redis://{}/{}'.format(
    REDIS_ADDRESS, CELERY_REDIS_BACKEND_DB
)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Amsterdam'

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += (
    'rest_framework.renderers.BrowsableAPIRenderer',
)

PID_DIR = '/tmp/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@localhost'
