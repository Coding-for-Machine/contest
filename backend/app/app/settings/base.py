# app/settings/base.py
import os
from pathlib import Path
from decouple import config, Csv
from django_bolt import FileSize

# settings/ ichida bo'lgani uchun .parent.parent.parent
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
    'django_celery_results',
    'django_bolt',
    'contests',
    'problems',
    'submissions',
    'baseuser',
    'quizs',
    'courses.apps.CoursesConfig',
    'video',
    'status',
    'payment',
    'certificate.apps.CertificateConfig',
    'notifications.apps.NotificationsConfig',
    'mdeditor',
    'paytechuz.integrations.django',
    'centers.apps.CentersConfig',
]

from .payteach import payteach
PAYTECH_API_KEY = "5cf1ea79-737f-472c-ab8a-fa3c690b7a13"
PAYTECHUZ = payteach

X_FRAME_OPTIONS = 'SAMEORIGIN'

MDEDITOR_CONFIGS = {
    'default': {
        'width': '100%',
        'height': 700,
        'toolbar': ["undo", "redo", "|", "bold", "del", "italic", "quote",
                    "ucwords", "uppercase", "lowercase", "|",
                    "h1", "h2", "h3", "h5", "h6", "|",
                    "list-ul", "list-ol", "hr", "|",
                    "link", "reference-link", "image", "code",
                    "preformatted-text", "code-block", "table", "datetime",
                    "emoji", "html-entities", "pagebreak", "goto-line", "|",
                    "help", "info", "||", "preview", "watch", "fullscreen"],
        'upload_image_formats': ["jpg", "jpeg", "gif", "png", "bmp", "webp", "svg"],
        'image_folder': 'editor',
        'theme': 'default',
        'preview_theme': 'default',
        'editor_theme': 'default',
        'toolbar_autofixed': False,
        'search_replace': True,
        'emoji': True,
        'tex': True,
        'flow_chart': True,
        'sequence': True,
        'watch': True,
        'lineWrapping': True,
        'lineNumbers': True,
        'language': 'en'
    }
}


AUTH_SERVER_BASE_URL = config("AUTH_SERVICE")

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST', default='localhost'),
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
    }
}
# Redis - to'liq .env dan
REDIS_HOST = config('REDIS_HOST', default='127.0.0.1')
REDIS_PORT = config('REDIS_PORT', default='6379')
REDIS_PASSWORD = config('REDIS_PASSWORD', default=None)

# Password bilan yoki usiz URL yasash
_redis_auth = f":{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""
REDIS_URL = f"redis://{_redis_auth}{REDIS_HOST}:{REDIS_PORT}"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
            "PASSWORD": REDIS_PASSWORD,  # None bo'lsa e'tiborga olinmaydi
        }
    }
}

# Celery ham shu URL dan foydalansin
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=f"{REDIS_URL}/0")
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

import os
from decouple import config, Csv  # Agar python-decouple ishlatayotgan bo'lsangiz

# DATABASES & CONNECTIONS
CONN_MAX_AGE = 600
# Tizim hodisalari (Signals) faollashtirildi
BOLT_EMIT_SIGNALS = True
# Ishlab chiqish jarayonida majburiy polling (so'rov yuborish) rejimini yoqish
BOLT_DEV_FORCE_POLLING = True
# 500 MB = 500 * 1024 * 1024 bayt
BOLT_MAX_UPLOAD_SIZE = 500 * 1024 * 1024  
# RAM chegarasi: 50 MB (50MB gacha xotirada, undan kattasi vaqtinchalik diskda yoziladi)
BOLT_MEMORY_SPOOL_THRESHOLD = 50 * 1024 * 1024  
# Front-end manzillarini .env fayldan o'qiydi (standart: http://localhost:3000)
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000',
    cast=Csv()
)
# API so'rovlari uchun ruxsat berilgan HTTP metodlari
CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "OPTIONS",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",        # ← ENG MUHIMI
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
# Cookie va autentifikatsiya tokenlarini (Session) yuborishga ruxsat berish
CORS_ALLOW_CREDENTIALS = True

BOLT_DEV_FORCE_POLLING = True

AUTHENTICATION_BACKENDS = [
    'baseuser.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True
LANGUAGES = [("uz", "O'zbekcha")]
LOCALE_PATHS = [BASE_DIR / 'locale']

from .unfold import unfold
UNFOLD = unfold()
UNFOLD["DASHBOARD_CALLBACK"] = "app.dashboard.dashboard_callback"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# MinIO / S3 Asosiy sozlamalar
AWS_ACCESS_KEY_ID       = config('MINIO_ROOT_USER')
AWS_SECRET_ACCESS_KEY   = config('MINIO_ROOT_PASSWORD')
AWS_STORAGE_BUCKET_NAME = config('MINIO_BUCKET_NAME', default='cfm')
AWS_S3_ENDPOINT_URL     = config('MINIO_ENDPOINT', default='http://localhost:9000') # Docker ichki ulanishi uchun
AWS_S3_REGION_NAME      = 'us-east-1'
AWS_QUERYSTRING_AUTH    = False
AWS_S3_FILE_OVERWRITE   = False
AWS_DEFAULT_ACL         = 'public-read'

# .env fayldan brauzer uchun tashqi URL manzilini olamiz (http://localhost:9000)
MINIO_ENDPOINT_PUBLIC = config('MINIO_ENDPOINT_PUBLIC', default='http://localhost:9000')
# custom_domain uchun 'http://' qismini kesib tashlaymiz (localhost:9000 bo'lishi kerak)
MINIO_DOMAIN            = MINIO_ENDPOINT_PUBLIC.replace('http://', '').replace('https://', '')
_url_protocol = "https:" if MINIO_ENDPOINT_PUBLIC.startswith("https") else "http:"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "location": "media",
            "file_overwrite": False,
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "custom_domain":f"{MINIO_DOMAIN}/{AWS_STORAGE_BUCKET_NAME}", # Brauzer uchun to'g'ri domen
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "default_acl": "public-read",
            "querystring_auth": False,
            "use_ssl": False,
            "url_protocol": _url_protocol,
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "location": "static",
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "custom_domain":f"{MINIO_DOMAIN}/{AWS_STORAGE_BUCKET_NAME}", # Brauzer uchun to'g'ri domen
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "default_acl": "public-read",
            "querystring_auth": False,
            "use_ssl": False,
            "url_protocol": _url_protocol,
        },
    },
}

# Brauzer so'rov yuboradigan yakuniy URL manzillar
STATIC_URL = f"{MINIO_ENDPOINT_PUBLIC}/{AWS_STORAGE_BUCKET_NAME}/static/"
MEDIA_URL  = f"{MINIO_ENDPOINT_PUBLIC}/{AWS_STORAGE_BUCKET_NAME}/media/"

STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT  = BASE_DIR / "mediafiles"