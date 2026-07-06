from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
# python-decouple kutubxonasidan config-ni import qilamiz
from decouple import config

class Command(BaseCommand):
    help = "Agar mavjud bo'lmasa, avtomatik superuser yaratadi"

    def handle(self, *args, **options):
        User = get_user_model()
        
        # python-decouple orqali .env dan ma'lumotlarni o'qiymiz
        username = config("DJANGO_SUPERUSER_USERNAME", default="admin_cfm_contest_asadbek")
        email = config("DJANGO_SUPERUSER_EMAIL", default="admin_cfm_contest_asadbek@gmail.com")
        password = config("DJANGO_SUPERUSER_PASSWORD", default="admin_cfm_contest_asadbek_password")

        # Bazada bunday foydalanuvchi bor yoki yo'qligini tekshiramiz
        if not User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' yaratilmoqda..."))
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' muvaffaqiyatli yaratildi!"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' allaqachon mavjud, qayta yaratilmadi."))
