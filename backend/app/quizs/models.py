import io
import uuid
import qrcode
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.template import Template, Context
from django.db.models import Max
from weasyprint import HTML

from baseuser.models import BaseUser
from courses.models import Course, Lesson
from problems.models import Problem


# ─────────────────────────────────────────────
#  1. REYTING VA UNVON TIZIMI
# ─────────────────────────────────────────────
class UserRank(models.Model):
    """Talabalarning umumiy reyting ballari va unvonlarini saqlash modeli"""
    RANKS = [
        ('beginner', 'Yangi boshlovchi'),
        ('bronze', 'Bronza'),
        ('silver', 'Kumush'),
        ('gold', 'Oltin'),
        ('pro', 'Professional')
    ]
    
    user = models.OneToOneField(BaseUser, on_delete=models.CASCADE, related_name="rank_profile")
    total_xp = models.PositiveIntegerField("Jami to'plangan XP", default=0, db_index=True)
    level = models.CharField("Unvon (Daraja)", max_length=20, choices=RANKS, default='beginner')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "🏅 Foydalanuvchi Reytingi"
        verbose_name_plural = "🏅 Foydalanuvchilar Reytingi"
        ordering = ["-total_xp"]

    def update_level(self):
        """Xotirada tezkor tekshirib, darajani avtomatik yangilash"""
        if self.total_xp >= 5000:
            self.level = 'pro'
        elif self.total_xp >= 2500:
            self.level = 'gold'
        elif self.total_xp >= 1000:
            self.level = 'silver'
        elif self.total_xp >= 300:
            self.level = 'bronze'
        else:
            self.level = 'beginner'
        self.save(update_fields=['level', 'updated_at'])

    def __str__(self):
        return f"{self.user.username} — {self.total_xp} XP ({self.get_level_display()})"


# ─────────────────────────────────────────────
#  2. TEST MODEL (Mustaqil va Kurs ichidagi Testlar)
# ─────────────────────────────────────────────
class Test(models.Model):
    """Imtihonlar va darslik ichidagi testlarni boshqaruvchi asosiy model"""
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        related_name="tests",
        blank=True,
        null=True,
        help_text="Agar bo'sh qolsa, bu mustaqil umumiy imtihon testi hisoblanadi."
    )
    title = models.CharField("Test nomi", max_length=255)
    duration_minutes = models.PositiveIntegerField("Davomiyligi (daqiqa)", default=60)
    question_count = models.PositiveIntegerField("Savollar soni", default=20)
    min_pass_percentage = models.PositiveIntegerField(
        "O'tish foizi", 
        default=60, 
        validators=[MaxValueValidator(100)]
    )
    randomize_questions = models.BooleanField("Savollarni aralashtirish", default=False)
    max_attempts = models.PositiveIntegerField("Maksimal urinishlar soni (0 = cheksiz)", default=0)
    access_code = models.CharField("Kirish kodi (bo'sh = ochiq)", max_length=50, blank=True, null=True)
    is_active = models.BooleanField("Faol", default=True, db_index=True)
    deadline = models.DateTimeField("Testning tugash muddati")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_available(self):
        """Test topshirish muddati o'tmaganligini aniqlash"""
        return self.is_active and self.deadline > timezone.now()

    class Meta:
        verbose_name = "📝 Test"
        verbose_name_plural = "📑 Testlar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Test — {self.title}"


# ─────────────────────────────────────────────
#  3. SAVOL VA VARIANTLAR MODELLARI
# ─────────────────────────────────────────────
class Question(models.Model):
    """Polimorfik savollar: Ham Test, ham Problemga xizmat qila oladi"""
    DIFFICULTIES = [('easy', 'Oson'), ('medium', "O'rtacha"), ('hard', 'Qiyin')]

    problem = models.ForeignKey(Problem, on_delete=models.SET_NULL, related_name="questions", null=True, blank=True)
    test = models.ForeignKey(Test, on_delete=models.SET_NULL, related_name="questions", null=True, blank=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTIES, default='easy')
    xp = models.PositiveIntegerField(
        default=10, 
        validators=[MinValueValidator(10), MaxValueValidator(100)]
    )
    text = models.TextField("Savol matni")
    image = models.ImageField("Rasm", upload_to="questions/", blank=True, null=True)
    order = models.PositiveIntegerField("Tartib raqami", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Biznes mantiq xavfsizligi validationi"""
        if not self.problem and not self.test:
            raise ValidationError("Savol kamida bitta joyga (Problem yoki Test) bog'lanishi shart!")
        if self.problem and self.test:
            raise ValidationError("Savol bir vaqtning o'zida ham Problemga, ham Testga bog'lana olmaydi!")

    def save(self, *args, **kwargs):
        self.clean()
        if not self.xp or self.xp == 0:
            xp_map = {'easy': 10, 'medium': 25, 'hard': 50}
            self.xp = xp_map.get(self.difficulty, 10)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "❓ Savol"
        verbose_name_plural = "❔ Savollar"
        ordering = ["order", "created_at"]

    def __str__(self):
        return self.text[:50]


class Choice(models.Model):
    """Savol javoblari variantlari"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField("Javob matni", max_length=500)
    is_correct = models.BooleanField("To'g'ri javob", default=False, db_index=True)
    explanation = models.TextField("Javob izohi / Tushuntirish", blank=True, null=True)
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "🔘 Javob varianti"
        verbose_name_plural = "✅ Javob variantlari"
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:50]


# ─────────────────────────────────────────────
#  4. SERTIFIKAT DIZAYN SHABLONI
# ─────────────────────────────────────────────
class CertificateTemplate(models.Model):
    """Kurslar yoki Yirik Mustaqil imtihonlar uchun yagona dizayn shabloni"""
    name = models.CharField("Shablon nomi", max_length=255)
    html_content = models.TextField(
        "HTML Shabloni", 
        help_text="Dinamik taglar: {{ full_name }}, {{ title }}, {{ date }}, {{ code }}, {{ qr_code_url }}"
    )
    min_percentage = models.PositiveIntegerField("Minimal o'tish foizi", default=80)
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name="certificate_template", null=True, blank=True)
    test = models.OneToOneField(Test, on_delete=models.CASCADE, related_name="certificate_template", null=True, blank=True)

    def clean(self):
        if not self.course and not self.test:
            raise ValidationError("Shablon Kurs yoki Testga bog'lanishi shart!")
        if self.course and self.test:
            raise ValidationError("Shablon bir vaqtda ikkala manbaga bog'lana olmaydi!")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "📜 Sertifikat Shabloni"
        verbose_name_plural = "📜 Sertifikat Shablonlari"

    def __str__(self):
        source = f"Kurs: {self.course.title}" if self.course else f"Test: {self.test.title}"
        return f"{self.name} ({source})"


# ─────────────────────────────────────────────
#  5. TEST SESSION (Talaba Imtihon Jarayoni)
# ─────────────────────────────────────────────
class TestSession(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED   = "completed",   "Yakunlangan"
        EXPIRED     = "expired",     "Muddati o'tgan"

    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name="test_sessions")
    test = models.ForeignKey(Test, on_delete=models.SET_NULL, related_name="sessions", null=True, blank=True)
    problem = models.ForeignKey(Problem, on_delete=models.SET_NULL, related_name="test_sessions", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)
    
    score = models.PositiveIntegerField("To'g'ri javoblar", default=0)
    total_questions = models.PositiveIntegerField("Jami savollar", default=0)
    percentage = models.DecimalField("Foiz", max_digits=5, decimal_places=2, default=0.00)
    total_xp_earned = models.PositiveIntegerField("To'plangan XP", default=0)
    
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField("Tugash vaqti", null=True, blank=True)
    finish = models.DateTimeField("Tugatgan vaqti", null=True, blank=True)
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def calculate_results(self):
        """Natijalarni jamlash va statusni yangilash (Signalni trigger qiladi)"""
        answers = self.answers.select_related('question', 'choice').all()
        correct_count = answers.filter(choice__is_correct=True).count()
        total_xp = sum(a.question.xp for a in answers if a.choice.is_correct)
        total_q = self.test.questions.count() if self.test else self.problem.questions.count()
        
        self.score = correct_count
        self.total_xp_earned = total_xp
        self.total_questions = total_q
        if total_q > 0:
            self.percentage = (correct_count / total_q) * 100
        
        self.status = self.Status.COMPLETED
        self.finish = timezone.now()
        self.save() # Saqlash orqali post_save signal ishga tushadi
    class Meta:
        verbose_name = "⏱️ Test Sessiyasi"
        verbose_name_plural = "⏱️ Test Sessiyalari"
        ordering = ["-started_at"]
    def str(self):
        target = self.test.title if self.test else f"Problem #{self.problem_id}"
        return f"{self.user.username} — {target} ({self.status})"
    
class UserAnswer(models.Model):
    """Talabaning test davomida belgilagan har bir javobi logs"""
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "👤 Talaba Javobi"
        verbose_name_plural = "👤 Talaba Javoblari"
        unique_together = ("session", "question")


# ─────────────────────────────────────────────
#  6. HAQIQIY BERILGAN SERTIFIKATLAR MODELI (XATOSIZ)
# ─────────────────────────────────────────────
class Certificate(models.Model):
    """Unikal QR-kod va WeasyPrint PDF generatsiyasiga ega, siklsiz (Safe) model"""
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name="certificates")
    template = models.ForeignKey(CertificateTemplate, on_delete=models.PROTECT)
    test_session = models.OneToOneField(TestSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_test_certificate")
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_course_certificates")
    
    certificate_code = models.CharField("Sertifikat ID/Kodi", max_length=100, unique=True, blank=True)
    qr_code_image = models.ImageField("QR Kod", upload_to="certificates/qrcodes/", blank=True, null=True)
    pdf_file = models.FileField("PDF Fayl", upload_to="certificates/pdfs/", blank=True, null=True)
    issued_at = models.DateTimeField("Berilgan vaqti", auto_now_add=True)

    def clean(self):
        if not self.test_session and not self.course: 
            raise ValidationError("Manba (Test sessiyasi yoki Kurs) ko'rsatilishi shart!")
        if self.test_session and self.course: 
            raise ValidationError("Sertifikat bir vaqtda ham Test, ham Kurs uchun bo'la olmaydi!")

    def save(self, *args, **kwargs):
        self.clean()
        if not self.certificate_code:
            self.certificate_code = f"CERT-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
        
        # 🌟 QADAM 1: Obyektni bazada saqlash (ID olish va fayl tizimini tayyorlash uchun)
        is_created = self.pk is None
        super().save(*args, **kwargs)

        # 🌟 QADAM 2: QR va PDF ni xavfsiz, cheksiz sikl vujudga keltirmasdan generatsiya qilish
        if is_created or not self.qr_code_image or not self.pdf_file:
            is_updated = False
            
            if not self.qr_code_image:
                self.generate_qr_code()
                is_updated = True
            
            if not self.pdf_file:
                self.generate_pdf_file()
                is_updated = True

            # Faqatgina fayl fieldlarini qayta yangilaymiz (save=False tufayli sikl bo'lmaydi)
            if is_updated:
                super().save(update_fields=['qr_code_image', 'pdf_file'])

    def generate_qr_code(self):
        """Dinamik settings.SITE_URL orqali istalgan server muhitida ishlaydigan QR-kod"""
        verify_url = f"{settings.SITE_URL}/certificates/verify/{self.certificate_code}/"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(verify_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        
        # 🔥 save=False cheksiz siklni (Maximum recursion depth) butunlay yo'qotadi!
        self.qr_code_image.save(f"qr-{self.certificate_code}.png", ContentFile(buffer.getvalue()), save=False)

    def generate_pdf_file(self):
        """HTML/CSS shablon va unikal QR-kodni birlashtirib, professional PDF yaratish"""
        full_name = f"{self.user.first_name} {self.user.last_name}" if self.user.first_name else self.user.username
        title = self.course.title if self.course else self.test_session.test.title
        
        # WeasyPrint rasmni o'qishi uchun mutlaq (Absolute) URL manzil
        qr_absolute_url = f"{settings.SITE_URL}{self.qr_code_image.url}" if self.qr_code_image else ""

        context_data = {
            "full_name": full_name,
            "title": title,
            "date": self.issued_at.strftime("%d.%m.%Y") if self.issued_at else timezone.now().strftime("%d.%m.%Y"),
            "code": self.certificate_code,
            "qr_code_url": qr_absolute_url
        }
        
        django_template = Template(self.template.html_content)
        rendered_html = django_template.render(Context(context_data))
        
        pdf_buffer = io.BytesIO()
        HTML(string=rendered_html).write_pdf(pdf_buffer)
        
        # 🔥 save=False cheksiz siklni (Maximum recursion depth) butunlay yo'qotadi!
        self.pdf_file.save(f"certificate-{self.certificate_code}.pdf", ContentFile(pdf_buffer.getvalue()), save=False)

    class Meta:
        verbose_name = "📜 Berilgan Sertifikat"
        verbose_name_plural = "📜 Berilgan Sertifikatlar"
        unique_together = [("user", "course"), ("user", "test_session")]

    def __str__(self):
        return f"{self.user.username if self.user.username else self.user.telegram_id} — {self.certificate_code}"
