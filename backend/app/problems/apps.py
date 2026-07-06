from django.apps import AppConfig


class ProblemsConfig(AppConfig):
    name = 'problems'
    def ready(self):
        from . import signals