"""
Milliy attestatsiya tizimi — YAKUNIY model qatlami (v3).

ARXITEKTURA: "thin models, fat services"

Ushbu versiyada oldingi review'larda topilgan barcha nomuvofiqliklar tuzatildi:
  - TestSessionQuestion.order maydoni qaytarildi (scoring.py shu bilan mos)
  - Subject.theta_low/theta_high (ishlatilmagan, o'lik) olib tashlandi —
    ScoringPolicy yagona haqiqat manbai (single source of truth)
  - RaschCalibration statuslari izchil: PENDING -> RUNNING -> COMPLETED ->
    (QUALITY CHECK) -> ACTIVE / REJECTED, eskisi -> RETIRED
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ============================================================
# SUBJECT
# ============================================================

class Subject(models.Model):
    """Har bir fan — mustaqil Rasch o'lchov shkalasiga ega."""

    name = models.CharField("Fan nomi", max_length=100)
    slug = models.SlugField("Slug", unique=True)
    is_active = models.BooleanField("Faol", default=True)

    rasch_min_persons = models.PositiveIntegerField(
        "Kalibratsiya uchun minimal ishtirokchilar", default=100,
        help_text="Kalibratsiya statistik jihatdan barqaror bo'lishi uchun kamida shuncha ishtirokchi kerak.",
    )
    rasch_recalibration_response_threshold = models.PositiveIntegerField(
        "Qayta kalibratsiya chegarasi (yangi javoblar)", default=500,
    )
    rasch_prior_variance = models.FloatField(
        "MAP prior variance", default=1.0,
        help_text="N(0, sigma²) prior. Standart = 1.0.",
    )
    rasch_theta_min = models.FloatField("θ minimum", default=-6.0)
    rasch_theta_max = models.FloatField("θ maximum", default=6.0)

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"

    def __str__(self):
        return self.name

    def get_active_calibration(self):
        return (
            self.rasch_calibrations
            .filter(status=RaschCalibration.Status.ACTIVE, is_active=True)
            .order_by("-version")
            .first()
        )


# ============================================================
# SCORING POLICY
# ============================================================

class ScoringPolicy(models.Model):
    """
    Fanning baholash siyosati — versiyalangan. Bu yagona joy, qayerda
    theta -> ball -> daraja aylantirish qoidalari saqlanadi.
    """
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="scoring_policies")
    version = models.PositiveIntegerField(default=1)
    name = models.CharField("Siyosat nomi", max_length=100)
    is_active = models.BooleanField("Faol", default=False)

    theta_low = models.FloatField("θ → 0 ball", default=-4.0)
    theta_high = models.FloatField("θ → 100 ball", default=4.0)

    grade_a_plus_min = models.FloatField("A+ minimum", default=70.0)
    grade_a_min = models.FloatField("A minimum", default=65.0)
    grade_b_plus_min = models.FloatField("B+ minimum", default=60.0)
    grade_b_min = models.FloatField("B minimum", default=55.0)
    grade_c_plus_min = models.FloatField("C+ minimum", default=50.0)
    grade_c_min = models.FloatField("C minimum", default=46.0)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        verbose_name = "Baholash siyosati"
        verbose_name_plural = "Baholash siyosatlari"
        constraints = [
            models.UniqueConstraint(fields=["subject", "version"], name="unique_policy_version_per_subject"),
            models.UniqueConstraint(
                fields=["subject"], condition=models.Q(is_active=True),
                name="unique_active_policy_per_subject",
            ),
        ]

    def __str__(self):
        return f"{self.subject.name} — {self.name} v{self.version}"

    def get_grade(self, scaled_score: float) -> tuple[str, str]:
        if scaled_score >= self.grade_a_plus_min:
            return "A+", "A'lo"
        if scaled_score >= self.grade_a_min:
            return "A", "A'lo"
        if scaled_score >= self.grade_b_plus_min:
            return "B+", "Yaxshi"
        if scaled_score >= self.grade_b_min:
            return "B", "Yaxshi"
        if scaled_score >= self.grade_c_plus_min:
            return "C+", "Qoniqarli"
        if scaled_score >= self.grade_c_min:
            return "C", "Qoniqarli"
        return "NC", "Qoniqarsiz"

    def theta_to_scaled(self, theta: float) -> float:
        pct = (theta - self.theta_low) / (self.theta_high - self.theta_low) * 100.0
        return round(max(0.0, min(100.0, pct)), 2)


# ============================================================
# TEST / QUESTION / CHOICE
# ============================================================

class TestEnrollment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="test_enrollments")
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name="enrollments")
    amount = models.DecimalField("To'lov summasi", max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "🛒 Sotib olingan test"
        verbose_name_plural = "🛒 Sotib olingan testlar"
        unique_together = ('user', 'test')
        indexes = [models.Index(fields=["user", "test"])]

    def __str__(self):
        return f"{self.user} -> {self.test.title}"


class Test(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="tests", verbose_name="Fan")
    title = models.CharField("Test nomi", max_length=255)
    slug = models.SlugField("Slug", max_length=255, unique=True)
    description = models.TextField("Test sharti", null=True, blank=True)

    duration_minutes = models.PositiveIntegerField("Davomiyligi (daqiqa)", default=60)
    random_questions_count = models.PositiveIntegerField(
        "Tasodifiy savollar soni", default=0,
        help_text="0 = barcha savollar ko'rsatiladi.",
    )
    rasch_theta_pass_threshold = models.FloatField(
        "O'tish chegarasi (θ, logit)", default=0.0,
    )
    max_attempts = models.PositiveIntegerField("Maksimal urinishlar soni", default=1)
    access_code = models.CharField("Kirish kodi", max_length=50, blank=True, null=True)
    is_active = models.BooleanField("Faol", default=True, db_index=True)
    start_time = models.DateTimeField("Boshlanish vaqti")
    end_time = models.DateTimeField("Tugash vaqti")

    price = models.DecimalField("Test narxi", max_digits=10, decimal_places=2, default=0.00)
    discount_price = models.DecimalField("Chegirmadagi narx", max_digits=10, decimal_places=2, null=True, blank=True)
    max_lifelines = models.PositiveIntegerField("Maksimal Yordam soni", default=3)

    reveal_correct_answers = models.BooleanField(
        "To'g'ri javoblarni ochish", default=False,
        help_text="Savollar banki qayta ishlatilsa, O'CHIRIQ holda qoldiring.",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tests', verbose_name="Yaratuvchi",
    )
    questions = models.ManyToManyField("Question", through="TestQuestion", related_name="tests", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "📋 Test"
        verbose_name_plural = "📋 Testlar"
        ordering = ["-id"]

    def __str__(self):
        return f"Test — {self.title}"

    @property
    def is_available(self):
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    @property
    def is_finished(self):
        return timezone.now() > self.end_time


class Question(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="questions", verbose_name="Fan")
    text = models.TextField("Savol matni")
    explanation = models.TextField("Javob izohi", blank=True, null=True)
    is_active = models.BooleanField("Faol", default=True, db_index=True)
    dif_group = models.CharField(
        "DIF guruhi", max_length=50, blank=True, null=True,
        help_text="Kelajakda Differential Item Functioning tahlili uchun.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_questions', verbose_name="Yaratuvchi",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "❓ Savol"
        verbose_name_plural = "❔ Savollar"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["subject", "dif_group"])]

    def __str__(self):
        return f"Savol #{self.id}: {self.text[:40]}..."

    @property
    def active_rasch_parameter(self):
        calibration = self.subject.get_active_calibration()
        if calibration is None:
            return None
        return self.rasch_parameters.filter(calibration=calibration).first()


class TestQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="test_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="test_usages")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Test savoli"
        verbose_name_plural = "Test savollari"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["test", "question"], name="unique_question_per_test"),
        ]

    def __str__(self):
        return f"{self.test_id} -> Savol #{self.question_id}"


class Choice(models.Model):
    question = models.ForeignKey("Question", on_delete=models.CASCADE, related_name="choices", verbose_name="Savol")
    text = models.TextField("Variant matni")
    is_correct = models.BooleanField("To'g'ri javob", default=False, db_index=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "🔘 Javob varianti"
        verbose_name_plural = "✅ Javob variantlari"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=['question'], condition=models.Q(is_correct=True),
                name='unique_correct_choice_per_question',
            ),
        ]

    def __str__(self):
        status = "✅" if self.is_correct else "❌"
        return f"[{status}] {self.text[:40]}..."


# ============================================================
# TEST SESSION
# ============================================================

class TestSession(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED = "completed", "Yakunlangan"
        EXPIRED = "expired", "Muddati o'tgan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="Seans ID")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="test_sessions", verbose_name="Foydalanuvchi",
    )
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name="sessions", verbose_name="Test")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)

    # --- Kalibratsiya snapshot — sessiya BOSHLANGANDA o'rnatiladi (services/sessions.py) ---
    rasch_calibration = models.ForeignKey(
        "RaschCalibration", on_delete=models.PROTECT, null=True, blank=True,
        related_name="sessions", verbose_name="Ishlatilgan kalibratsiya",
    )
    scoring_policy = models.ForeignKey(
        ScoringPolicy, on_delete=models.PROTECT, null=True, blank=True,
        related_name="sessions", verbose_name="Ishlatilgan siyosat",
    )

    rasch_theta = models.FloatField(null=True, blank=True, verbose_name="Qobiliyat (θ, logit)")
    rasch_se = models.FloatField(null=True, blank=True, verbose_name="Standart xatolik (SE)")
    rasch_converged = models.BooleanField(default=False, verbose_name="θ baholash yaqinlashdimi")
    person_infit = models.FloatField(null=True, blank=True)
    person_outfit = models.FloatField(null=True, blank=True)

    scaled_score = models.FloatField(null=True, blank=True, verbose_name="0-100 shkala ball")
    grade = models.CharField("Daraja", max_length=10, blank=True)
    grade_description = models.CharField("Daraja tavsifi", max_length=50, blank=True)

    is_provisional = models.BooleanField(
        "Vaqtinchalik natija", default=False,
        help_text="True bo'lsa — savollarning muhim qismi hali kalibrlanmagan.",
    )
    uncalibrated_question_count = models.PositiveIntegerField(default=0)

    raw_percentage = models.FloatField(default=0.0, verbose_name="Oddiy foiz (%)")
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    unanswered_count = models.PositiveIntegerField(default=0)

    lifelines_used = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "⏱ Test Seansi"
        verbose_name_plural = "⏱ Test Seanslari"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "test", "status"]),
            models.Index(fields=["status", "-started_at"]),
            models.Index(fields=["rasch_calibration"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.test.title}"

    @property
    def passed(self):
        if self.rasch_theta is None:
            return False
        return self.rasch_theta >= self.test.rasch_theta_pass_threshold

    def complete(self, requesting_user=None):
        from .services.scoring import score_session
        return score_session(self, requesting_user=requesting_user)


class TestSessionQuestion(models.Model):
    """Sessiya uchun tanlangan savollar — tartib bilan (random_questions_count qo'llanganda ham)."""
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name="session_questions")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="session_usages")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Seans savoli"
        verbose_name_plural = "Seans savollari"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["session", "question"], name="unique_question_per_session"),
        ]

    def __str__(self):
        return f"{self.session_id} -> Savol #{self.question_id}"


class UserResponse(models.Model):
    session = models.ForeignKey(
        "TestSession", on_delete=models.CASCADE, related_name="responses",
        null=True, blank=True, verbose_name="Test seansi",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_responses", verbose_name="Foydalanuvchi",
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="user_responses", verbose_name="Savol")
    choice = models.ForeignKey(
        Choice, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Tanlangan variant", help_text="Bo'sh = javobsiz qoldirilgan.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "🎯 Foydalanuvchi Javobi"
        verbose_name_plural = "🎯 Foydalanuvchi Javoblari"
        constraints = [
            models.UniqueConstraint(fields=["session", "question"], name="unique_response_per_session_question"),
        ]

    def clean(self):
        super().clean()
        if self.choice_id and self.choice.question_id != self.question_id:
            raise ValidationError({"choice": "Tanlangan javob ushbu savolga tegishli emas."})
        if self.session_id and self.user_id and self.user_id != self.session.user_id:
            raise ValidationError({"user": "Javob foydalanuvchisi seans foydalanuvchisiga mos emas."})


# ============================================================
# RASCH — Fan darajasidagi kalibratsiya
# ============================================================

class RaschCalibration(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        RUNNING = "running", "Hisoblanmoqda"
        COMPLETED = "completed", "Yakunlandi (ko'rib chiqilmoqda)"
        FAILED = "failed", "Xatolik"
        REJECTED = "rejected", "Rad etildi"
        ACTIVE = "active", "Faol"
        RETIRED = "retired", "Almashtirildi"

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="rasch_calibrations")
    version = models.PositiveIntegerField()
    algorithm_version = models.CharField(max_length=50, default="rasch-mml-v3")
    response_policy = models.CharField(max_length=30, default="first_attempt_only")

    sample_size = models.PositiveIntegerField(default=0, help_text="Noyob shaxslar (userlar) soni.")
    response_count = models.PositiveIntegerField(default=0)
    item_count = models.PositiveIntegerField(default=0)
    mean_beta = models.FloatField(default=0.0)
    std_beta = models.FloatField(default=0.0)
    min_beta = models.FloatField(default=0.0)
    max_beta = models.FloatField(default=0.0)
    converged = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    data_cutoff_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        verbose_name = "Rasch kalibratsiyasi"
        verbose_name_plural = "Rasch kalibratsiyalari"
        constraints = [
            models.UniqueConstraint(fields=["subject", "version"], name="unique_rasch_calibration_version"),
            models.UniqueConstraint(
                fields=["subject"], condition=models.Q(is_active=True),
                name="unique_active_calibration_per_subject",
            ),
        ]
        indexes = [
            models.Index(fields=["subject", "status"]),
            models.Index(fields=["subject", "is_active"]),
        ]

    def __str__(self):
        return f"{self.subject.name} — v{self.version} ({self.status})"


class RaschItemParameter(models.Model):
    calibration = models.ForeignKey(RaschCalibration, on_delete=models.CASCADE, related_name="item_parameters")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="rasch_parameters")

    beta = models.FloatField("β qiyinchilik", default=0.0)
    beta_se = models.FloatField("β SE", default=999.0)
    infit = models.FloatField(null=True, blank=True)
    outfit = models.FloatField(null=True, blank=True)
    sample_size = models.PositiveIntegerField(default=0)
    is_calibrated = models.BooleanField(default=False)
    flagged_for_review = models.BooleanField(default=False)
    is_extreme = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rasch item parametri"
        verbose_name_plural = "Rasch item parametrlari"
        constraints = [
            models.UniqueConstraint(fields=["calibration", "question"], name="unique_item_per_calibration"),
        ]
        indexes = [models.Index(fields=["question"])]

    def __str__(self):
        return f"Savol #{self.question_id} (v{self.calibration.version}) β={self.beta:.2f}"


class UserSubjectAbility(models.Model):
    """Foydalanuvchining fan bo'yicha JORIY ability'si — read model / kesh."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subject_abilities")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="user_abilities")

    theta = models.FloatField("Qobiliyat (θ)")
    theta_se = models.FloatField("Standart xatolik", default=999.0)
    person_infit = models.FloatField(null=True, blank=True)
    person_outfit = models.FloatField(null=True, blank=True)

    calibration = models.ForeignKey(RaschCalibration, on_delete=models.PROTECT, related_name="subject_abilities")
    calibration_version = models.PositiveIntegerField()

    response_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foydalanuvchi fan darajasi"
        verbose_name_plural = "Foydalanuvchi fan darajalari"
        constraints = [
            models.UniqueConstraint(fields=["user", "subject"], name="unique_user_subject_ability"),
        ]
        indexes = [
            models.Index(fields=["user", "subject"]),
            models.Index(fields=["subject", "-theta"]),
        ]

    def __str__(self):
        return f"{self.user_id} — {self.subject.name} θ={self.theta:.2f}"