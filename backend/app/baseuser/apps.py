from django.apps import AppConfig

def avto_superadmin_yarat(sender, **kwargs):
    from django.core.management import call_command
    try:
        call_command('createsuperuser_if_none')
    except Exception:
        pass

class BaseuserConfig(AppConfig):
    name = 'baseuser'
    def ready(self):
        from django.db.models.signals import post_migrate
        from . import signals
        post_migrate.connect(signals.create_groups, sender=self)
        from .admin_overrides import register_uz_actions
        register_uz_actions()
        post_migrate.connect(avto_superadmin_yarat, sender=self)