import uuid
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from centers.models import CenterScopedMixin
from baseuser.models import BaseUser
from video.models import Video
from mdeditor.fields import MDTextField
from quizs.models import Question, Choice




class Contest(CenterScopedMixin, models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Ochiq"
        PRIVATE = "private", "Yopiq"

    class ContestType(models.TextChoices):
        ICPC = "icpc", "ICPC (vaqt jarimasi)"
        DYNAMIC = "dynamic", "Dinamik ball (Codeforces uslubi)"
        SIMPLE = "simple", "Oddiy (to'g'ri/noto'g'ri)"

    class Format(models.TextChoices):
        CODING = "coding", "Faqat dasturlash masalalari"
        QUIZ = "quiz", "Faqat variantli savollar"
        MIXED = "mixed", "Aralash (kod + variant)"

    title = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Musobaqa nomi",
        help_text=(
            "Foydalanuvchilarga ko'rsatiladigan musobaqa nomi. "
            "Masalan: Python Weekly Contest #1."
        ),
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        verbose_name="URL manzili",
        help_text=(
            "Musobaqaning URL uchun ishlatiladigan yagona nomi. "
            "Bo'sh qoldirilsa title asosida avtomatik yaratiladi."
        ),
    )

    description = MDTextField(
        blank=True,
        verbose_name="Musobaqa tavsifi",
        help_text=(
            "Musobaqa haqida batafsil ma'lumot, qoidalar, "
            "shartlar va ishtirokchilar uchun qo'shimcha izohlar."
        ),
    )
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        db_index=True,
        verbose_name="Ko'rinish turi",
        help_text=(
            "Ochiq contest barcha ruxsat etilgan foydalanuvchilar uchun "
            "ko'rinadi. Yopiq contestga kirish uchun access key talab qilinadi."
        ),
    )
    access_key = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Kirish kaliti",
        help_text=(
            "Faqat yopiq contest uchun ishlatiladi. "
            "Bo'sh qoldirilsa backend xavfsiz random kalit yaratadi. "
            "Ochiq contest uchun bu maydon avtomatik ravishda bo'shatiladi."
        ),
    )
    contest_type = models.CharField(
        max_length=10,
        choices=ContestType.choices,
        default=ContestType.ICPC,
        verbose_name="Baholash turi",
        help_text=(
            "Contest davomida ball va jarima qanday hisoblanishini "
            "belgilaydi. ICPC vaqt jarimasidan, Dynamic vaqt/urinishga "
            "qarab kamayuvchi balldan, Simple esa oddiy to'g'ri/noto'g'ri "
            "baholashdan foydalanadi."
        ),
    )
    format = models.CharField(
        max_length=10,
        choices=Format.choices,
        default=Format.CODING,
        db_index=True,
        verbose_name="Musobaqa formati",
        help_text=(
            "Contest tarkibidagi topshiriqlar turini bildiradi: "
            "coding — dasturlash masalalari, "
            "quiz — variantli savollar, "
            "mixed — ikkalasi birgalikda. "
            "Kerak bo'lsa refresh_format() orqali avtomatik aniqlanadi."
        ),
    )
    start_time = models.DateTimeField(
        verbose_name="Boshlanish vaqti",
        help_text=(
            "Contest ishtirokchilar uchun boshlanadigan sana va vaqt."
        ),
    )
    end_time = models.DateTimeField(
        verbose_name="Tugash vaqti",
        help_text=(
            "Contest yakunlanadigan sana va vaqt. "
            "Boshlanish vaqtidan keyin bo'lishi shart."
        ),
    )
    registration_deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ro'yxatdan o'tish muddati",
        help_text=(
            "Yangi ishtirokchilar contestga qo'shilishi mumkin bo'lgan "
            "oxirgi vaqt. Bo'sh qoldirilsa, registration start_time "
            "gacha ochiq bo'ladi."
        ),
    )
    duration_minutes = models.PositiveIntegerField(
        verbose_name="Contest davomiyligi",
        help_text=(
            "Contestning umumiy davomiyligi daqiqalarda. "
            "Masalan: 120 = 2 soat."
        ),
    )
    allow_practice = models.BooleanField(
        default=True,
        verbose_name="Mashq rejimiga ruxsat",
        help_text=(
            "Contest yakunlangandan keyin uning masalalarini "
            "practice rejimida ishlashga ruxsat beradimi. "
            "Bu contest davomida qatnashish ruxsati emas."
        ),
    )
    penalty_minutes_per_wrong = models.PositiveIntegerField(
        default=20,
        verbose_name="Xato urinish uchun jarima",
        help_text=(
            "ICPC turidagi contestlarda har bir noto'g'ri urinish "
            "uchun qo'shiladigan jarima daqiqalari. "
            "Masalan: 20 = har bir xato uchun 20 daqiqa."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol",
        help_text=(
            "Contest tizimda faol ekanini bildiradi. "
            "Faol bo'lmagan contestlar odatiy public API ro'yxatlarida "
            "ko'rsatilmasligi mumkin."
        ),
    )
    intro_video = models.ForeignKey(
        Video,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contests",
        verbose_name="Tanishtiruv videosi",
        help_text=(
            "Contest boshlanishidan oldin ko'rsatiladigan "
            "qoida, yo'riqnoma yoki tushuntiruvchi video. "
            "Ixtiyoriy."
        ),
    )
    problems = models.ManyToManyField(
        "problems.Problem",
        through="ContestProblem",
        related_name="contests",
        verbose_name="Masalalar",
        help_text=(
            "Contest tarkibidagi dasturlash masalalari. "
            "ContestProblem orqali tartib, ball va boshqa "
            "contest-specific sozlamalar boshqariladi."
        ),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contests",
        verbose_name="Tashkilotchi",
        help_text=(
            "Ushbu contestni yaratgan yoki boshqaradigan foydalanuvchi."
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan sana",
        help_text="Contest tizimga yaratilgan vaqt.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan sana",
        help_text="Contest ma'lumotlari oxirgi marta o'zgartirilgan vaqt.",
    )

    class Meta:
        verbose_name = "🏆 Musobaqa"
        verbose_name_plural = "🏆 Musobaqalar"
        ordering = ["-start_time"]

        indexes = [
            models.Index(
                fields=["visibility"],
                name="contest_visibility_idx",
            ),
            models.Index(
                fields=["format"],
                name="contest_format_idx",
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        errors = {}
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                errors["end_time"] = (
                    "Tugash vaqti boshlanish vaqtidan keyin "
                    "bo'lishi kerak."
                )
        if self.registration_deadline and self.start_time:
            if self.registration_deadline > self.start_time:
                errors["registration_deadline"] = (
                    "Ro'yxatdan o'tish muddati contest "
                    "boshlanishidan oldin tugashi kerak."
                )
        if self.duration_minutes is not None:
            if self.duration_minutes <= 0:
                errors["duration_minutes"] = (
                    "Contest davomiyligi 0 dan katta bo'lishi kerak."
                )
        if self.visibility == self.Visibility.PUBLIC:
            # Public contestda key bo'lishi mumkin emas.
            self.access_key = ""

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):

        if not self.slug:
            base_slug = slugify(self.title)
            if not base_slug:
                base_slug = "contest"
            slug = base_slug
            counter = 1
            while (
                Contest.objects
                .exclude(pk=self.pk)
                .filter(slug=slug)
                .exists()
            ):
                counter += 1
                slug = f"{base_slug}-{counter}"

            self.slug = slug

        if self.visibility == self.Visibility.PUBLIC:
            self.access_key = ""

        elif self.visibility == self.Visibility.PRIVATE:
            if not self.access_key:
                self.access_key = secrets.token_urlsafe(32)

        super().save(*args, **kwargs)


    @property
    def status(self):
        """
        Contestning vaqtga asoslangan holati.

        Bu DB field emas.

        Frontend uchun:
            upcoming
            ongoing
            ended

        sifatida ishlatilishi mumkin.
        """

        if not self.start_time or not self.end_time:
            return None

        now = timezone.now()

        if now < self.start_time:
            return "upcoming"

        if now <= self.end_time:
            return "ongoing"

        return "ended"

    @property
    def is_running(self):
        """
        Contest ayni vaqtda davom etyaptimi?
        """

        if not self.start_time or not self.end_time:
            return False

        now = timezone.now()

        return self.start_time <= now <= self.end_time

    @property
    def is_registration_open(self):
        """
        Hozir yangi participant contestga ro'yxatdan o'tishi mumkinmi?

        Qoidalar:

        1. Contest hali boshlanmagan bo'lsa:
           registration_deadline bo'lmasa start_time gacha ochiq.

        2. registration_deadline berilgan bo'lsa:
           deadlinegacha ochiq.

        3. Contest boshlanganidan keyin:
           yangi registration yopiladi.
        """

        if not self.start_time:
            return False

        now = timezone.now()

        if now >= self.start_time:
            return False

        if self.registration_deadline:
            return now <= self.registration_deadline

        return True

    @property
    def is_practice_available(self):
        """
        Contest tugagandan keyin practice qilish mumkinmi?

        Bu faqat:
            - contest tugagan
            - allow_practice=True

        bo'lganda True bo'ladi.
        """

        if not self.allow_practice:
            return False

        if not self.end_time:
            return False

        return timezone.now() > self.end_time

    # ==============================================================
    # FORMAT MANAGEMENT
    # ==============================================================

    def refresh_format(self, commit=True):
        has_problem = self.contest_problems.filter(
            problem__isnull=False
        ).exists()

        has_question = self.contest_problems.filter(
            question__isnull=False
        ).exists()

        if has_problem and has_question:
            new_format = self.Format.MIXED

        elif has_question:
            new_format = self.Format.QUIZ

        elif has_problem:
            new_format = self.Format.CODING

        else:
            new_format = self.Format.CODING

        if self.format != new_format:
            self.format = new_format

            if commit:
                self.save(update_fields=["format", "updated_at"])

        return self.format


class ContestProblem(models.Model):

    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="contest_problems")

    problem = models.ForeignKey(
        "problems.Problem", on_delete=models.PROTECT,
        related_name="contest_links", null=True, blank=True,
        verbose_name="Dasturlash masalasi",
    )
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT,
        related_name="contest_links", null=True, blank=True,
        verbose_name="Test savoli",
    )
    letter = models.CharField(
        max_length=3,
        editable=False,
        blank=True,
        null=True,
        verbose_name="Harf/Raqam",
        help_text="A, B, C ... AA, AB ...",
    )

    order_index = models.PositiveSmallIntegerField(
        verbose_name="Tartib raqami",
    )

    max_score = models.PositiveIntegerField(
        default=100,
        verbose_name="Maksimal ball",
    )

    is_scoring_dynamic = models.BooleanField(
        default=False,
        verbose_name="Dinamik ball",
        help_text="Yoqilsa, ball vaqt/urinish soniga qarab kamayib boradi.",
    )


    def save(self, *args, **kwargs):
        if self.order_index and self.order_index > 0:
            number = self.order_index
            letter = ""

            while number > 0:
                number, remainder = divmod(number - 1, 26)
                letter = chr(65 + remainder) + letter

            self.letter = letter
        else:
            self.letter = None

        super().save(*args, **kwargs)
    class Meta:
        verbose_name = "🔗 Contest — Masala/Savol"
        verbose_name_plural = "🔗 Contest — Masalalar/Savollar"
        ordering = ["order_index"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(problem__isnull=False, question__isnull=True)
                    | models.Q(problem__isnull=True, question__isnull=False)
                ),
                name="contest_problem_belongs_to_problem_xor_question",
            ),
            models.UniqueConstraint(
                fields=["contest", "problem"],
                condition=models.Q(problem__isnull=False),
                name="unique_problem_per_contest",
            ),
            models.UniqueConstraint(
                fields=["contest", "question"],
                condition=models.Q(question__isnull=False),
                name="unique_question_per_contest",
            ),
        ]

    @property
    def is_quiz(self):
        return self.question_id is not None

    @property
    def target_title(self):
        return self.problem.title if self.problem_id else self.question.text[:50]

    def __str__(self):
        return f"{self.contest.title} [{self.letter}] {self.target_title}"


class ContestPrize(models.Model):
    """Mukofotlar uchun alohida mustaqil jadval."""

    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE, related_name='prizes',
        verbose_name="Musobaqa", help_text="Mukofot tegishli bo'lgan tanlov.",
    )
    title = models.CharField(
        max_length=200, verbose_name="Mukofot nomi",
        help_text="Masalan: Noutbuk, Sertifikat, Oltin medal.",
    )
    rank_target = models.PositiveSmallIntegerField(
        verbose_name="O'rin (reyting)",
        help_text="Ushbu mukofot nechinchi o'rin uchun mo'ljallanganini bildiradi (masalan: 1, 2, 3).",
        default=1,
    )
    description = MDTextField(
        blank=True, null=True, verbose_name="Qo'shimcha tavsif",
        help_text="Mukofot haqida batafsil ma'lumot, shartlar yoki izohlar.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prizes',
        verbose_name="Qo'shgan admin", help_text="Mukofotni tizimga kiritgan staff foydalanuvchi.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan sana")

    class Meta:
        verbose_name = "🎁 Mukofot"
        verbose_name_plural = "🎁 Mukofotlar"
        ordering = ['rank_target']
        unique_together = ['contest', 'rank_target']

    def __str__(self):
        return f"{self.contest.title} - {self.title} ({self.rank_target}-o'rin)"
# ======================================================================
# RO'YXATDAN O'TISH, URINISHLAR VA QUIZ JAVOBLARI
# ======================================================================

class ContestRegistration(models.Model):
    """Tanlovga ro'yxatdan o'tish va seans natijalari jadvali."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED = "completed", "Yakunlangan"
        EXPIRED = "expired", "Muddati o'tgan"
        DISQUALIFIED = "disqualified", "Diskvalifikatsiya qilingan"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
        verbose_name="Identifikator", help_text="Har bir seans uchun noyob UUID identifikator.",
    )
    user = models.ForeignKey(
        BaseUser, on_delete=models.CASCADE, related_name='contest_registrations',
        verbose_name="Ishtirokchi", help_text="Tanlovga ro'yxatdan o'tgan foydalanuvchi (Telegram bot foydalanuvchisi).",
    )
    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE, related_name="registrations", db_index=True,
        verbose_name="Tegishli musobaqa", help_text="Ushbu ro'yxatdan o'tish qaysi tanlovga tegishli ekanligi.",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True,
        verbose_name="Holati",
        help_text="Seans hozirgi holati: jarayonda, yakunlangan, muddati o'tgan yoki diskvalifikatsiya qilingan.",
    )

    correct_count = models.PositiveIntegerField("To'g'ri javoblar soni", default=0)
    wrong_count = models.PositiveIntegerField("Noto'g'ri javoblar soni", default=0)
    unanswered_count = models.PositiveIntegerField("Javobsiz qoldirilgan savollar soni", default=0)

    score = models.FloatField(
        default=0.0, verbose_name="Yakuniy ball",
        help_text="Jarima koeffitsiyenti hisobga olingan sof ball.",
    )
    penalty_minutes = models.PositiveIntegerField(
        default=0, verbose_name="Jarima (daqiqa)",
        help_text="ICPC uslubidagi vaqt jarimasi — teng ballda tartiblash uchun ishlatiladi.",
    )
    time_spent_seconds = models.PositiveIntegerField("Sarflangan vaqt (soniya)", default=0)

    total_xp_earned = models.PositiveIntegerField(
        "Ushbu musobaqa jami XP balli", default=0, db_index=True,
        help_text="Foydalanuvchi ushbu testdan ishlagan toza XP ballari. Reyting shu maydon bo'yicha tuziladi.",
    )
    rank = models.PositiveIntegerField(
        "Musobaqadagi o'rni", null=True, blank=True, db_index=True,
        help_text="Tanlov yakunlangach hisoblangan, ushbu ishtirokchining umumiy reytingdagi o'rni (1 — birinchi o'rin).",
    )
    ip_address = models.GenericIPAddressField(
        "IP manzil", null=True, blank=True,
        help_text="Ishtirokchi testni boshlagan paytdagi IP manzili. Firibgarlikni aniqlash uchun foydali.",
    )
    session_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Contest session",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
        related_name='contests_registration', verbose_name="Qayd etgan admin",
        help_text="Ushbu yozuvni tizimga kiritgan/nazorat qiluvchi staff foydalanuvchi.",
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan sana")
    xp_awarded = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name="Yakunlangan sana",
        help_text="Test yakunlangan yoki muddati tugagan payt. Avtomat to'ldiriladi.",
    )

    class Meta:
        unique_together = ['user', 'contest']
        ordering = ['rank', '-score', 'penalty_minutes']
        verbose_name = "🪪 Ro'yxatdan o'tish"
        verbose_name_plural = "👥 Ro'yxatdan o'tganlar"
        indexes = [
            models.Index(fields=['contest', 'rank']),
            models.Index(fields=['contest', '-total_xp_earned']),
            models.Index(fields=['contest', '-score', 'penalty_minutes']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "contest"],
                condition=models.Q(xp_awarded__gt=0),
                name="unique_xp_award_per_user_contest",
            )
        ]

    def __str__(self):
        user_identifier = getattr(self.user, 'username', None) or getattr(self.user, 'telegram_id', "Noma'lum")
        return f"{user_identifier} - {self.contest.title} (+{self.total_xp_earned} XP)"

    @property
    def total_questions_answered(self):
        return self.correct_count + self.wrong_count

    @property
    def accuracy_percent(self):
        total = self.total_questions_answered
        if not total:
            return 0
        return round((self.correct_count / total) * 100, 1)

    @property
    def medal(self):
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        return medals.get(self.rank, "")

    def save(self, *args, **kwargs):
        if self.status in [self.Status.COMPLETED, self.Status.EXPIRED, self.Status.DISQUALIFIED] and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Ball va jarima hisoblash — CODING va QUIZ ikkovi uchun ham ishlaydi
    # ------------------------------------------------------------------
    def recalculate_score(self, commit=True):
        """
        Contest turiga qarab (ICPC / DYNAMIC / SIMPLE) score va penalty_minutes
        maydonlarini qayta hisoblaydi. Har submit/javob'dan keyin yoki contest
        yakunlanganda chaqiriladi. Coding (Submission) va Quiz (ContestAnswer)
        bandlarining ikkalasini ham qo'llab-quvvatlaydi.
        """
        from submissions.models import Submission

        total_score = 0.0
        total_penalty = 0

        for cp in self.contest.contest_problems.select_related("problem", "question").all():

            wrong_before = 0
            accepted_time_offset = None

            if cp.problem_id:
                # ---- Dasturlash masalasi (coding) ----
                subs = self.submissions.filter(problem=cp.problem).order_by("submitted_at")
                accepted = subs.filter(verdict=Submission.VerdictChoices.ACCEPTED).first()
                if not accepted:
                    continue
                wrong_before = subs.filter(
                    submitted_at__lt=accepted.submitted_at
                ).exclude(verdict=Submission.VerdictChoices.ACCEPTED).count()
                accepted_time_offset = accepted.time_offset_seconds

            else:
                # ---- Test savoli (quiz) — faqat 1 marta javob beriladi ----
                answer = self.quiz_answers.filter(contest_problem=cp).first()
                if not answer or not answer.is_correct:
                    continue
                wrong_before = 0  # quiz'da qayta urinish yo'q, jarima bo'lmaydi
                accepted_time_offset = answer.time_offset_seconds

            use_dynamic = cp.is_scoring_dynamic or self.contest.contest_type == Contest.ContestType.DYNAMIC

            if use_dynamic:
                minutes_passed = (accepted_time_offset or 0) // 60
                duration = max(self.contest.duration_minutes, 1)
                decay = cp.max_score * (1 - minutes_passed / (2 * duration))
                attempt_penalty = wrong_before * (cp.max_score * 0.05)
                total_score += max(round(decay - attempt_penalty), cp.max_score * 0.3)
            else:
                total_score += cp.max_score
                if self.contest.contest_type == Contest.ContestType.ICPC:
                    total_penalty += wrong_before * self.contest.penalty_minutes_per_wrong

        self.score = total_score
        self.penalty_minutes = total_penalty
        if commit:
            self.save(update_fields=["score", "penalty_minutes"])
        return total_score, total_penalty

class ContestAnswer(models.Model):
    """
    Contest ichidagi test-savol (Question) turidagi bandga berilgan javob.
    Coding masaladagi Submission'ning quiz uchun analogi — lekin faqat
    BITTA marta javob berish mumkin (qayta urinish yo'q).
    """

    registration = models.ForeignKey(
        ContestRegistration, on_delete=models.CASCADE, related_name="quiz_answers",
        verbose_name="Ro'yxatdan o'tish",
    )
    contest_problem = models.ForeignKey(
        ContestProblem, on_delete=models.CASCADE, related_name="answers",
        verbose_name="Contest bandi",
    )
    choice = models.ForeignKey(
        Choice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contest_answers", verbose_name="Tanlangan variant",
        help_text="Bo'sh bo'lsa — javobsiz qoldirilgan.",
    )
    answered_at = models.DateTimeField(auto_now_add=True, verbose_name="Javob berilgan vaqt")

    class Meta:
        verbose_name = "📮 Contest javobi (Quiz)"
        verbose_name_plural = "📮 Contest javoblari (Quiz)"
        unique_together = ["registration", "contest_problem"]
        indexes = [
            models.Index(fields=["registration", "contest_problem"]),
        ]

    def clean(self):
        super().clean()
        if not self.contest_problem.is_quiz:
            raise ValidationError(
                "ContestAnswer faqat 'question' turidagi ContestProblem uchun yaratilishi mumkin."
            )
        if self.choice_id and self.choice.question_id != self.contest_problem.question_id:
            raise ValidationError(
                "Tanlangan variant ushbu contest bandiga tegishli savolga tegishli emas."
            )

    @property
    def is_true(self):
        return bool(self.choice_id and self.choice.is_correct)

    @property
    def time_offset_seconds(self):
        delta = self.answered_at - self.registration.started_at
        return int(delta.total_seconds())

    def __str__(self):
        status = "✅" if self.is_true else "❌"
        return f"[{status}] {self.registration} — {self.contest_problem.letter}"
    


class CheatFlag(models.Model):
    """Shubhali harakatlar jurnali: tab almashtirish, bir nechta IP va h.k."""

    class Reason(models.TextChoices):
        TAB_SWITCH = "tab_switch", "Tab almashtirildi"
        MULTIPLE_IP = "multiple_ip", "Bir nechta IP manzil"
        COPY_PASTE = "copy_paste", "Ko'p marta copy-paste"
        TIME_ANOMALY = "time_anomaly", "Vaqt anomaliyasi"
        SIMILAR_CODE = "similar_code", "Boshqa foydalanuvchi kodi bilan o'xshashlik"
        MANUAL = "manual", "Qo'lda belgilangan"

    registration = models.ForeignKey(
        ContestRegistration, on_delete=models.CASCADE, related_name="cheat_flags", verbose_name="Ro'yxatdan o'tish",
    )
    reason = models.CharField(max_length=20, choices=Reason.choices, verbose_name="Sabab")
    detail = models.TextField(blank=True, verbose_name="Tafsilot")
    detected_at = models.DateTimeField(auto_now_add=True, verbose_name="Aniqlangan vaqt")
    reviewed = models.BooleanField(default=False, verbose_name="Ko'rib chiqilgan")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_cheat_flags", verbose_name="Ko'rib chiqqan admin",
    )

    class Meta:
        verbose_name = "🚩 Shubhali harakat"
        verbose_name_plural = "🚩 Shubhali harakatlar"
        ordering = ["-detected_at"]

    def __str__(self):
        return f"{self.registration} — {self.get_reason_display()}"