import json
import environ
import logging
import socket


# now that setting are deep inside the file structure, we need to manually dig ourselves out
APPS_DIR = environ.Path(__file__) - 3

env = environ.Env()

DEBUG = True

# add admins of the form:
#    ('Ben Adida', 'ben@adida.net'),
# if you want to be emailed about errors.
ADMINS = ()

MANAGERS = ADMINS

# is this the master Helios web site?
MASTER_HELIOS = True

# show ability to log in? (for example, if the site is mostly used by voters)
# if turned off, the admin will need to know to go to /auth/login manually
SHOW_LOGIN_OPTIONS = True

# sometimes, when the site is not that social, it's not helpful
# to display who created the election
SHOW_USER_INFO = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "helios",
        "HOST": env("POSTGRES_HOST", default=""),
        "PORT": env("POSTGRES_PORT", default=""),
        "USER": env("POSTGRES_USER", default=""),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
    }
}


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "UTC"

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en-us"

SITE_ID = 1


# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ""

# *********************** STATIC ***********************

STATIC_URL = "/static/"
STATICFILES_DIRS = [str(APPS_DIR("static"))]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Make this unique, and don't share it with anybody.
SECRET_KEY = env("DJANGO_SECRET_KEY")


SESSION_COOKIE_HTTPONLY = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

MIDDLEWARE = [
    # secure a bunch of things
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = "urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            str(APPS_DIR.path("templates")),
            str(APPS_DIR),

        ],
        "OPTIONS": {
            "debug": DEBUG,
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            'context_processors': [
                'django.template.context_processors.request',
            ]
        }
    },
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backend.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackends',
]


INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.messages",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "debug_toolbar",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",

    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',

    "helios_auth.apps.HeliosAuthConfig",
    "helios.apps.HeliosConfig",
    "server_ui.apps.ServerUiConfig",
)

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': env('GOOGLE_CLIENT_ID', default=''),
            'secret': env('GOOGLE_CLIENT_SECRET', default=''),
            'key': '',
        }
    },
    'github': {
        'SCOPE': [
            'user',
        ]
    }
}

INTERNAL_IPS = ['127.0.0.1']

# tricks to have debug toolbar when developing with docker
ip = socket.gethostbyname(socket.gethostname())
INTERNAL_IPS += [ip[:-1] + "1"]

##
## HELIOS
##


MEDIA_ROOT = str(APPS_DIR.path("media"))

# a relative path where voter upload files are stored
VOTER_UPLOAD_REL_PATH = "voters/%Y/%m/%d"

# Change your email settings
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="ben@adida.net")
DEFAULT_FROM_NAME = env("DEFAULT_FROM_NAME", default="Ben for Helios")
SERVER_EMAIL = "%s <%s>" % (DEFAULT_FROM_NAME, DEFAULT_FROM_EMAIL)

LOGIN_URL = "/auth/"
LOGOUT_ON_CONFIRMATION = True


ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# The two hosts are here so the main site can be over plain HTTP
# while the voting URLs are served over SSL.
URL_HOST = env("URL_HOST", default="http://localhost:8000").rstrip("/")

# IMPORTANT: you should not change this setting once you've created
# elections, as your elections' cast_url will then be incorrect.
# SECURE_URL_HOST = "https://localhost:8443"
SECURE_URL_HOST = env("SECURE_URL_HOST", default=URL_HOST).rstrip("/")

# election stuff
SITE_TITLE = env("SITE_TITLE", default="Helios Voting")
MAIN_LOGO_URL = env("MAIN_LOGO_URL", default="/static/logo.png")
ALLOW_ELECTION_INFO_URL = env("ALLOW_ELECTION_INFO_URL", default="0") == "1"

# FOOTER links
FOOTER_LINKS = json.loads(env("FOOTER_LINKS", default="[]"))
FOOTER_LOGO_URL = env("FOOTER_LOGO_URL", default=None)

WELCOME_MESSAGE = env("WELCOME_MESSAGE", default="This is the default message")

HELP_EMAIL_ADDRESS = env("HELP_EMAIL_ADDRESS", default="help@heliosvoting.org")

AUTH_TEMPLATE_BASE = "server_ui/templates/base.html"
HELIOS_TEMPLATE_BASE = "server_ui/templates/base.html"
HELIOS_ADMIN_ONLY = False
HELIOS_VOTERS_UPLOAD = True
HELIOS_VOTERS_EMAIL = True

# are elections private by default?
HELIOS_PRIVATE_DEFAULT = False

# authentication systems enabled
# AUTH_ENABLED_AUTH_SYSTEMS = ['password','facebook','twitter', 'google', 'yahoo']
AUTH_ENABLED_AUTH_SYSTEMS = env("AUTH_ENABLED_AUTH_SYSTEMS", default="google").split(
    ","
)
AUTH_DEFAULT_AUTH_SYSTEM = env("AUTH_DEFAULT_AUTH_SYSTEM", default=None)

# google
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")

# facebook
FACEBOOK_APP_ID = env("FACEBOOK_APP_ID", default="")
FACEBOOK_API_KEY = env("FACEBOOK_API_KEY", default="")
FACEBOOK_API_SECRET = env("FACEBOOK_API_SECRET", default="")

# twitter
TWITTER_API_KEY = ""
TWITTER_API_SECRET = ""
TWITTER_USER_TO_FOLLOW = "heliosvoting"
TWITTER_REASON_TO_FOLLOW = "we can direct-message you when the result has been computed in an election in which you participated"

# the token for Helios to do direct messaging
TWITTER_DM_TOKEN = {
    "oauth_token": "",
    "oauth_token_secret": "",
    "user_id": "",
    "screen_name": "",
}

# LinkedIn
LINKEDIN_API_KEY = ""
LINKEDIN_API_SECRET = ""

# CAS (for universities)
CAS_USERNAME = env("CAS_USERNAME", default="")
CAS_PASSWORD = env("CAS_PASSWORD", default="")
CAS_ELIGIBILITY_URL = env("CAS_ELIGIBILITY_URL", default="")
CAS_ELIGIBILITY_REALM = env("CAS_ELIGIBILITY_REALM", default="")

# Clever
CLEVER_CLIENT_ID = env("CLEVER_CLIENT_ID", default="")
CLEVER_CLIENT_SECRET = env("CLEVER_CLIENT_SECRET", default="")

# email server
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = int(env("EMAIL_PORT", default="2525"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default="0") == "1"

# to use AWS Simple Email Service
# in which case environment should contain
# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
if env("EMAIL_USE_AWS", default="0") == "1":
    EMAIL_BACKEND = "django_ses.SESBackend"

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

# set up django-celery
# BROKER_BACKEND = "kombu.transport.DatabaseTransport"

CELERY_BROKER_URL = "amqp://localhost"
CELERY_TASKS_ALWAYS_EAGER = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_PRELOAD = True

CORS_ORIGIN_ALLOW_ALL = True
