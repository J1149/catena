"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 3.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
import logging
import os
import sys


LOGIN_URL = 'users:login'
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = os.path.join(BASE_DIR, 'static_content')
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['CATENA_DJANGO_SECRET']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['0.0.0.0', 'localhost', os.environ['BACKEND_HOST']]

DEPLOYMENT_ENV_DEV = 'development'
DEPLOYMENT_ENV_PROD = 'production'
DEPLOYMENT_ENV_STAG = 'staging'

DEPLOYMENT_ENV = os.environ['DEPLOYMENT_ENVIRONMENT']


def is_in_cloud(deployment_env):
    if deployment_env == DEPLOYMENT_ENV_PROD:
        return True
    elif deployment_env == DEPLOYMENT_ENV_STAG:
        return True
    elif deployment_env == DEPLOYMENT_ENV_DEV:
        return False
    else:
        raise Exception(f"DEPLOYMENT_ENV: {DEPLOYMENT_ENV} NOT RECOGNIZED.")


get_port = lambda port: ':' + str(port) if port != 80 else ''
SCHEME = os.environ['SCHEME']

BACKEND_PORT = get_port(int(os.environ['BACKEND_PORT']))
BACKEND_DOMAIN = SCHEME + os.environ['BACKEND_HOST'] + BACKEND_PORT + '/'

PAIPASS_PORT = get_port(int(os.environ['PAIPASS_PORT']))
PAIPASS_DOMAIN = SCHEME + os.environ['PAIPASS_HOST'] + PAIPASS_PORT + '/'

# This is more for internal development than anything else but
# it will still be required in prod.
# the gist is, catena is behind its own docker-compose system which has its own network
# it has access to. this network can't access the same localhost that the frontend
# has access to. catena relies on a network bridge to paipass to reach paipass
# paipass has it's own internal name for the backend service which differs from the name
# the frontend uses to access paipass (namely, the frontend access paipass through localhost;
# whereas catena accesses through its docker-compose internal name, backend)
PAIPASS_API_PORT = get_port(int(os.environ['PAIPASS_API_PORT']))
PAIPASS_API_DOMAIN = SCHEME + os.environ['PAIPASS_API_HOST'] + PAIPASS_API_PORT + '/'

if is_in_cloud(DEPLOYMENT_ENV.lower()):

    DEBUG = False
    # A tuple representing a HTTP header/value combination that signifies
    # a request is secure. This controls the behavior of the request
    # object’s is_secure() method.
    #
    # By default, is_secure() determines if a request is secure by
    # confirming that a requested URL uses https://. This method is
    # important for Django’s CSRF protection, and it may be used by
    # your own code or third-party apps.
    #
    # If your Django app is behind a proxy, though, the proxy may be
    # “swallowing” whether the original request uses HTTPS or not.
    # If there is a non-HTTPS connection between the proxy and Django
    # then is_secure() would always return False – even for requests
    # that were made via HTTPS by the end user. In contrast, if there
    # is an HTTPS connection between the proxy and Django then is_secure()
    # would always return True – even for requests that were made originally
    # via HTTP.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # The domain to use for session cookies. Set this to a string such as
    # "example.com" for cross-domain cookies, or use None for a standard domain
    # cookie.
    #
    # Be cautious when updating this setting on a production site. If you update
    # this setting to enable cross-domain cookies on a site that previously used
    # standard domain cookies, existing user cookies will be set to the old domain.
    # This may result in them being unable to log in as long as these cookies persist.
    SESSION_COOKIE_DOMAIN = '.' + os.environ['BACKEND_HOST'] + BACKEND_PORT
    # The domain to be used when setting the CSRF cookie. This can be
    # useful for easily allowing cross-subdomain requests to be
    # excluded from the normal cross site request forgery protection.
    # It should be set to a string such as "example.com" to allow a
    # POST request from a form on one subdomain to be accepted by a
    # view served from another subdomain.
    CSRF_COOKIE_DOMAIN = '.' + os.environ['BACKEND_HOST'] + BACKEND_PORT
    # Whether to use HttpOnly flag on the CSRF cookie. If this is set to True,
    # client-side JavaScript will not be able to access the CSRF cookie.
    #
    # Designating the CSRF cookie as HttpOnly doesn’t offer any practical
    # protection because CSRF is only to protect against cross-domain attacks.
    # If an attacker can read the cookie via JavaScript, they’re already on the
    # same domain as far as the browser knows, so they can do anything they like
    # anyway. (XSS is a much bigger hole than CSRF.)
    CSRF_COOKIE_HTTPONLY = False
    # Whether to use HttpOnly flag on the language cookie. If this is set to True,
    # client-side JavaScript will not be able to access the language cookie.
    SESSION_COOKIE_HTTPONLY = False
    # Whether to use a secure cookie for the CSRF cookie. If this is set to True,
    # the cookie will be marked as “secure”, which means browsers may ensure that
    # the cookie is only sent with an HTTPS connection.
    CSRF_COOKIE_SECURE = True

    # Whether to use a secure cookie for the session cookie. If this is set to True,
    # the cookie will be marked as “secure”, which means browsers may ensure that
    # the cookie is only sent under an HTTPS connection.
    #
    # Leaving this setting off isn’t a good idea because an attacker could capture
    # an unencrypted session cookie with a packet sniffer and use the cookie to
    # hijack the user’s session.
    SESSION_COOKIE_SECURE = True

else:
    DEBUG = True
    SESSION_COOKIE_DOMAIN = os.environ['BACKEND_HOST']
    SESSION_COOKIE_NAME = BACKEND_PORT





# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrap4',
    'corsheaders',
    'rest_framework',
    'users.apps.UsersConfig',
    'assets.apps.AssetsConfig',
    'django_messages.apps.DjangoMessagesConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'users.middleware.RequireLoginMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(CONTENT_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django_messages.context_processors.inbox'
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'
AUTH_USER_MODEL = 'users.CatenaUser'

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['CATENA_DB_NAME'],
        'USER': os.environ['SQL_USER'],
        'PASSWORD': os.environ['SQL_PASS'],
        'HOST': os.environ['SQL_HOST'],
        'PORT': os.environ['SQL_PORT']
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

LOG_FILE_PATH = os.path.join(BASE_DIR, 'logs', 'logs.txt')
lfp_dirpath = os.path.dirname(LOG_FILE_PATH)
if not os.path.exists(lfp_dirpath):
    os.makedirs(lfp_dirpath)

fh = logging.FileHandler(LOG_FILE_PATH)
fh.setLevel(logging.DEBUG)

logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
fh.setFormatter(logFormatter)

LOGGER.addHandler(fh)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(logFormatter)
LOGGER.addHandler(stdout_handler)

logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_ROOT = os.path.join(CONTENT_DIR, 'static')
STATIC_URL = '/static/'

MEDIA_ROOT = os.path.join(CONTENT_DIR, 'media')
MEDIA_URL = '/media/'

STATICFILES_DIRS = [
    os.path.join(CONTENT_DIR, 'assets'),
]

LOCALE_PATHS = [
    os.path.join(CONTENT_DIR, 'locale')
]


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ]
}

PAIPASS_REQ_KEY_NAMES = ['email', 'phone', 'name', 'paicoin_address']
PAIPASS_REQ_SCOPES = []
PAIPASS_REQ_DATA_URLS = []
for key_name in PAIPASS_REQ_KEY_NAMES:
    PAIPASS_REQ_SCOPES.append(f'READ_ALL.PAIPASS.{key_name}')
    PAIPASS_REQ_DATA_URLS.append(PAIPASS_API_DOMAIN + f'attributes/paipass/{key_name}/')


CATENA_PAIPASS_NAMESPACE = 'catena'

CATENA_REQ_KEY_NAMES = ['AccountType']
CATENA_REQ_SCOPES = []
CATENA_REQ_DATA_URLS = []
for key_name in CATENA_REQ_KEY_NAMES:
    CATENA_REQ_SCOPES.append(f'READ_ALL.CATENA.{key_name}')
    CATENA_REQ_DATA_URLS.append(PAIPASS_API_DOMAIN + f'attributes/{CATENA_PAIPASS_NAMESPACE}/{key_name}/')

REQ_SCOPES = []
REQ_SCOPES.extend(PAIPASS_REQ_SCOPES)
REQ_SCOPES.extend(CATENA_REQ_SCOPES)

REQ_DATA_URLS = []
REQ_DATA_URLS.extend(PAIPASS_REQ_DATA_URLS)
REQ_DATA_URLS.extend(CATENA_REQ_DATA_URLS)

OAUTH_CALLBACK_URL = BACKEND_DOMAIN + 'users/login-token/'
PAIPASS_SSO_CLIENT_ID = os.environ['PAIPASS_SSO_CLIENT_ID']
PAIPASS_SSO_CLIENT_SECRET = os.environ['PAIPASS_SSO_CLIENT_SECRET']
CATENA_SCHEMA_ASSET_UUID = os.environ['CATENA_SCHEMA_ASSET_UUID']


PAIPASS_DEV_EMAIL = os.environ['DEV_EMAIL']
PAIPASS_DEV_PASS = os.environ['DEV_PASS']

