# status/models.py
"""
Status app — foydalanuvchi statistikasi va faollik tarixi.

XP BERISH QOIDASI (muhim!):
  - Bu modelda to'g'ridan-to'g'ri XP BERILMAYDI.
  - XP faqat quyidagi joylarda beriladi:
      1. problems app: Submission signal (birinchi ACCEPTED uchun)
      2. quizs app: TestSession.calculate_mathematical_score() ichida (atomik)
      3. contests app: ContestRegistration signal (birinchi COMPLETED uchun)
  - add_xp() metodi faqat boshqa applardan chaqiriladi, hech qachon o'zi chaqirmaydi.
"""
from django.db import models, transaction
from django.utils import timezone
from baseuser.models import BaseUser
from django.utils.translation import gettext_lazy as _

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    class Meta:
        abstract = True


class UserStats(TimeStampedModel):
    """Foydalanuvchining joriy XP va darajasi."""

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Yangi boshlovchi"
        BRONZE = "bronze", "Bronza"
        SILVER = "silver", "Kumush"
        GOLD = "gold", "Oltin"
        PRO = "pro", "Professional"

    LEVEL_THRESHOLDS = (
        (15_000, Level.PRO),
        (8_000, Level.GOLD),
        (5_000, Level.SILVER),
        (2_000, Level.BRONZE),
    )

    user = models.OneToOneField(
        BaseUser, 
        on_delete=models.CASCADE, 
        related_name="stats",
        verbose_name="Foydalanuvchi",
        help_text="Ushbu statistika egasi bo'lgan foydalanuvchi."
    )
    xp = models.PositiveIntegerField(
        "Jami to'plangan XP", 
        default=0, 
        db_index=True,
        help_text="Foydalanuvchi tomonidan platformada to'plangan jami umumiy ball (XP)."
    )
    level = models.CharField(
        "Joriy darajasi",
        max_length=20,
        choices=Level.choices,
        default=Level.BEGINNER,
        db_index=True,
        help_text="Foydalanuvchining jami XP ballariga qarab avtomatik hisoblanadigan unvoni."
    )

    class Meta:
        verbose_name = "📊 Foydalanuvchi Statistikasi"
        verbose_name_plural = "📊 Foydalanuvchilar Statistikasi"
        ordering = ["-xp"]

    def __str__(self):
        return f"{self.user.username} — {self.xp} XP ({self.get_level_display()})"

    def compute_level(self) -> str:
        """XP asosida darajani hisoblaydi."""
        for threshold, level in self.LEVEL_THRESHOLDS:
            if self.xp >= threshold:
                return level
        return self.Level.BEGINNER

    @classmethod
    def add_xp(cls, user: BaseUser, xp_amount: int, duration_mins: int = 0) -> "UserStats":
        """Foydalanuvchiga XP qo'shish — YAGONA umumiy metod."""
        if xp_amount <= 0:
            stats, _ = cls.objects.get_or_create(user=user)
            return stats

        with transaction.atomic():
            stats, _ = cls.objects.select_for_update().get_or_create(user=user)
            stats.xp += xp_amount
            stats.level = stats.compute_level()
            stats.save(update_fields=["xp", "level", "updated_at"])

            # Heatmap uchun kunlik faollikni yozish
            today = timezone.now().date()
            activity, _ = UserActivityDaily.objects.get_or_create(
                user=user, date=today
            )
            
            activity.xp_earned = models.F("xp_earned") + xp_amount
            activity.tasks_count = models.F("tasks_count") + 1
            activity.total_duration = models.F("total_duration") + duration_mins
            activity.save(update_fields=["xp_earned", "tasks_count", "total_duration"])

        stats.refresh_from_db()
        return stats


class UserActivityDaily(models.Model):
    """GitHub Heatmap kalendarini chizish uchun kunlik arxiv."""

    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="activity_days",
        verbose_name="Foydalanuvchi",
        help_text="Kunlik faollik qayd etilgan talaba."
    )
    date = models.DateField(db_index=True, verbose_name="Sana", help_text="Tizimdagi faollik sodir bo'lgan kun.")
    xp_earned = models.PositiveIntegerField(
        default=0, 
        verbose_name="Kunlik XP",
        help_text="Aynan shu sana doirasida foydalanuvchi ishlagan jami ball."
    )
    tasks_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Vazifalar soni",
        help_text="Shu kunda to'g'ri yechilgan masalalar va test savollari soni."
    )
    total_duration = models.PositiveIntegerField(
        default=0, 
        verbose_name="Sarflangan umumiy vaqt (daqiqa)",
        help_text="Shu kuni dars va testlarda o'tkazilgan jami vaqt miqdori."
    )

    class Meta:
        unique_together = ("user", "date")
        verbose_name = "📅 Kunlik Faollik (Heatmap)"
        verbose_name_plural = "📅 Kunlik Faolliklar (Heatmap)"
        indexes = [
            models.Index(fields=["user", "date"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.date} (+{self.xp_earned} XP)"


class LessonStatus(models.Model):
    """Talabaning muayyan darsni o'zlashtirish holati."""
    
    user = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE, 
        related_name="lesson_statuses",
        verbose_name="Foydalanuvchi"
    )
    lesson = models.ForeignKey(
        "courses.Lesson", 
        on_delete=models.CASCADE, 
        related_name="statuses",
        verbose_name="Darslik",
        help_text="Holati kuzatilayotgan dars."
    )
    finished_tasks_count = models.PositiveSmallIntegerField(
        default=0, 
        verbose_name="Tugatilgan vazifalar soni",
        help_text="Ushbu dars ichida muvaffaqiyatli yakunlangan amaliy masalalar soni."
    )
    is_completed = models.BooleanField(
        default=False, 
        db_index=True, 
        verbose_name="Tugallangan",
        help_text="Dars to'liq o'zlashtirildi deb hisoblanishi uchun belgi."
    )
    completed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Tugatilgan vaqti",
        help_text="Dars to'liq yakunlangan aniq sana va vaqt."
    )

    class Meta:
        unique_together = ("user", "lesson")
        verbose_name = "📗 Dars holati"
        verbose_name_plural = "📗 Darslar holati"

    def __str__(self):
        return f"{self.user} — {self.lesson} ({'✅' if self.is_completed else '⏳'})"


class LectureStatus(models.Model):
    lecture = models.ForeignKey(
        'courses.Lecture',  # Biz hozirgina yaratgan yangi ko'p ma'ruzali model
        on_delete=models.CASCADE,
        related_name="user_statuses",
        verbose_name=_("Ma'ruza / Video blok"),
        help_text=_("Foydalanuvchi o'qib yoki ko'rib tugatgan ma'ruza bloki.")
    )
    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="lecture_statuses",
        verbose_name=_("Foydalanuvchi"),
        help_text=_("Tizimda faol bo'lgan talaba.")
    )

    is_completed = models.BooleanField(
        default=True,
        db_index=True,  # API-da foizli progressni mikrosekundlarda hisoblash uchun
        verbose_name=_("Tugatilgan (✓)"),
        help_text=_("Agar talaba ma'ruzani o'qib bo'lib yoki videoni ko'rib 'Tugatdim' tugmasini bossa True bo'ladi.")
    )
    completed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Tugatilgan vaqti")
    )

    class Meta:
        verbose_name = _("📝 Ma'ruza progress holati")
        verbose_name_plural = _("📝 Ma'ruza progress holatlari")
        
        unique_together = ('user', 'lecture')
        
        # ⚡ HIGH-PERFORMANCE INDEKSLAR
        indexes = [
            models.Index(fields=['user', 'lecture', 'is_completed']),
            models.Index(fields=['is_completed', '-completed_at']),
        ]

    def __str__(self):
        username = self.user.username if self.user.username else f"User-{self.user.id}"
        status_text = "Tugatilgan ✓" if self.is_completed else "Tugatilmagan ✗"
        return f"{username} -> {self.lecture.title[:25]} ({status_text})"
