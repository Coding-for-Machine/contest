from django.db import models
from django.utils.translation import gettext_lazy as _
from baseuser.models import BaseUser


class Notification(models.Model):
    class TypeChoices(models.TextChoices):
        LESSON_COMPLETED = "lesson_completed", _("Dars yakunlandi")
        MODULE_COMPLETED = "module_completed", _("Bob yakunlandi")
        COURSE_COMPLETED = "course_completed", _("Kurs yakunlandi")
        CERTIFICATE_READY = "certificate_ready", _("Sertifikat tayyor")
        NEW_LESSON = "new_lesson", _("Yangi dars")
        ACHIEVEMENT = "achievement", _("Yutuq")
        SUBMISSION_RESULT = "submission", _("Taqdimot natijasi")
        CONTEST_START = "contest_start", _("Musobaqa boshlanishi")
        CONTEST_END = "contest_end", _("Musobaqa tugashi")
        SYSTEM = "system", _("Tizim xabari")

    user = models.ForeignKey(
       BaseUser,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Foydalanuvchi")
    )
    
    type = models.CharField(
        max_length=20,
        choices=TypeChoices.choices,
        default=TypeChoices.SYSTEM,
        verbose_name=_("Turi")
    )
    
    title = models.CharField(max_length=255, verbose_name=_("Sarlavha"))
    message = models.TextField(verbose_name=_("Xabar"))
    
    # Qayerga o'tish kerak (frontend URL path)
    link = models.CharField(
        max_length=500, 
        blank=True, 
        default="",
        verbose_name=_("Havola")
    )
    
    # Qo'shimcha data (JSON)
    meta = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name=_("Meta ma'lumotlar")
    )
    
    is_read = models.BooleanField(
        default=False, 
        db_index=True,
        verbose_name=_("O'qilganmi")
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True, 
        db_index=True,
        verbose_name=_("Yaratilgan vaqt")
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]
        verbose_name = _("Bildirishnoma")
        verbose_name_plural = _("Bildirishnomalar")

    def __str__(self):
        return f"#{self.id} | {self.user} | {self.title}"