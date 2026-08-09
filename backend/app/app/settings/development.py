# app/settings/development.py
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Development da SQLite ishlatish (ixtiyoriy, tez test uchun)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Development logging — oddiy, tushunarli format
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "handlers": {
#         "console": {
#             "class": "logging.StreamHandler",
#         },
#     },
#     "root": {
#         "handlers": ["console"],
#         "level": "DEBUG",
#     },
#     "loggers": {
#         "django": {
#             "handlers": ["console"],
#             "level": "DEBUG",
#             "propagate": False,
#         },
#         "django_bolt": {
#             "handlers": ["console"],
#             "level": "DEBUG",
#         },
#     },
# }
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',  # 💡 SQL so'rovlarini terminalda ko'rish uchun
        },
    },
}
