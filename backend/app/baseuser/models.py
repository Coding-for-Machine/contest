# apps/baseuser/models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class BaseUser(models.Model):
    """
    Talaba (Telegram bot) foydalanuvchisi.
    Auth serverdan yoki Telegram botdan keladigan ma'lumotlarni saqlaydi.
    Bu model Django'ning ichki `User` modelidan MUSTAQIL — xodimlar/adminlar
    uchun `django.contrib.auth` User ishlatiladi, talabalar uchun shu model.
    """

    # --- Asosiy identifikatorlar ---
    telegram_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        verbose_name="Telegram ID",
    )

    # --- Foydalanuvchi ma'lumotlari ---
    username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Username",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Telefon",
    )
    full_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="To'liq ism",
    )
    center = models.ForeignKey(
        "centers.Center",
        on_delete=models.CASCADE,
        related_name="students",
        null=True, blank=True,  # Avvalgi (markazsiz) userlar uchun
        verbose_name="O'quv markazi",
        db_index=True,
    )

    # --- Vaqt maydonlari ---
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Oxirgi kirish",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan",
    )

    # --- Status ---
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol",
    )

    class Meta:
        db_table = "users"
        verbose_name = "👤 Foydalanuvchi"
        verbose_name_plural = "👥 Foydalanuvchilar"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["center", "is_active"]),
        ]

    def __str__(self):
        return self.username or self.full_name or f"User#{self.telegram_id}"

    def update_last_login(self):
        """Oxirgi kirishni yangilash (query-optimal: faqat kerakli maydon)."""
        self.last_login = timezone.now()
        self.save(update_fields=["last_login"])


class Profile(models.Model):
    """
    Xodim (Django `User`) yoki talaba (`BaseUser`) uchun umumiy profil.

    MUHIM: `django_user` va `student_user` — ikkalasi ham ixtiyoriy, lekin
    admin panelida (`baseuser.utils.admin.MultiCenterOwnerMixin`) ishlatiladigan
    markaz-aniqlash mantig'i (`request.user.profile.center`) FAQAT
    `django_user` orqali kirilgan profilga tayanadi. Shuning uchun bu yerda
    ikkalasi bir vaqtda to'ldirilishiga (odatiy holatda) yo'l qo'yilmaydi —
    aks holda qaysi tomon "haqiqiy" ekanligi noaniq bo'lib qoladi.
    """

    django_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        null=True,
        blank=True,
        verbose_name="Django foydalanuvchi (Admin/Xodim)",
    )
    student_user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="profile",
        null=True,
        blank=True,
        verbose_name="Talaba (BaseUser)",
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        verbose_name="Avatar",
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Bio",
    )
    website = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Veb-sayt",
    )
    center = models.ForeignKey(
        "centers.Center",
        on_delete=models.CASCADE,
        related_name="staff_profiles",
        null=True, blank=True,
        verbose_name="Ish joyi (Markaz)",
        help_text=(
            "Xodim biriktirilgan o'quv markazi. Bo'sh qoldirilsa (masalan "
            "superuser/Direktor uchun), admin panelida markaz maydonlarini "
            "har safar qo'lda tanlash talab qilinadi."
        ),
    )

    class Meta:
        db_table = "user_profiles"
        verbose_name = "👤 Profil"
        verbose_name_plural = "👤 Profillar"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(django_user__isnull=False, student_user__isnull=True)
                    | models.Q(django_user__isnull=True, student_user__isnull=False)
                    | models.Q(django_user__isnull=True, student_user__isnull=True)
                ),
                name="profile_django_user_xor_student_user",
                violation_error_message=(
                    "Profil FAQAT django_user GA yoki FAQAT student_user GA "
                    "tegishli bo'lishi mumkin, ikkalasiga birdan emas."
                ),
            ),
        ]

    def __str__(self):
        owner = self.django_user or self.student_user
        return f"Profil#{self.id} - {owner}" if owner else f"Profil#{self.id}"

    def clean(self):
        super().clean()
        if self.django_user_id and self.student_user_id:
            raise ValidationError(
                "Profil bir vaqtning o'zida ham xodimga (django_user), ham "
                "talabaga (student_user) bog'lanishi mumkin emas."
            )

    @property
    def owner(self):
        """Profilga tegishli haqiqiy foydalanuvchi obyekti (qaysi turi bo'lishidan qat'i nazar)."""
        return self.django_user or self.student_user

    @property
    def is_staff_profile(self) -> bool:
        return self.django_user_id is not None

    @property
    def is_student_profile(self) -> bool:
        return self.student_user_id is not None

    @property
    def has_center(self) -> bool:
        """
        Admin permission mixin (`_get_user_center`) shu yerga tayanadi:
        superuser yoki Direktor kabi "barcha markazlarga" mas'ul xodimlarda
        `center = None` bo'lishi kutiladigan holat, xato emas.
        """
        return self.center_id is not None