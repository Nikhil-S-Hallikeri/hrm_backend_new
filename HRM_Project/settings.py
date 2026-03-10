from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-^gh#$wo2(!g8zm!y(dniy$#b(88$a@d2!$#=%@q!o+znbl2$+p'
DEBUG = True

ALLOWED_HOSTS = ["*"]
#'127.0.0.1',"192.168.0.110","192.168.0.126"

INSTALLED_APPS = [

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "HRM_App",
    "EMS_App",
    "LMS_App",
    "payroll_app",
    "Contract_Emp_App",
    "corsheaders",
    "rest_framework",
    'django_filters',
    "django_apscheduler",
    # 'rest_framework_api_key',
    "celery",
    'django_celery_beat',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware', 
    
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

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# DATABASES = {
#      'default': {  
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'hrm',
#         'USER': 'root', 
#         'PASSWORD': 'system123',
#         'HOST': '127.0.0.1',  
#         'PORT': '3306',  
#         'CONN_MAX_AGE': 600,    
#     }
# }




# DATABASES = {
#     'default': 
#     {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'HRM',
#         'USER': 'MeridaDatabase',
#         'PASSWORD': 'Team@4321',
#         'HOST': '62.72.59.145',
#         'PORT': '3306',
#     }
# }




DATABASES = {
     'default': {  
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'hrm',
        'USER': 'root', 
        'PASSWORD': 'Nikhil@2001',
        'HOST': '127.0.0.1',  
        'PORT': '3306',  
        'CONN_MAX_AGE': 600,    
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

CSRF_TRUSTED_ORIGINS = [
    'http://62.72.59.145',
    'https://hrmbackendapi.meridahr.com',
    # Add more trusted IP addresses as needed
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

WKHTMLTOPDF_PATH = 'HRM_Project/wkhtmltopdf'

# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_HOST_USER = 'info@meridatechminds.com'
# EMAIL_HOST_PASSWORD = 'aeaz lghp zbyq gocd'
# EMAIL_USE_SSL = True
# EMAIL_PORT = 465
# EMAIL_USE_TLS = False


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'nikhilhallikeri@gmail.com'
EMAIL_HOST_PASSWORD = 'wlprmiwusaxxaxur'
EMAIL_USE_SSL = True
EMAIL_PORT = 465
EMAIL_USE_TLS = False



DAS_URL = 'https://dasbackendapi.meridahr.com/'


# set the celery broker url
# CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_BROKER_URL ="redis://default:tdwMOHfcoENfdcFapildXhcucDdOPFgT@ballast.proxy.rlwy.net:39739"

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

"""steps to run redies in cmd"""
# wsl --install
# sudo apt update
# if not installd redis  sudo apt install redis-server


