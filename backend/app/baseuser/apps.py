# baseuser/apps.py

from django.apps import AppConfig

def avto_superadmin_yarat(sender, **kwargs):
    from django.core.management import call_command
    try:
        call_command('createsuperuser_if_none')
    except Exception:
        pass

class BaseuserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'baseuser'

    def ready(self):
        import baseuser.permissions.signals

        import baseuser.signals

        from .admin_overrides import register_uz_actions
        register_uz_actions()

        from django.db.models.signals import post_migrate
        post_migrate.connect(avto_superadmin_yarat, sender=self)