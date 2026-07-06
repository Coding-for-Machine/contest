from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from problems.models import Problem, Language
from baseuser.models import BaseUser

class Submission(models.Model):
    class VerdictChoices(models.TextChoices):
        ACCEPTED = "AC", "Accepted"               # Hamma testlardan o'tdi
        WRONG_ANSWER = "WA", "Wrong Answer"       # Testda xatolik bor
        RUNTIME_ERROR = "RE", "Runtime Error"     # Kod ijrosida xato (Crash)
        TIME_LIMIT_EXCEEDED = "TLE", "Time Limit Exceeded" # Vaqt tugadi
        MEMORY_LIMIT_EXCEEDED = "MLE", "Memory Limit Exceeded" # Xotira to'ldi
        COMPILE_ERROR = "CE", "Compile Error"     # Kompilyatsiya xatosi

    # 1. MUNOSABATLAR (Relations)
    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name=_("Foydalanuvchi")
    )
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name=_("Masala")
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name="submissions",
        verbose_name=_("Dasturlash tili")
    )

    # 2. FOYDALANUVCHI YUBORGAN KOD
    code = models.TextField(verbose_name=_("Yechim kodi"))

    # 3. YAKUNIY NATIJA (Verdict)
    status = models.BooleanField(
        default=False, 
        verbose_name=_("Muvaffaqiyatli yechildimi?"),
        help_text=_("Agar hamma testlardan o'tgan bo'lsa True, aks holda False.")
    )
    verdict = models.CharField(
        max_length=4,
        choices=VerdictChoices.choices,
        default=VerdictChoices.WRONG_ANSWER,
        verbose_name=_("Yakuniy hukm (Verdict)")
    )

    # 4. TEST STATISTICS (Metrikalar)
    passed_test_count = models.PositiveIntegerField(default=0, verbose_name=_("O'tgan testlar soni"))
    total_test_count = models.PositiveIntegerField(default=0, verbose_name=_("Jami testlar soni"))
    
    execution_time = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name=_("Ijro vaqti (ms)"),
        help_text=_("Yechimning eng sekin ishlagan testidagi vaqti.")
    )
    execution_memory = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name=_("Ishlatilgan xotira (KB)")
    )

    # 5. BITTA-BITTA TESTLARNING BATAFSIL JSON JAVOBI
    test_results = models.JSONField(
        default=list, 
        blank=True, 
        verbose_name=_("Batafsil test natijalari JSON"),
        help_text=_("Format: [{'idx': 1, 'ok': true, 'stdout': '...', 'stderr': null}, ...]")
    )

    # 6. VAQT METRIKALARI
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Yuborilgan vaqt")
    )

    class Meta:
        verbose_name = _("📥 Yechim (Submission)")
        verbose_name_plural = _("📥 Yechimlar (Submissions)")
        indexes = [
            models.Index(fields=["user", "problem"]),
            models.Index(fields=["problem", "status"]),
            models.Index(fields=["-submitted_at"]), 
        ]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Sub #{self.id} | {self.user.username if self.user.username else self.user.phone} -> {self.problem.title} [{self.verdict}]"
