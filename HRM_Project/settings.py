from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if present
env_file = BASE_DIR / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip()

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-^gh#$wo2(!g8zm!y(dniy$#b(88$a@d2!$#=%@q!o+znbl2$+p')
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', '*').split(',') if host.strip()]
#'127.0.0.1',"192.168.0.110","192.168.0.126"

INSTALLED_APPS = [
    # --- Django Core ---
    'daphne',               # Must be FIRST for ASGI/WebSocket support
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # --- HRM Apps (existing) ---
    "HRM_App",
    "EMS_App",
    "LMS_App",
    "payroll_app",
    "Contract_Emp_App",

    # --- Third-party (existing) ---
    "corsheaders",
    "rest_framework",
    'django_filters',
    "django_apscheduler",
    "celery",
    'django_celery_beat',

    # --- WhatsApp Module (NEW) ---
    'channels',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'whatsapp_app',
    'chatbot_app',
    'facebook_app',
]


MIDDLEWARE = [
    #19/6/26
    'corsheaders.middleware.CorsMiddleware',
    'whatsapp_app.middleware.WhatsAppConfigMiddleware',  # WA config per-request (NEW)
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_COOKIE_SECURE = False

CORS_ALLOW_ALL_ORIGINS =True

CORTS_ALLOWED_ORIGINS = [
    "*"
]
X_FRAME_OPTION="SAMEORIGIN"

SESSION_COOKIE_SECURE = False

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_CREDENTIALS = True


ROOT_URLCONF = 'HRM_Project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ["HRM_App/templates"],
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

WSGI_APPLICATION = 'HRM_Project.wsgi.application'

DATABASES = {
     'default': {  
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.environ.get('DB_NAME', 'hrm'),
        'USER': os.environ.get('DB_USER', 'root'), 
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),  
        'PORT': os.environ.get('DB_PORT', '3306'),  
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', 600)),    
    }
}




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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True

import os



MEDIA_URL = '/media/'
MEDIA_ROOT=os.path.join('media')

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join('static')

CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://62.72.59.145,https://hrmbackendapi.meridahr.com').split(',') if origin.strip()]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

WKHTMLTOPDF_PATH = 'HRM_Project/wkhtmltopdf'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True').lower() in ('true', '1', 'yes')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 465))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False').lower() in ('true', '1', 'yes')


DAS_URL = 'https://das.meridahr.com/'


# set the celery broker url
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')

CELERY_ACCEPT_CONTENT=['json']

CELERY_TASK_SERIALIZER='json'

CELERY_IMPORTS = ("LMS_App.tasks",)

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True


# run celery 
# celery -A delivery_project worker --loglevel=info --pool=eventlet
# celery -A CeleryProject worker --pool=solo --loglevel=info
# celery -A CeleryProject beat --loglevel=info

# celery -A CeleryProject beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# # set the celery result backend
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# # set the celery timezone
# CELERY_TIMEZONE = 'UTC'



# =============================================================================
# WhatsApp Module Settings (NEW)
# =============================================================================

# ASGI Application (required for WebSocket / Django Channels real-time inbox)
ASGI_APPLICATION = 'HRM_Project.asgi.application'

# Channel Layers — InMemory for local dev, Redis for production
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
        # For production with Redis, switch to:
        # 'BACKEND': 'channels_redis.core.RedisChannelLayer',
        # 'CONFIG': {'hosts': [('127.0.0.1', 6379)]},
    },
}

# DRF — WhatsApp module uses HRM employee auth
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'whatsapp_app.authentication.HRMEmployeeAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',  # WA webhook must be public; views set own perms
    ),
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}

# SimpleJWT (used by token_blacklist app)
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

# Meta / WhatsApp Cloud API
META_APP_ID = os.environ.get('META_APP_ID', '')
META_APP_SECRET = os.environ.get('META_APP_SECRET', '')
META_CONFIG_ID = os.environ.get('META_CONFIG_ID', '977728578634087')
META_CONFIG_ID_COEXISTENCE = os.environ.get('META_CONFIG_ID_COEXISTENCE', '')
GRAPH_API_VERSION = os.environ.get('GRAPH_API_VERSION', 'v25.0')
DJANGO_RUNSERVER_ADDR = os.environ.get('DJANGO_RUNSERVER_ADDR', 'https://hrmbackendapi.meridahr.com')
WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '1295734776086368')

# FastAPI Chatbot microservice (optional — Phase 2)
CHATBOT_SERVICE_URL = os.environ.get('CHATBOT_SERVICE_URL', 'http://localhost:8002')
CHATBOT_SERVICE_TIMEOUT = int(os.environ.get('CHATBOT_SERVICE_TIMEOUT', 30))

# Extra CORS headers needed by WA module
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
    'cache-control', 'pragma',
    'x-whatsapp-config-id',   # WA config selector
    'x-hrm-employee-id',      # HRM employee auth
    'x-tenant-email', 'x-user-email',
]

"""steps to run redies in cmd"""
# wsl --install
# sudo apt update
# if not installd redis  sudo apt install redis-server
