from django.apps import AppConfig


class QuizsConfig(AppConfig):
    name = 'quizs'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import quizs.signals
