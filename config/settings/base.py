from pathlib import Path

from decouple import Csv, config
from dj_database_url import parse as db_url
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

DOTENV_PATH = BASE_DIR / ".env"

load_dotenv(DOTENV_PATH)

# SECURITY WARNING: keep the secret key used in production secret!
DEBUG = config("DEBUG", default=True, cast=bool)

SECRET_KEY = config("SECRET_KEY", default="secret-key")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*", cast=Csv())

# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "widget_tweaks",
    "django_filters",
    "constance",
    "easyaudit",
    "allauth",
    "allauth.account",
    "django_extensions",
    "rest_framework",
    "rest_framework.authtoken",
    "django_celery_beat",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.authentication.apps.AuthenticationConfig",
    "apps.customers.apps.CustomersConfig",
    "apps.users.apps.UsersConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "easyaudit.middleware.easyaudit.EasyAuditMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "apps/templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": config("DATABASE_URL", default="sqlite:///db.sqlite3", cast=db_url)  # noqa
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa  # noqa
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",  # noqa
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",  # noqa
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",  # noqa
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Chicago"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "apps/static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "apps/media"

# Translation settings
# https://docs.djangoproject.com/en/5.0/topics/i18n/translation/

LANGUAGES = (
    ("en", _("English")),
    ("es", _("Spanish")),
)

LOCALE_PATHS = [BASE_DIR / "apps/locale/"]

# Django Allauth settings
# https://django-allauth.readthedocs.io/en/latest/configuration.html

AUTH_USER_MODEL = "users.User"

SITE_ID = 1

LOGIN_URL = "/"

LOGIN_REDIRECT_URL = "/dashboard/"

ACCOUNT_SIGNUP_REDIRECT_URL = "/login/"

ACCOUNT_AUTHENTICATION_METHOD = "email"

ACCOUNT_USER_MODEL_USERNAME_FIELD = None

ACCOUNT_LOGOUT_ON_GET = True

ACCOUNT_EMAIL_REQUIRED = True

ACCOUNT_USERNAME_REQUIRED = False

ACCOUNT_EMAIL_VERIFICATION = "mandatory"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_FORMS = {"signup": "apps.authentication.forms.CustomSignupForm"}


# Django Rest Framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"
    ],
}

# Celery settings

CELERY_TIMEZONE = TIME_ZONE
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"
CELERY_BROKER_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://127.0.0.1:6379/")
