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

PROGRESS YANGILASH QOIDASI:
  - ProblemStatus, LessonStatus, LectureStatus, ModuleStatus, CourseStatus
    hech qachon signal orqali emas, services/ qatlamidagi servislar orqali yangilanadi:
        ProblemProgressService -> LessonProgressService
            -> ModuleProgressService -> CourseProgressService -> EnrollmentService
"""
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from baseuser.models import BaseUser


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    class Meta:
        abstract = True


# ======================================================================
# XP / DARAJA / KUNLIK FAOLLIK
# ======================================================================

class UserStats(TimeStampedModel):
    """
    Foydalanuvchining umumiy statistikasi.

    XP faqat add_xp() orqali qo'shiladi.
    Daraja (Level) XP asosida avtomatik yangilanadi.
    """

    class Level(models.TextChoices):
        BEGINNER = "beginner", _("Yangi boshlovchi")
        BRONZE = "bronze", _("Bronza")
        SILVER = "silver", _("Kumush")
        GOLD = "gold", _("Oltin")
        PLATINUM = "platinum", _("Platina")
        EMERALD = "emerald", _("Zumrad")
        DIAMOND = "diamond", _("Olmos")
        MASTER = "master", _("Master")
        GRANDMASTER = "grandmaster", _("Grandmaster")
        IMMORTAL = "immortal", _("Immortal")

    # XP chegaralari (katta qiymatdan kichikka)
    LEVEL_THRESHOLDS = (
        (100_000, Level.IMMORTAL),
        (75_000, Level.GRANDMASTER),
        (55_000, Level.MASTER),
        (40_000, Level.DIAMOND),
        (28_000, Level.EMERALD),
        (18_000, Level.PLATINUM),
        (10_000, Level.GOLD),
        (5_000, Level.SILVER),
        (1_500, Level.BRONZE),
    )

    user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="stats",
        verbose_name=_("Foydalanuvchi"),
    )
    xp = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name=_("Jami XP"),
    )
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.BEGINNER,
        db_index=True,
        verbose_name=_("Daraja"),
    )

    class Meta:
        ordering = ["-xp"]
        verbose_name = _("📊 Foydalanuvchi statistikasi")
        verbose_name_plural = _("📊 Foydalanuvchilar statistikasi")

    def __str__(self):
        return f"{self.user.username} • {self.xp} XP • {self.get_level_display()}"

    # ---------------- LEVEL ----------------

    def compute_level(self):
        """XP bo'yicha levelni hisoblaydi."""
        for threshold, level in self.LEVEL_THRESHOLDS:
            if self.xp >= threshold:
                return level
        return self.Level.BEGINNER

    # ---------------- PROGRESS ----------------

    @property
    def current_level_min_xp(self):
        """Joriy level boshlanadigan XP."""
        reverse = list(reversed(self.LEVEL_THRESHOLDS))
        for xp, level in reverse:
            if level == self.level:
                return xp
        return 0

    @property
    def next_level_xp(self):
        """Keyingi level uchun kerak bo'ladigan XP."""
        reverse = [(0, self.Level.BEGINNER)] + list(reversed(self.LEVEL_THRESHOLDS))
        for index, (_, level) in enumerate(reverse):
            if level != self.level:
                continue
            if index == len(reverse) - 1:
                return None
            return reverse[index + 1][0]
        return None

    @property
    def xp_to_next_level(self):
        """Keyingi levelgacha qolgan XP."""
        if self.next_level_xp is None:
            return 0
        return max(0, self.next_level_xp - self.xp)

    @property
    def progress_percent(self):
        """Level ichidagi progress (%)."""
        next_xp = self.next_level_xp
        if next_xp is None:
            return 100
        current = self.current_level_min_xp
        span = next_xp - current
        if span <= 0:
            return 100
        progress = ((self.xp - current) / span) * 100
        return max(0, min(100, round(progress)))

    # ---------------- XP ----------------

    @classmethod
    def add_xp(cls, user, xp_amount: int, duration_mins: int = 0):
        """Platformadagi YAGONA XP qo'shish metodi."""
        if xp_amount <= 0:
            stats, _ = cls.objects.get_or_create(user=user)
            return stats

        with transaction.atomic():
            stats, _ = cls.objects.select_for_update().get_or_create(user=user)

            stats.xp += xp_amount
            stats.level = stats.compute_level()
            stats.save(update_fields=["xp", "level", "updated_at"])

            today = timezone.now().date()
            activity, created = UserActivityDaily.objects.select_for_update().get_or_create(
                user=user,
                date=today,
                defaults={
                    "xp_earned": xp_amount,
                    "tasks_count": 1,
                    "total_duration": duration_mins,
                },
            )

            if not created:
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


# ======================================================================
# KONTENT PROGRESS ZANJIRI: Lecture -> Lesson -> Modul -> Course
# ======================================================================

class LectureStatus(models.Model):
    """Foydalanuvchi - Ma'ruza/Video blok progress holati."""

    lecture = models.ForeignKey(
        "courses.Lecture",
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
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Boshlangan vaqti"),
        help_text=_("Foydalanuvchi ma'ruzani birinchi marta ochgan vaqt.")
    )
    last_position = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Oxirgi video pozitsiyasi (soniya)"),
        help_text=_("Video qayerda to'xtaganini eslab qolish uchun (resume uchun).")
    )
    watch_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Ko'rilgan umumiy vaqt (soniya)"),
        help_text=_("Analytics uchun: foydalanuvchi videoni jami necha soniya ko'rgan.")
    )
    is_completed = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Tugatilgan (✓)"),
        help_text=_("Agar talaba ma'ruzani o'qib bo'lib yoki videoni ko'rib 'Tugatdim' tugmasini bossa True bo'ladi.")
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Tugatilgan vaqti")
    )

    class Meta:
        verbose_name = _("📝 Ma'ruza progress holati")
        verbose_name_plural = _("📝 Ma'ruza progress holatlari")
        unique_together = ("user", "lecture")
        indexes = [
            models.Index(fields=["user", "lecture", "is_completed"]),
            models.Index(fields=["is_completed", "-completed_at"]),
        ]

    def __str__(self):
        username = self.user.username if self.user.username else f"User-{self.user.id}"
        status_text = "Tugatilgan ✓" if self.is_completed else "Tugatilmagan ✗"
        return f"{username} -> {self.lecture.title[:25]} ({status_text})"


class ProblemStatus(models.Model):
    """Foydalanuvchi - Masala progress holati (tezkor lookup uchun, Submission tarixidan mustaqil)."""

    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="problem_statuses",
        verbose_name="Foydalanuvchi"
    )
    problem = models.ForeignKey(
        "problems.Problem",
        on_delete=models.CASCADE,
        related_name="statuses",
        verbose_name="Masala"
    )
    solved = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Yechilgan",
        help_text="Ushbu masala kamida bir marta Accepted bo'lganmi?"
    )
    best_submission = models.ForeignKey(
        "submissions.Submission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="best_for_status",
        verbose_name="Eng yaxshi yechim",
        help_text="Eng tez/eng samarali Accepted submission."
    )
    attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Urinishlar soni",
        help_text="Ushbu masala uchun yuborilgan barcha submissionlar soni."
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Birinchi urinish vaqti"
    )
    solved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Yechilgan vaqti"
    )

    class Meta:
        unique_together = ("user", "problem")
        verbose_name = "🧩 Masala holati"
        verbose_name_plural = "🧩 Masalalar holati"
        indexes = [
            models.Index(fields=["user", "solved"]),
            models.Index(fields=["problem", "solved"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.problem} ({'✅' if self.solved else '⏳'})"


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
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Boshlangan vaqti",
        help_text="Foydalanuvchi darsni birinchi marta ochgan vaqt."
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
        indexes = [
            models.Index(fields=["user", "lesson", "is_completed"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.lesson} ({'✅' if self.is_completed else '⏳'})"


class ModuleStatus(models.Model):
    """Foydalanuvchi - Modul progress holati (real-time COUNT() o'rniga)."""

    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="module_statuses",
        verbose_name="Foydalanuvchi"
    )
    modul = models.ForeignKey(
        "courses.Modul",
        on_delete=models.CASCADE,
        related_name="statuses",
        verbose_name="Modul"
    )
    completed_lessons = models.PositiveSmallIntegerField(default=0, verbose_name="Tugatilgan darslar soni")
    completed_tests = models.PositiveSmallIntegerField(default=0, verbose_name="Tugatilgan testlar soni")
    is_completed = models.BooleanField(default=False, db_index=True, verbose_name="Tugallangan")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Boshlangan vaqti")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugatilgan vaqti")

    class Meta:
        unique_together = ("user", "modul")
        verbose_name = "📚 Modul holati"
        verbose_name_plural = "📚 Modullar holati"
        indexes = [
            models.Index(fields=["user", "modul", "is_completed"]),
        ]

    def __str__(self):
        status = "✅" if self.is_completed else "⏳"
        return f"{self.user} — {self.modul} ({status})"

class CourseStatus(models.Model):
    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="course_statuses",
        verbose_name="Foydalanuvchi"
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="statuses",
        verbose_name="Kurs"
    )
    completed_modules = models.PositiveSmallIntegerField(default=0, verbose_name="Tugatilgan modullar soni")
    completed_lessons = models.PositiveSmallIntegerField(default=0, verbose_name="Tugatilgan darslar soni")
    completed_tests = models.PositiveSmallIntegerField(default=0, verbose_name="Tugatilgan testlar soni")
    completed_problems = models.PositiveSmallIntegerField(default=0, verbose_name="Yechilgan masalalar soni")
    is_completed = models.BooleanField(default=False, db_index=True, verbose_name="Tugallangan")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Boshlangan vaqti")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugatilgan vaqti")

    class Meta:
        unique_together = ("user", "course")
        verbose_name = "🏆 Kurs holati"
        verbose_name_plural = "🏆 Kurslar holati"
        indexes = [
            models.Index(fields=["user", "course", "is_completed"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.course}"