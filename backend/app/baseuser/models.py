# apps/users/models.py
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
    
    # Session
    session_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Session ID"
    )
    secret_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Secret Key"
    )
    iat = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Token issued at",
        help_text="JWT tokenning issued at timestampi"
    )
    
    # Vaqt
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