from pathlib import Path
from decouple import config, Csv


BASE_DIR = Path(__file__).resolve().parent.parent
# SECRET_KEY = 'a-string-secret-at-least-256-bits-long'
SECRET_KEY = config('SECRET_KEY')
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())


# Application definition

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters", # Ixtiyoriy
    "unfold.contrib.forms",   # WYSIWYG uchun bu juda muhim!
    "unfold.contrib.import_export", # Ixtiyoriy

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',  # django-storages
    'django_celery_results', 

    # installed
    'ninja',  # Django Ninja
    'corsheaders',
    # 'django_bolt',
    # apps
    'contests',
    'problems',
    'submissions',
    'baseuser',
    'quizs',
    'courses',
    'video',
    'status',
]

# celery -A your_project_name worker --loglevel=info
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# -----------------------------start-----------------------------------------
CORS_ALLOW_ALL_ORIGINS = True  # Development uchun
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# CSRF uchun ishonchli domenlar (bu so'rov yuboruvchi domenlar uchun)
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:9000"
]
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
# ------------------------------end----------------------------------------

# JWT Auth Server manzili
AUTH_SERVER_BASE_URL = config("AUTH_SERVICE")

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
        'DIRS': [BASE_DIR, "templates"],
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


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': 'localhost',  # Agar Docker ishlatayotgan bo'lsangiz 'db' deb yozing
        'PORT': '5432',
    }
}
# -------------------REDIS-------------------
IS_DOCKER=False
REDIS_HOST = "redis" if IS_DOCKER else "127.0.0.1"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
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

# settings.py
from django.urls import reverse_lazy

UNFOLD = {
    "SITE_TITLE": "Kurslar",
    "SITE_HEADER": "Admin Panel",
    "SITE_SYMBOL": "speed", # Google Material Symbols ikonkasi
    
    # Login sahifasi sozlamalari
    "LOGIN": {
        "image": lambda request: "https://your-domain.com", # Orqa fon rasmi
        "redirect_after_login": reverse_lazy("admin:index"),
    },
    
    # Brending (Logo)
    "SIDEBAR": {
        "show_search": True, # Qidiruv maydoni
        "show_all_applications": True,
    },
    
    # Ranglar sxemasi (ixtiyoriy)
    "COLORS": {
        "primary": {
            "50": "250 250 250",
            "100": "244 244 245",
            # ... ranglarni Tailwind kabi sozlash mumkin
        },
    },
    "STYLES": [
        lambda request: """
            <style>
                /* Agar ba'zi matnlar tarjima bo'lmasa, CSS orqali ham o'zgartirsa bo'ladi */
                h1:contains("Welcome back to") { font-size: 0; }
                h1:contains("Welcome back to"):before { content: "Xush kelibsiz!"; font-size: 1.5rem; }
            </style>
        """,
    ],
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─────────────────────────────────────────────
# ✅ MinIO / S3 Sozlamalari (.env dan)
# ─────────────────────────────────────────────
AWS_ACCESS_KEY_ID       = config('MINIO_ROOT_USER')
AWS_SECRET_ACCESS_KEY   = config('MINIO_ROOT_PASSWORD')
AWS_STORAGE_BUCKET_NAME = config('MINIO_BUCKET_NAME', default='cfm')
AWS_S3_ENDPOINT_URL     = config('MINIO_ENDPOINT', default='http://localhost:9000')
AWS_S3_REGION_NAME      = 'us-east-1'
AWS_QUERYSTRING_AUTH    = False   # Public fayllar uchun False
AWS_S3_FILE_OVERWRITE   = False   # Bir xil nomli fayllarni ustiga yozmasin
AWS_DEFAULT_ACL         = 'public-read'

STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# Alohida bucket yoki prefix ishlatish (media vs static)
STORAGES = {
    "default": {  # Media fayllar (upload qilingan)
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "location": "media",  # /mybucket/media/ papkasiga
            "file_overwrite": False,
        },
    },
    "staticfiles": {  # Static fayllar (CSS, JS)
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "location": "static",  # /mybucket/static/ papkasiga
        },
    },
}

# URL lar
STATIC_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/static/"
MEDIA_URL  = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/"

# Local fallback (collectstatic, development)
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT  = BASE_DIR / "mediafiles"
