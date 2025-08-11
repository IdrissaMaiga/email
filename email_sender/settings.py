"""
Django settings for email_sender project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-your-secret-key-here-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'

# Disable APPEND_SLASH to prevent issues with webhook POST requests
APPEND_SLASH = False

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,email.horizoneurope.io,horizoneurope.io,sender.horizoneurope.io,13.60.195.151,testserver').split(',')

# CSRF Settings for tunnel access
CSRF_TRUSTED_ORIGINS = [
    'https://sender.horizoneurope.io',
    'https://email.horizoneurope.io', 
    'https://horizoneurope.io',
    'http://localhost:2001',
    'http://127.0.0.1:2001',
]

# CSRF Cookie Settings
CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'email_app',
    'email_monitor',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'email_sender.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'email_sender.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Check if we're running in Docker/production
if os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'email_sender_db'),
            'USER': os.getenv('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres_password_2024'),
            'HOST': os.getenv('POSTGRES_HOST', 'db'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# File upload settings for large CSV files
# Increase maximum file size for CSV uploads (100 MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 MB

# Increase maximum request body size (100 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 MB

# Increase maximum number of fields (for large CSV files with many contacts)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000  # Default is 1000

# Maximum number of files that can be uploaded (default is 100)
DATA_UPLOAD_MAX_NUMBER_FILES = 100


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Only add STATICFILES_DIRS if the static directory exists
if (BASE_DIR / 'static').exists():
    STATICFILES_DIRS = [BASE_DIR / 'static']
else:
    STATICFILES_DIRS = []

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'




# Multiple Email Sender Configurations
EMAIL_SENDERS = {
    'horizoneurope': {
        'email': 'roland.zonai@horizoneurope.io',
        'name': 'Roland Zonai - Horizon Europe IO',
        'api_key': 're_Cs5WjBoq_KQVASjgHeJv5ru1Nkuomk3BY',
        'domain': 'horizoneurope.io',
        'webhook_url': 'sender.horizoneurope.io/webhook1/',
        'webhook_secret': 'whsec_mxDD0UTbIirVJ1//WCon4NpRz4e0jotf'
    },
    'horizon_eu': {
        'email': 'roland.zonai@horizon.eu.com',
        'name': 'Roland Zonai - Horizon EU',
        'api_key': 're_2g11XipG_PZyEkMWAkwJ2eTSMbZVbk5hz',
        'domain': 'horizon.eu.com',
        'webhook_url': 'sender.horizoneurope.io/webhook2/',
        'webhook_secret': 'whsec_tAU54drStmKUyqSmDT2An08p0m3WuvSv'
    }
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'email_monitor.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'email_monitor': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Development server settings
DEFAULT_PORT = 2001
