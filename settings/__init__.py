import os

from environment import base_dir as BASE_DIR

DEBUG = False

SITE_ID = 1
ALLOWED_HOSTS = []

SITE_TITLE = 'Game-Server'
SITE_ADMIN_TITLE = '{} Administration'.format(SITE_TITLE)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.messages',

    'django.contrib.admin',
    'corsheaders',

    'apps.games',
    'apps.players',
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'allow_cidr.middleware.AllowCIDRMiddleware'
]

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [
        os.path.join(BASE_DIR, 'templates')
    ],
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'django.template.context_processors.media',
            'django.template.context_processors.static',

            'django.template.context_processors.request',
        ],
        'loaders': [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]
    },
}]

ROOT_URLCONF = 'urls'
# ASGI_APPLICATION = 'routing.application'
WSGI_APPLICATION = 'wsgi.application'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'
    }
]

PASSWORD_MIN_LENGTH = 6

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_camel.render.CamelCaseJSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_camel.parser.CamelCaseJSONParser',
    ),
    'DEFAULT_METADATA_CLASS': 'apps.main.metadata.NoMetadata'
}

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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

FILE_UPLOAD_PERMISSIONS = 0o644

SILENCED_SYSTEM_CHECKS = [
    'django_mysql.E016',  # MySQL 5.7+ is required to use JSONField
]

###

LOG_DIR = '/tmp/logs'
PID_DIR = '/tmp/pids'


SERVER_NAME = 'game-server'
WEB_SERVER_NAME = 'web-game-server'

BROADCAST_INTERVAL = .01  # in seconds
SERVER_MAIN_LOOP_INTERVAL = .01  # in seconds
SERVER_DB_KEEPALIVE = 1  # in seconds

# where the (test) client should connect to
WEBSOCKET_CLIENT_HOST = '127.0.0.1'

# where the server listens, '0.0.0.0' for network access
WEBSOCKET_SERVER_HOST = '127.0.0.1'

WEBSOCKET_SERVER_PORT = 9000


from settings.constants import *
