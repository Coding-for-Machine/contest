from django.db import models
from django.utils.translation import gettext_lazy as _

# Bog'langan modellarni to'g'ri import qilamiz
from baseuser.models import BaseUser
from problems.models import Problem, Language
from contests.models import Contest


class Submission(models.Model):
    # ─── FOYDALANUVCHI VA MASALA BOG'LANISHLARI ───
    user = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name=_("Foydalanuvchi")
    )
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name=_("Masala")
    )
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name='submissions',
        null=True,
        blank=True,
        verbose_name=_("Musobaqa (Contest)")
    )

    # ─── KOD VA KO'RSATKICHLAR ───
    code = models.TextField(
        verbose_name=_("Yuborilgan kod")
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,  # Til o'chib ketsa ham urinishlar tarixi saqlanib qoladi
        related_name='submissions',
        verbose_name=_("Dasturlash tili")
    )

    # ─── YAKUNIY STATUS (Accepted / Wrong Answer) ───
    status = models.BooleanField(
        default=False,
        db_index=True,  # Filtrlar va statistika tez ishlashi uchun indekslangan
        verbose_name=_("Muvaffaqiyatli yechilgan (✓)")
    )

    # ─── RAMda BAJARILGAN TEST CASE NATIJALARI (JSON FORMATDA) ───
    # Masalan: [{"test_case": 1, "status": "passed", "time": 45}, ...]
    test_results = models.JSONField(
        default=list, 
        blank=True,
        help_text=_('Har bir test case holati: [{"test_case": 1, "status": "passed", "time": 100}]'),
        verbose_name=_("Test natijalari")
    )
    
    # ─── VAQT KO'RSATKICHI ───
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,  # Oxirgi urinishlarni tezkor saralash uchun indekslangan
        verbose_name=_("Yuborilgan vaqt")
    )
    
    class Meta:
        verbose_name = _("Kod urinishi")
        verbose_name_plural = _("Kod urinishlari")
        ordering = ['-submitted_at']  # Har doim eng oxirgi urinishlar birinchi ko'rinadi
        
        # ⚡ BAZANI MAKSIMAL TEZLASHTIRISH UCHUN MULTI-COLUMN INDEKSLAR (DATABASE OPTIMIZATION)
        indexes = [
            # 1. Bosh sahifadagi "Mening holatim" (✓, ✗, —) ko'rsatkichini millisekundlarda hisoblash uchun
            models.Index(fields=['user', 'problem', 'status']),
            
            # 2. Musobaqa (Contest) sahifasidagi liderlar jadvali (Leaderboard) tez shakllanishi uchun
            models.Index(fields=['user', 'contest']),
            
            # 3. Umumiy statistika va oxirgi muvaffaqiyatli yechilgan masalalar lentalari uchun
            models.Index(fields=['status', 'submitted_at']),
            
            # 4. Musobaqa ichidagi qabul qilingan toza yechimlarni filterlash uchun
            models.Index(fields=['contest', 'status']),
        ]

    def __str__(self):
        # Admin panelda chiroyli va tushunarli ko'rinishi uchun
        status_text = "Accepted ✓" if self.status else "Failed ✗"
        return f"{self.user.telegram_id} - {self.problem.title} - {status_text}"
