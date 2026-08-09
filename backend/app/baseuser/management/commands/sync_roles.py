# baseuser/management/commands/sync_roles.py
from django.core.management.base import BaseCommand
from baseuser.permissions.signals import create_roles

class Command(BaseCommand):
    help = 'Barcha guruh va permissionlarni qayta sozlash'

    def handle(self, *args, **kwargs):
        create_roles(None)
        self.stdout.write(self.style.SUCCESS('✅ Rollar sinxronlandi'))