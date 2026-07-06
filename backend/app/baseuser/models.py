# apps/baseuser/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone


class BaseUser(models.Model):
    """
    Foydalanuvchi modeli
    Auth serverdan keladigan ma'lumotlarni saqlaydi
    """

    # Asosiy identifikatorlar
    telegram_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        verbose_name="Telegram ID"
    )

    # Foydalanuvchi ma'lumotlari
    username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Username"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Telefon"
    )
    full_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="To'liq ism"
    )

    # Vaqt maydonlari
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Oxirgi kirish"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    class Meta:
        db_table = 'users'
        verbose_name = '👤 Foydalanuvchi'
        verbose_name_plural = '👥 Foydalanuvchilar'
        ordering = ['-created_at']

    def __str__(self):
        return self.username or f"User#{self.telegram_id}"

    def update_last_login(self):
        """Oxirgi kirishni yangilash"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])


class Profile(models.Model):
    django_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        null=True,
        blank=True,
        verbose_name="Django default user (Admin/Teacher)"
    )
    student_user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name='profile',
        null=True,
        blank=True,
        verbose_name="Talaba (BaseUser)"
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        verbose_name="Avatar"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Bio"
    )
    website = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Veb-sayt"
    )

    class Meta:
        db_table = 'user_profiles'
        verbose_name = '👤 Profil'
        verbose_name_plural = '👤 Profillar'

    def __str__(self):
        return f"Profil#{self.id} - {self.django_user or self.student_user}"