"""
quizs/models.py
================

Testlar, savollar, test seanslari, reyting (UserRank) va sertifikatlar
uchun model qatlami.

Salbiy baholash (negative marking) formulasi:

    S = Sum(C_i * P_i) - Sum(W_i * P_i * K)

    bu yerda:
        C_i — to'g'ri javob berilgan savol uchun 1, aks holda 0
        W_i — noto'g'ri javob berilgan savol uchun 1, aks holda 0
        P_i — savolning bazaviy balli (xp)
        K   — Test.penalty_coefficient (jarima koeffitsiyenti, masalan 0.33)

Javobsiz qoldirilgan (selected_choice=None) savollar uchun ball ham
qo'shilmaydi, ham ayirilmaydi (0 ball).

XP/Rank yangilanishi FAQAT shu fayldagi
``TestSession.calculate_mathematical_score()`` ichida, bitta
``transaction.atomic()`` blokida amalga oshiriladi. ``signals.py``
takroran XP qo'shmaydi — u faqat sertifikat chiqarish bilan shug'ullanadi.
"""
import base64
import io
import uuid

import qrcode
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.template import Context, Template
from django.utils import timezone
from django.utils.functional import cached_property
from weasyprint import HTML

from video.models import Video
from baseuser.models import BaseUser
from courses.models import Course, Lesson
from problems.models import Problem
from mdeditor.fields import MDTextField

# ─────────────────────────────────────────────
#  1. FOYDALANUVCHI REYTINGI
# ─────────────────────────────────────────────
class UserRank(models.Model):
    """Talabaning umumiy to'plagan XP'si va shu asosdagi unvoni (daraja)."""

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Yangi boshlovchi"
        BRONZE = "bronze", "Bronza"
        SILVER = "silver", "Kumush"
        GOLD = "gold", "Oltin"
        PRO = "pro", "Professional"

    # Daraja chegaralari (total_xp >= chegara -> shu daraja)
    LEVEL_THRESHOLDS = (
        (10_000, Level.PRO),
        (5_000, Level.GOLD),
        (3_000, Level.SILVER),
        (1_000, Level.BRONZE),
        (0, Level.BEGINNER),
    )

    user = models.OneToOneField(
        BaseUser, on_delete=models.CASCADE, related_name="rank_profile"
    )
    total_xp = models.PositiveIntegerField("Jami to'plangan XP", default=0, db_index=True)
    level = models.CharField(
        "Unvon (Daraja)", max_length=20, choices=Level.choices, default=Level.BEGINNER
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "🏅 Foydalanuvchi Reytingi"
        verbose_name_plural = "🏅 Foydalanuvchilar Reytingi"
        ordering = ["-total_xp"]

    def __str__(self):
        return f"{self.user.username} — {self.total_xp} XP ({self.get_level_display()})"

    def compute_level(self):
        """``total_xp`` asosida mos darajani (level) hisoblab qaytaradi (DB'ga yozmaydi)."""
        for threshold, level in self.LEVEL_THRESHOLDS:
            if self.total_xp >= threshold:
                return level
        return self.Level.BEGINNER

    def update_level(self, commit=True):
        """Joriy ``total_xp``'ga mos darajani aniqlaydi va kerak bo'lsa DB'ni yangilaydi.

        ``commit=True`` bo'lsa, ``save()`` signallarini chaqirmasdan,
        faqat ``level`` va ``updated_at`` maydonlarini ``UPDATE`` qiladi.
        """
        new_level = self.compute_level()
        changed = new_level != self.level
        self.level = new_level

        if commit and changed:
            UserRank.objects.filter(pk=self.pk).update(
                level=self.level, updated_at=timezone.now()
            )
        return changed


# ─────────────────────────────────────────────
#  2. TEST (IMTIHON)
# ─────────────────────────────────────────────
class Test(models.Model):
    """Imtihonlar va darslik ichidagi testlarni boshqaruvchi asosiy model."""

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        related_name="tests",
        blank=True,
        null=True,
        help_text="Agar bo'sh qolsa, bu mustaqil umumiy imtihon testi hisoblanadi.",
    )
    title = models.CharField("Test nomi", max_length=255)
    slug = models.SlugField(max_length=500)
    duration_minutes = models.PositiveIntegerField("Davomiyligi (daqiqa)", default=60)
    question_count = models.PositiveIntegerField("Savollar soni", default=20)
    min_pass_percentage = models.PositiveIntegerField(
        "O'tish foizi", default=60, validators=[MaxValueValidator(100)]
    )
    randomize_questions = models.BooleanField("Savollarni aralashtirish", default=False)
    max_attempts = models.PositiveIntegerField(
        "Maksimal urinishlar soni (0 = cheksiz)", default=0
    )
    access_code = models.CharField(
        "Kirish kodi (bo'sh = ochiq)", max_length=50, blank=True, null=True
    )
    is_active = models.BooleanField("Faol", default=True, db_index=True)
    start_time = models.DateTimeField(verbose_name="Boshlanish vaqti")
    end_time = models.DateTimeField(verbose_name="Tugash vaqti")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    price = models.DecimalField(
        "Kurs narxi", 
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Kursning asosiy narxi (masalan: 500000.00)"
    )
    discount_price = models.DecimalField(
        "Chegirmadagi narx", 
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        help_text="Agar chegirma bo'lsa, yakuniy narxni kiriting"
    )
    # Matematika va o'yin balansi maydonlari
    penalty_coefficient = models.FloatField(
        "Jarima koeffitsiyenti (K)",
        default=0.33,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=(
            "Salbiy baholash koeffitsiyenti. Noto'g'ri javob uchun savol balli shu "
            "qiymatga ko'paytirilib, umumiy balldan ayriladi. Masalan: 0.33 kiritilsa, "
            "10 ballik savoldan xato qilgan talabadan 3.3 ball chegirib tashlanadi."
        ),
    )
    max_lifelines = models.PositiveIntegerField(
        "Maksimal Reler (Lifeline) soni",
        default=3,
        help_text=(
            "Talaba ushbu imtihon davomida ko'pi bilan nechta savolni jarimasiz "
            "o'tkazib yubora olish cheklovi. Lifeline ishlatilganda savolga 0 ball "
            "beriladi va jarima qo'llanilmaydi."
        ),
    )
    intro_video = models.ForeignKey(
        Video, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="tests",
        verbose_name="Kirish yoki qoidalar videosi"
    )

    class Meta:
        verbose_name = "📝 Test"
        verbose_name_plural = "📑 Testlar"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["start_time", "end_time"]),
            models.Index(fields=["is_active", "start_time"]),
        ]

    def __str__(self):
        return f"Test — {self.title}"

    @property
    def is_available(self):
        """Test hozirgi vaqtda faol va boshlanish/tugash oralig'idami?

        ``cached_property`` ATAMA emas — chunki ``timezone.now()`` har chaqiruvda
        yangi qiymat qaytarishi shart. Modelni keshlangan holda saqlab, bir necha
        marta ``is_available``ni o'qish noto'g'ri natija berib qo'yardi.
        """
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    @cached_property
    def total_possible_xp(self):
        """Testdagi barcha savollarning XP yig'indisi (1 so'rovda keshlanadi)."""
        return self.questions.aggregate(total=models.Sum("xp"))["total"] or 0


# ─────────────────────────────────────────────
#  3. SAVOL VA JAVOB VARIANTLARI
# ─────────────────────────────────────────────
class Question(models.Model):
    """Polimorfik savollar: Ham ``Test``, ham ``Problem``ga xizmat qila oladi."""

    class Difficulty(models.TextChoices):
        EASY = "easy", "Oson"
        MEDIUM = "medium", "O'rtacha"
        HARD = "hard", "Qiyin"

    # Qiyinchilik darajasiga qarab avtomatik beriladigan standart XP qiymatlari
    DEFAULT_XP_BY_DIFFICULTY = {
        Difficulty.EASY: 10,
        Difficulty.MEDIUM: 25,
        Difficulty.HARD: 50,
    }

    problem = models.ForeignKey(
        Problem, on_delete=models.SET_NULL, related_name="questions", null=True, blank=True
    )
    test = models.ForeignKey(
        Test, on_delete=models.SET_NULL, related_name="questions", null=True, blank=True
    )
    difficulty = models.CharField(
        max_length=10, choices=Difficulty.choices, default=Difficulty.EASY
    )
    xp = models.PositiveIntegerField(
        default=10, validators=[MinValueValidator(10), MaxValueValidator(100)]
    )
    explanation_video = models.ForeignKey(
        Video, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="questions",
        verbose_name="Savol video tahlili",
        help_text="Talaba xato qilganda javobni tushunishi uchun video darslik."
    )
    text = MDTextField(verbose_name="Savol matni")
    order = models.PositiveIntegerField("Tartib raqami", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "❓ Savol"
        verbose_name_plural = "❔ Savollar"
        ordering = ["order", "created_at"]

    def __str__(self):
        return self.text[:50]

    def clean(self):
        """Biznes mantiq xavfsizligi: savol aniq bir joyga (Test yoki Problem) tegishli bo'lsin."""
        if not self.problem and not self.test:
            raise ValidationError(
                "Savol kamida bitta joyga (Problem yoki Test) bog'lanishi shart!"
            )
        if self.problem and self.test:
            raise ValidationError(
                "Savol bir vaqtning o'zida ham Problemga, ham Testga bog'lana olmaydi!"
            )

    def save(self, *args, **kwargs):
        self.full_clean(exclude=[f.name for f in self._meta.fields if f.name not in ("problem", "test")])
        if not self.xp:
            self.xp = self.DEFAULT_XP_BY_DIFFICULTY.get(self.difficulty, 10)
        super().save(*args, **kwargs)


class Choice(models.Model):
    """Savol javoblari variantlari."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = MDTextField(verbose_name="Savol matni")
    is_correct = models.BooleanField("To'g'ri javob", default=False, db_index=True)
    explanation = MDTextField(verbose_name="Javob izohi / Tushuntirish", blank=True, null=True)
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "🔘 Javob varianti"
        verbose_name_plural = "✅ Javob variantlari"
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:50]


# ─────────────────────────────────────────────
#  4. SERTIFIKAT SHABLONI
# ─────────────────────────────────────────────

class CertificateTemplate(models.Model):
    """Sertifikat uchun faqat sozlamalar, matnlar va rasmlarni saqlovchi eng minimal model."""

    name = models.CharField("Shablon konfiguratsiya nomi", max_length=255)
    
    # Tashkilot ma'lumotlari
    organization_name = models.CharField("Tashkilot nomi", max_length=255, default="Platforma.uz")
    verify_domain = models.CharField("Tasdiqlash domeni", max_length=100, default="platforma.uz")
    
    # Sertifikat ichidagi tabrik matni
    congratulation_text = models.TextField(
        "Tabrik matni", 
        default="Tizim tomonidan tashkil etilgan maxsus imtihon sinovlaridan muvaffaqiyatli o'tib, yuqori natijalarni ko'rsatganligi uchun topshirildi."
    )
    
    # Mentor va imzo ma'lumotlari
    mentor_name = models.CharField("Mas'ul shaxs (Mentor) ismi", max_length=150, default="cfm")
    mentor_status = models.CharField("Mentor lavozimi", max_length=150, default="Kurs Mentori")
    mentor_signature = models.ImageField("Mentor imzosi (PNG)", upload_to="certificates/signatures/", null=True, blank=True)
    
    # Qo'shimcha grafik bezaklar
    logo_image = models.ImageField("Platforma Logotipi", upload_to="certificates/logos/", null=True, blank=True)
    illustration_image = models.ImageField("Pastdagi rasm (Illustration)", upload_to="certificates/illustrations/", null=True, blank=True)

    class Meta:
        verbose_name = "📜 Sertifikat Sozlamasi"
        verbose_name_plural = "📜 Sertifikat Sozlamalari"

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  5. TEST SEANSI VA JAVOBLAR
# ─────────────────────────────────────────────
class TestSession(models.Model):
    """Foydalanuvchining test topshirish seansi va matematik hisob-kitobi."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED = "completed", "Yakunlangan"
        EXPIRED = "expired", "Muddati o'tgan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name="test_sessions")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="sessions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)

    # Salbiy baholash natijalari (statistika)
    score = models.FloatField("Yakuniy ball (S)", default=0.0)
    correct_count = models.PositiveIntegerField("To'g'ri javoblar soni", default=0)
    wrong_count = models.PositiveIntegerField("Noto'g'ri javoblar soni", default=0)
    unanswered_count = models.PositiveIntegerField(
        "Javobsiz qoldirilgan savollar soni", default=0
    )
    total_xp_earned = models.PositiveIntegerField(
        "UserRank.total_xp ga qo'shilgan XP",
        default=0,
        help_text="Faqat ma'lumot/statistika uchun; signals.py bu maydonni o'qib XP qo'shmaydi.",
    )

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "⏱ Test Seansi"
        verbose_name_plural = "⏱ Test Seanslari"
        indexes = [
            models.Index(fields=["user", "test", "status"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.test.title} ({self.status})"

    def calculate_percentage(self):
        """Yig'ilgan ballni testning umumiy XP'siga nisbatan foizga aylantiradi.

        Manfiy ball 0% sifatida hisoblanadi (talabaga "-15%" ko'rsatish noqulay).
        """
        total_possible = self.test.total_possible_xp
        if total_possible <= 0:
            return 0.0
        return max(0.0, (self.score / total_possible) * 100)

    def calculate_mathematical_score(self):
        """``S = Sum(C*P) - Sum(W*P*K)`` formulasi bo'yicha yakuniy ballni hisoblaydi.

        Bir vaqtning o'zida:
          * ``score``, ``correct_count``, ``wrong_count``, ``unanswered_count``,
            ``total_xp_earned``, ``status``, ``completed_at`` maydonlarini yangilaydi;
          * ``UserRank.total_xp``ni xavfsiz (atomik) oshiradi va darajani yangilaydi.

        Bu metod ichidagi XP qo'shish — tizimdagi YAGONA joy bo'lib qoladi.
        ``signals.py`` bu jarayonni TAKRORLAMAYDI.
        """
        penalty_k = self.test.penalty_coefficient

        correct_count = 0
        wrong_count = 0
        unanswered_count = 0
        total_score = 0.0

        responses = self.responses.select_related("question", "selected_choice")

        for response in responses:
            question_points = response.question.xp

            if response.selected_choice is None:
                # Javobsiz qoldirilgan savol: 0 ball (na qo'shiladi, na ayriladi)
                unanswered_count += 1
                continue

            if response.selected_choice.is_correct:
                correct_count += 1
                total_score += question_points
            else:
                wrong_count += 1
                total_score -= question_points * penalty_k

        rounded_score = round(total_score, 2)
        # UserRank.total_xp manfiy bo'lmasligi uchun, faqat musbat qismi qo'shiladi
        xp_to_award = max(0, int(rounded_score))

        with transaction.atomic():
            self.score = rounded_score
            self.correct_count = correct_count
            self.wrong_count = wrong_count
            self.unanswered_count = unanswered_count
            self.total_xp_earned = xp_to_award
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
            self.save(
                update_fields=[
                    "score",
                    "correct_count",
                    "wrong_count",
                    "unanswered_count",
                    "total_xp_earned",
                    "status",
                    "completed_at",
                ]
            )

            rank_profile, _ = UserRank.objects.select_for_update().get_or_create(user=self.user)
            rank_profile.total_xp = max(0, rank_profile.total_xp + xp_to_award)
            rank_profile.save(update_fields=["total_xp", "updated_at"])
            rank_profile.update_level(commit=True)

        return self.score


class UserResponse(models.Model):
    """Talabaning har bir savolga bergan javobi."""

    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="user_responses")
    # Agar null bo'lsa, talaba bu savolni o'tkazib yuborgan (javob bermagan) hisoblanadi
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "🎯 Foydalanuvchi Javobi"
        verbose_name_plural = "🎯 Foydalanuvchi Javoblari"
        # Xavfsizlik: bitta savolga bitta javob
        unique_together = ("session", "question")

    def __str__(self):
        status_text = "Javob berilgan" if self.selected_choice else "Javobsiz qoldirilgan"
        return f"{self.session.user.username} -> Savol №{self.question_id} [{status_text}]"


# ─────────────────────────────────────────────
#  6. BERILGAN SERTIFIKATLAR
# ─────────────────────────────────────────────
from django.template.loader import render_to_string
class Certificate(models.Model):
    """
    Kurs (Course), Musobaqa (Contest) va Testlar uchun to'g'ridan-to'g'ri 
    manbaga munosabat o'rnatuvchi, premium va tozalangan sertifikat modeli.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name="certificates")
    
    # ⚡️ YANGI TO'G'RIDAN-TO'G'RI BOG'LANISHLAR (Shtamplar):
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_certificates"
    )
    test = models.ForeignKey(
        Test, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_test_certificates"
    )
    # Agarda loyihangizda 'Contest' modeli jismonan bor bo'lsa, ushbu satrni yoqing:
    # contest = models.ForeignKey(Contest, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_contest_certificates")
    
    # Mantiqiy sessiya (Test natijasi hisoblangan joy)
    test_session = models.OneToOneField(
        TestSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_test_certificate"
    )

    # Identifikatsiya va PDF fayllari
    certificate_code = models.CharField("Sertifikat ID/Kodi", max_length=100, unique=True, blank=True)
    qr_code_image = models.ImageField("QR Kod", upload_to="certificates/qrcodes/", blank=True, null=True)
    pdf_file = models.FileField("PDF Fayl", upload_to="certificates/pdfs/", blank=True, null=True)
    issued_at = models.DateTimeField("Berilgan vaqti", auto_now_add=True)

    class Meta:
        verbose_name = "📜 Berilgan Sertifikat"
        verbose_name_plural = "📜 Berilgan Sertifikatlar"

    def __str__(self):
        return f"{self.certificate_code} — {self.user.username}"

    def clean(self):
        """Xavfsizlik validationi: Sertifikat kamida bitta aniq manba uchun berilishi shart."""
        # Agar contest maydonini yoqqan bo'lsangiz, shartga qo'shib qo'ying: 'and not self.contest'
        if not self.course and not self.test:
            raise ValidationError("Sertifikat uchun manba (Kurs yoki Test) ko'rsatilishi shart!")

    def _get_certificate_title(self):
        """Sertifikat markazida chiqadigan Kurs yoki Test nomini aniqlash."""
        if self.course:
            return self.course.title
        # if hasattr(self, 'contest') and self.contest: return self.contest.title
        if self.test:
            return self.test.title
        return "Maxsus Yo'nalish"

    @staticmethod
    def _generate_unique_code():
        """CERT-2026-XXXXXX formatida unikal kod hosil qilish."""
        year = timezone.now().year
        for _ in range(10):
            candidate = f"CERT-{year}-{uuid.uuid4().hex[:6].upper()}"
            if not Certificate.objects.filter(certificate_code=candidate).exists():
                return candidate
        raise RuntimeError("Unikal kod generatsiya qilinmadi.")

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["qr_code_image", "pdf_file", "certificate_code"])

        if not self.certificate_code:
            self.certificate_code = self._generate_unique_code()

        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Fayllar yo'q bo'lsa, chigalliksiz ketma-ket generatsiya qilish
        if is_new or not self.qr_code_image or not self.pdf_file:
            updated_fields = []

            if not self.qr_code_image:
                self.generate_qr_code()
                updated_fields.append("qr_code_image")

            if not self.pdf_file:
                self.generate_pdf_file()
                updated_fields.append("pdf_file")

            if updated_fields:
                super().save(update_fields=updated_fields)

    def generate_qr_code(self):
        """QR-kodni xotirada yaratib fayl tizimiga va keshga yozadi."""
        site_url = getattr(settings, "SITE_URL", "https://platforma.uz")
        verify_url = f"{site_url}/certificates/verify/{self.certificate_code}/"

        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(verify_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        
        self._qr_bytes = buffer.getvalue()
        self.qr_code_image.save(f"qr-{self.certificate_code}.png", ContentFile(self._qr_bytes), save=False)

    def generate_pdf_file(self):
        """Manbaga tegishli default shablon sozlamalarini avtomat topib, PDF yaratadi."""
        full_name = self.user.full_name or self.user.username
        title = self._get_certificate_title()
        
        # ⚡️ AVTOMATIK SHABLONNI TOPISH MANTIQI:
        # Tizim Kurs yoki Testga tegishli bo'lgan birinchi global sozlamani qidiradi.
        # Agar topilmasa, xato bermasligi uchun bo'sh ob'ekt (default) yaratadi.
        template_config = None
        if self.course:
            template_config = CertificateTemplate.objects.filter(name__icontains="kurs").first()
        elif self.test:
            template_config = CertificateTemplate.objects.filter(name__icontains="test").first()
            
        if not template_config:
            template_config = CertificateTemplate.objects.first() or CertificateTemplate()

        # QR kodni Base64-ga o'tkazish
        qr_base64_str = ""
        if hasattr(self, '_qr_bytes') and self._qr_bytes:
            qr_base64_str = base64.b64encode(self._qr_bytes).decode('utf-8')
        elif self.qr_code_image:
            try:
                self.qr_code_image.open('rb')
                qr_base64_str = base64.b64encode(self.qr_code_image.read()).decode('utf-8')
                self.qr_code_image.close()
            except Exception:
                qr_base64_str = ""

        # Rasmlarni xavfsiz o'giriuvchi ichki funksiya
        def get_base64_image(image_field):
            if image_field:
                try:
                    image_field.open('rb')
                    b64_str = base64.b64encode(image_field.read()).decode('utf-8')
                    image_field.close()
                    return b64_str
                except Exception:
                    return ""
            return ""

        logo_base64 = get_base64_image(template_config.logo_image) if hasattr(template_config, 'logo_image') else ""
        signature_base64 = get_base64_image(template_config.mentor_signature) if hasattr(template_config, 'mentor_signature') else ""
        illustration_base64 = get_base64_image(template_config.illustration_image) if hasattr(template_config, 'illustration_image') else ""

        context_data = {
            "full_name": full_name,
            "title": title,
            "date": (self.issued_at or timezone.now()).strftime("%Y-yil, %d-%B"), 
            "code": self.certificate_code,
            "qr_base64": qr_base64_str,
            
            # Dinamik sozlamalar lug'ati (Modeldan xavfsiz o'qish):
            "organization_name": getattr(template_config, 'organization_name', "Platforma.uz"),
            "verify_domain": getattr(template_config, 'verify_domain', "platforma.uz"),
            "congratulation_text": getattr(template_config, 'congratulation_text', "Muvaffaqiyatli tamomlaganlik uchun berildi."),
            "mentor_name": getattr(template_config, 'mentor_name', "cfm"),
            "mentor_status": getattr(template_config, 'mentor_status', "Kurs Mentori"),
            
            # Base64 matnlari
            "logo_base64": logo_base64,
            "signature_base64": signature_base64,
            "illustration_base64": illustration_base64,
        }

        rendered_html = render_to_string('certificates/cert_template.html', context_data)

        pdf_buffer = io.BytesIO()
        HTML(string=rendered_html).write_pdf(pdf_buffer)

        filename = f"cert-{self.certificate_code}.pdf"
        self.pdf_file.save(filename, ContentFile(pdf_buffer.getvalue()), save=False)
