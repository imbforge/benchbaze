"""
Django settings for django_project project.

Generated by 'django-admin startproject' using Django 1.11.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os

from .private_settings import SECRET_KEY
from .private_settings import ALLOWED_HOSTS
from .private_settings import DB_NAME 
from .private_settings import DB_USER
from .private_settings import DB_PASSWORD
from .private_settings import DEBUG
from .private_settings import SERVER_EMAIL_ADDRESS
from .private_settings import SITE_ADMIN_EMAIL_ADDRESSES

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# Application definition

INSTALLED_APPS = [
    'adminactions',
    'django.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djangoql',
    'simple_history',
    'import_export',
    'collection_management',
    'user_management',
    'order_management',
    'guardian',
    'django.contrib.sites.apps.SitesConfig',
    'django.contrib.humanize.apps.HumanizeConfig',
    'django_nyt.apps.DjangoNytConfig',
    'mptt',
    'sekizai',
    'sorl.thumbnail',
    'wiki.apps.WikiConfig',
    'wiki.plugins.attachments.apps.AttachmentsConfig',
    'wiki.plugins.notifications.apps.NotificationsConfig',
    'wiki.plugins.images.apps.ImagesConfig',
    'wiki.plugins.macros.apps.MacrosConfig',
    'background_task',
    'formz',
    'record_approval',
    'my_admin',
    ]

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting' 

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend', # this is default
    'guardian.backends.ObjectPermissionBackend',
)

ROOT_URLCONF = 'django_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR + '/templates/'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                "sekizai.context_processors.sekizai",
            ],
        },
    },
]

WSGI_APPLICATION = 'django_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', 
        'NAME': DB_NAME, 
        'USER': DB_USER, 
        'PASSWORD': DB_PASSWORD,
        'HOST': 'localhost', 
        'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR,'static/')


# Media files

MEDIA_URL = '/uploads/'
MEDIA_ROOT = os.path.join(BASE_DIR,'uploads/')


#Email/SMTP settings

EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = None
EMAIL_HOST_PASSWORD = None
DEFAULT_FROM_EMAIL = SERVER_EMAIL_ADDRESS

#Email settings for error messages

SERVER_EMAIL = SERVER_EMAIL_ADDRESS
ADMINS = SITE_ADMIN_EMAIL_ADDRESSES

# Wiki settings

SITE_ID = 1
WIKI_ACCOUNT_SIGNUP_ALLOWED = False
WIKI_ACCOUNT_HANDLING = True
WIKI_MARKDOWN_HTML_WHITELIST = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em',
'i', 'li', 'ol', 'strong', 'ul', 'figure', 'figcaption', 'br', 'hr', 'p', 'div', 'img', 
'pre', 'span', 'sup', 'table', 'thead', 'tbody', 'th', 'tr', 'td', 'dl', 'dt', 'dd',
'h0', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'sub', 'sup']


# Other settings

FILE_UPLOAD_PERMISSIONS = 0o664

from django.conf.locale.en import formats as en_formats
en_formats.DATETIME_FORMAT = "j N Y, H:i:s"
en_formats.DATE_FORMAT = "j N Y"

from django.conf.locale.en_GB import formats as en_gb_formats
en_gb_formats.DATETIME_FORMAT = "j N Y, H:i:s"
en_gb_formats.DATE_FORMAT = "j N Y"

LOGIN_URL="/login/"