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
DEBUG = True

# Disable APPEND_SLASH to prevent issues with webhook POST requests
APPEND_SLASH = False

# Allow all hosts for development - NO SECURITY
ALLOWED_HOSTS = ['*']

# COMPLETELY DISABLE ALL SECURITY FEATURES
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_REFERRER_POLICY = None
X_FRAME_OPTIONS = None
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False
CSRF_COOKIE_HTTPONLY = False

# DISABLE ALL REQUEST/RESPONSE PROCESSING
USE_I18N = False
USE_L10N = False
USE_TZ = False

# ALLOW ALL CONTENT TYPES AND ORIGINS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# COMPLETELY ENABLE TUNNEL SUPPORT
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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

# MINIMAL MIDDLEWARE FOR ADMIN TO WORK - NO SECURITY AT ALL
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'email_monitor.permissive_middleware.AllowAllMiddleware',  # Allow everything through
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
# Force PostgreSQL only, never fallback to SQLite
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


# File upload settings for large CSV files - MAXIMUM PERMISSIVE
# Allow HUGE file sizes (1 GB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1 GB
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1 GB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100000  # Very high limit
DATA_UPLOAD_MAX_NUMBER_FILES = 1000  # Very high limit

# Disable all file upload security
FILE_UPLOAD_PERMISSIONS = None
FILE_UPLOAD_DIRECTORY_PERMISSIONS = None


# Disable all password validation for development - NO SECURITY
AUTH_PASSWORD_VALIDATORS = []


# Internationalization - DISABLED FOR PERFORMANCE
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = False


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

# Development server settings - COMPLETELY OPEN
DEFAULT_PORT = 2001

# DISABLE ALL REQUEST VALIDATION AND SECURITY
SILENCED_SYSTEM_CHECKS = ['security.W001', 'security.W002', 'security.W003', 'security.W004', 'security.W005', 'security.W006', 'security.W007', 'security.W008', 'security.W009', 'security.W010', 'security.W011', 'security.W012', 'security.W013', 'security.W014', 'security.W015', 'security.W016', 'security.W017', 'security.W018', 'security.W019', 'security.W020', 'security.W021', 'security.W022']

# FORCE TUNNEL COMPATIBILITY
FORCE_SCRIPT_NAME = ''
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# DISABLE ALL CONTENT SECURITY
CONTENT_SECURITY_POLICY = None
FEATURE_POLICY = None
