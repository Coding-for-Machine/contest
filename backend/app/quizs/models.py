import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from video.models import Video
from baseuser.models import BaseUser
from mdeditor.fields import MDTextField
from centers.models import CenterScopedMixin

class TestEnrollment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name="test_enrollments")
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name="enrollments")
    
    # To'lov ma'lumotlari bitta jadval ichida
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "🛒 Sotib olingan test"
        verbose_name_plural = "🛒 Sotib olingan testlar"
        unique_together = ('user', 'test') 
        indexes = [
            models.Index(fields=["user", "test"]), # Ruxsatni ultra-tezkor tekshirish uchun kompozit indeks
        ]

    def __str__(self):
        return f"{self.user.username if self.user.username else self.user.telegram_id} -> {self.test.title}"


class TestSession(models.Model):
    """Foydalanuvchining test topshirish seansi, statistikasi va geymifikatsiya hisoblagichi."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED = "completed", "Yakunlangan"
        EXPIRED = "expired", "Muddati o'tgan"

    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        verbose_name="Seans ID",
        help_text="Har bir test topshirish seansi uchun unikal UUID identifikator."
    )
    user = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE, 
        related_name="test_sessions",
        verbose_name="Foydalanuvchi",
        help_text="Testni topshirayotgan (tizimda faol bo'lgan) talaba."
    )
    test = models.ForeignKey(
        'Test', 
        on_delete=models.CASCADE, 
        related_name="sessions",
        verbose_name="Test (Imtihon)",
        help_text="Topshirilayotgan test yoki imtihon majmuasi."
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.IN_PROGRESS,
        db_index=True,
        verbose_name="Seans holati",
        help_text="Test jarayonining joriy holati: jarayonda, yakunlangan yoki vaqti o'tib ketgan (muddati o'tgan)."
    )
    score = models.FloatField(
        default=0.0,
        verbose_name="Yakuniy akademik ball (S)",
        help_text="S = Sum(C*P) - Sum(W*P*K) formulasi bo'yicha jarima koeffitsiyentini hisobga olgan holda aniqlangan sof ball."
    )
    correct_count = models.PositiveIntegerField(
        default=0,
        verbose_name="To'g'ri javoblar soni",
        help_text="Talaba tomonidan ushbu seansda to'g'ri belgilangan savollarning umumiy miqdori."
    )
    wrong_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Noto'g'ri javoblar soni",
        help_text="Talaba xato belgilagan yoki noto'g'ri topshirgan savollar soni."
    )
    unanswered_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Javobsiz qoldirilganlar soni",
        help_text="Talaba tomonidan belgilamasdan o'tkazib yuborilgan yoki vaqt yetmay umuman ochilmagan savollar soni."
    )
    total_xp_earned = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name="Yutilgan XP ball",
        help_text="Ushbu urinish natijasida foydalanuvchining global profiliga qo'shish uchun hisoblangan butun sonli mukofot balli."
    )
    lifelines_used = models.PositiveIntegerField(
        "Ishlatilgan Reler (Lifeline) soni",
        default=0,
        help_text="Ushbu seansda foydalanuvchi hozirgacha ishlatgan lifeline'lar soni "
                  "(faqat serverda hisoblanadi, frontend hisoblagichiga ishonilmaydi)."
    )
    selected_question_ids = models.JSONField(
        default=list, 
        blank=True,
        verbose_name="Tanlangan savollar IDlari",
        help_text="Agar random savollar ishlatilgan bo'lsa, shu seansda qaysi savollar berilgani."
    )
    started_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Boshlangan vaqti",
        help_text="Foydalanuvchi testni yechishni boshlagan aniq sana va vaqt."
    )
    completed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Yakunlangan vaqti",
        help_text="Test yakunlangan yoki vaqt tugashi sababli tizim tomonidan yopilgan aniq vaqt."
    )

    class Meta:
        verbose_name = "⏱ Test Seansi"
        verbose_name_plural = "⏱ Test Seanslari"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "test", "status"]),
            models.Index(fields=["status", "-started_at"]),
        ]

    def __str__(self):
        username = self.user.username if self.user.username else f"User-{self.user.telegram_id}"
        return f"{username} - {self.test.title})"

    def calculate_percentage(self):
        """Yig'ilgan ballni testning jami mumkin bo'lgan XP balliga nisbatan foizini hisoblaydi."""
        total_possible = self.test.total_possible_xp
        if total_possible <= 0:
            return 0.0
        return max(0.0, (self.score / total_possible) * 100)

    def calculate_mathematical_score(self):
        from status.models import UserStats

        with transaction.atomic():
            session = TestSession.objects.select_for_update().get(pk=self.pk)
            if session.status == session.Status.COMPLETED:
                return session.score

            penalty_k = session.test.penalty_coefficient
            correct_count = wrong_count = 0
            total_score = 0.0

            test_question_ids = session.test.questions.values_list('id', flat=True)
            user_responses = UserResponse.objects.filter(
                session_id=session.id, question_id__in=test_question_ids
            ).select_related("question", "choice")

            answered_ids = set()
            for r in user_responses:
                answered_ids.add(r.question_id)
                if r.choice is None:
                    continue
                if r.choice.is_correct:
                    correct_count += 1
                    total_score += r.question.xp
                else:
                    wrong_count += 1
                    total_score -= r.question.xp * penalty_k

            unanswered_count = len(test_question_ids) - len(answered_ids)
            rounded_score = round(total_score, 2)
            new_xp_earned = max(0, int(rounded_score))

            previous_best = TestSession.objects.filter(
                user=session.user, test=session.test, status=session.Status.COMPLETED
            ).order_by('-total_xp_earned').first()

            xp_to_add = new_xp_earned if not previous_best else max(0, new_xp_earned - previous_best.total_xp_earned)

            if xp_to_add > 0:
                UserStats.add_xp(user=session.user, xp_amount=xp_to_add)

            session.score = rounded_score
            session.correct_count = correct_count
            session.wrong_count = wrong_count
            session.unanswered_count = unanswered_count
            session.total_xp_earned = new_xp_earned
            session.status = session.Status.COMPLETED
            session.completed_at = timezone.now()
            session.save(update_fields=[
                "score", "correct_count", "wrong_count", "unanswered_count",
                "total_xp_earned", "status", "completed_at"
            ])

        return session.score

class Test(CenterScopedMixin, models.Model):
    """Imtihonlar va bob (Modul) yakunidagi testlarni boshqaruvchi asosiy model."""

    modul = models.ForeignKey(
        "courses.Modul",
        on_delete=models.SET_NULL,
        related_name="tests",
        blank=True,
        null=True,
        verbose_name="Bob (Modul)",
        help_text="Agar bo'sh qolsa, bu mustaqil umumiy imtihon testi hisoblanadi. Aks holda, bu bob (modul) yakunidagi test.",
    )
    title = models.CharField(
        "Test nomi", 
        max_length=255,
        help_text="Test yoki imtihon majmuasining to'liq sarlavhasi."
    )
    slug = models.SlugField(
        "Slug",
        max_length=255,
        unique=True,
        help_text="URL manzillari uchun avtomatik hosil bo'luvchi qisqa nom."
    )
    description = MDTextField(
        null=True,
        verbose_name="test sharti (Matn)", 
        help_text="Markdown formatida masalaning to'liq shartini yozing."
    )
    duration_minutes = models.PositiveIntegerField(
        "Davomiyligi (daqiqa)", 
        default=60,
        help_text="Testni yechish uchun foydalanuvchiga beriladigan umumiy vaqt (daqiqa hisobida)."
    )
    question_count = models.PositiveIntegerField(
        "Bazasidagi jami savollar soni", 
        default=0,
        help_text="Ushbu test tarkibiga qo'shilgan jami umumiy savollar soni (avtomatik yoki qo'lda yangilanadi)."
    )
    random_questions_count = models.PositiveIntegerField(
        "Foydalanuvchiga ko'rsatiladigan tasodifiy savollar soni", 
        default=0,
        help_text="0 = barcha savollar ko'rsatiladi. Agar masalan bazada 100 ta savol bo'lsa va bu yerga 20 yozilsa, foydalanuvchiga random 20 ta savol ajratib beriladi."
    )
    min_pass_percentage = models.PositiveIntegerField(
        "O'tish foizi", 
        default=60, 
        validators=[MaxValueValidator(100)],
        help_text="Testdan muvaffaqiyatli o'tish uchun talaba to'plashi kerak bo'lgan eng kam foiz ko'rsatkichi (0-100)."
    )
    max_attempts = models.PositiveIntegerField(
        "Maksimal urinishlar soni", 
        default=0,
        help_text="Foydalanuvchi ushbu testni ko'pi bilan necha marta topshira olishi. 0 = cheksiz urinishlar."
    )
    access_code = models.CharField(
        "Kirish kodi", 
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Testni boshlash uchun maxsus parol (bo'sh qoldirilsa = hamma uchun ochiq)."
    )
    is_active = models.BooleanField(
        "Faol", 
        default=True, 
        db_index=True,
        help_text="Test talabalarga ko'rinishi yoki vaqtincha yashirib qo'yilishi uchun boshqaruv belgisi."
    )
    start_time = models.DateTimeField(
        "Boshlanish vaqti",
        help_text="Test tizimda faollashadigan va talabalar kirishi boshlanadigan aniq sana va vaqt."
    )
    end_time = models.DateTimeField(
        "Tugash vaqti",
        help_text="Test butunlay yopiladigan muddat. Ushbu vaqtdan keyin talabalar testga kira olishmaydi."
    )
    price = models.DecimalField(
        "Test narxi", 
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Agar test pullik bo'lsa, uning asosiy qiymati (bepul bo'lsa 0.00 qoldiring)."
    )
    discount_price = models.DecimalField(
        "Chegirmadagi narx", 
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Aksiya va chegirmalar vaqtida amal qiladigan arzonlashtirilgan narx."
    )
    penalty_coefficient = models.FloatField(
        "Jarima koeffitsiyenti (K)", 
        default=0.33,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Noto'g'ri javoblar uchun jarima koeffitsiyenti. Masalan: 0.33 yozilsa, 3 ta xato javob 1 ta to'g'ri javob ballini olib ketadi."
    )
    max_lifelines = models.PositiveIntegerField(
        "Maksimal Reler (Lifeline) soni", 
        default=3,
        help_text="Talaba test davomida foydalanishi mumkin bo'lgan yordam vositalari (Lifeline) soni."
    )
    intro_video = models.ForeignKey(
        Video, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="test_video", 
        verbose_name="Kirish yoki qoidalar videosi",
        help_text="Testni boshlashdan oldin ko'rsatiladigan yo'riqnoma yoki tushuntirish videosi."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tests',
        verbose_name="Yaratuvchi o'qituvchi",
        help_text="Ushbu test majmuasini yaratgan va unga egalik qiluvchi o'qituvchi/admin."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")
    
    class Meta:
        verbose_name = "📋 Test"
        verbose_name_plural = "📋 Testlar"
        ordering = ["-id", "created_at"]
        
    def __str__(self):
        return f"Test — {self.title}"

    @property
    def is_available(self):
        """Test ayni vaqtda topshirish uchun ochiqligini tekshiradi."""
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    @property
    def total_possible_xp(self):
        """Test tarkibidagi barcha savollarning jami maksimal ballarini hisoblab beradi (Circular importlarsiz)."""
        return sum(self.questions.values_list('xp', flat=True))

class Question(models.Model):
    """Polimorfik savollar: Ham ``Test``, ham ``Lesson``ga (Darsga) xizmat qila oladi."""

    class Difficulty(models.TextChoices):
        EASY = "easy", "Oson"
        MEDIUM = "medium", "O'rtacha"
        HARD = "hard", "Qiyin"

    DEFAULT_XP_BY_DIFFICULTY = {
        Difficulty.EASY: 3,
        Difficulty.MEDIUM: 6,
        Difficulty.HARD: 10,
    }

    lesson = models.ForeignKey(
        "courses.Lesson", 
        on_delete=models.SET_NULL, 
        related_name="quiz_questions", 
        null=True, 
        blank=True,
        verbose_name="Darslik",
        help_text="Agar ushbu savol muayyan dars ichidagi amaliyot uchun bo'lsa, darsni tanlang."
    )
    test = models.ForeignKey(
        Test, 
        on_delete=models.SET_NULL, 
        related_name="questions", 
        null=True, 
        blank=True,
        verbose_name="Test (Imtihon)",
        help_text="Agar ushbu savol biror imtihon yoki modul yakuniy testi tarkibiga kirsa, testni tanlang."
    )
    difficulty = models.CharField(
        max_length=10, 
        choices=Difficulty.choices, 
        default=Difficulty.EASY,
        verbose_name="Qiyinchilik darajasi",
        help_text="Savolning murakkablik darajasi. Darajaga qarab avtomatik XP ballari belgilanadi."
    )
    explanation_video = models.ForeignKey(
        Video, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="question_explanations",
        verbose_name="Savol video tahlili",
        help_text="Talaba xato qilganda javobni tushunishi va tahlilini ko'rishi uchun biriktiriladigan video darslik."
    )
    text = MDTextField(
        verbose_name="Savol matni",
        help_text="Markdown formatida savol matnini va shartini to'liq yozing."
    )
    order = models.PositiveIntegerField(
        default=0, 
        verbose_name="Tartib raqami",
        help_text="Savollarning test sahifasida qaysi ketma-ketlikda chiqishini tartiblovchi raqam.",
        db_index=True,
    )
    xp = models.PositiveIntegerField(
        verbose_name="XP mukofoti",
        help_text="Ushbu savol to'g'ri topilganda foydalanuvchiga beriladigan ball miqdori (5 dan 20 gacha).",
        default=5, 
        validators=[MinValueValidator(5), MaxValueValidator(20)]
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_questions',
        verbose_name="Yaratuvchi o'qituvchi",
        help_text="Ushbu savolni tizimga qo'shgan mas'ul xodim yoki o'qituvchi."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    class Meta:
        verbose_name = "❓ Savol"
        verbose_name_plural = "❔ Savollar"
        ordering = ["order", "created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(lesson__isnull=False, test__isnull=True)
                    | models.Q(lesson__isnull=True, test__isnull=False)
                ),
                name="question_belongs_to_lesson_xor_test",
            )
        ]
    def __str__(self):
        # Markdown belgilari toza chiqishi uchun qisqartirib ko'rsatish
        return f"Savol #{self.id}: {self.text[:40]}..."

    def clean(self):
        super().clean()
        
        # 1. Ikkalasi ham bo'sh bo'lsa xatolik
        if not self.lesson and not self.test:
            raise ValidationError(
                "Savol kamida bitta joyga (Dars yoki Test) bog'lanishi shart!"
            )
            
        # 2. Ikkalasi ham tanlangan bo'lsa xatolik
        if self.lesson and self.test:
            raise ValidationError(
                "Savol bir vaqtning o'zida ham Darsga, ham Testga bog'lana olmaydi! Faqat bittasini tanlang."
            )

    def save(self, *args, **kwargs):
        # Agar XP qo'lda kiritilmagan bo'lsa, qiyinchilik darajasidan kelib chiqib avtomat belgilash
        if not self.xp or self.xp == 3:  # default 3 bo'lgani uchun tekshiriladi
            self.xp = self.DEFAULT_XP_BY_DIFFICULTY.get(self.difficulty, 3)
        super().save(*args, **kwargs)

class Choice(models.Model):
    """Savol javoblari variantlari (Choice)."""

    question = models.ForeignKey(
        "Question", 
        on_delete=models.CASCADE, 
        related_name="choices",
        verbose_name="Tegishli savol",
        help_text="Ushbu variant qaysi savolga tegishli ekanligini belgilang."
    )
    text = MDTextField(
        verbose_name="Variant matni",  # ✅ TUZATISH: "Savol matni" -> "Variant matni" ga o'zgartirildi
        help_text="Markdown formatida javob variantining matnini kiriting."
    )
    is_correct = models.BooleanField(
        "To'g'ri javob", 
        default=False, 
        db_index=True,
        help_text="Agar ushbu variant savolning to'g'ri javobi bo'lsa, belgilang."
    )
    explanation = MDTextField(
        verbose_name="Javob izohi / Tushuntirish", 
        blank=True, 
        null=True,
        help_text="Talaba ushbu variantni tanlaganidan keyin (yoki test yakunida) nega bu javob to'g'ri/noto'g'ri ekanligini tushuntiruvchi matn."
    )
    order = models.PositiveIntegerField(
        "Tartib raqami", 
        default=0,
        help_text="Javob variantlarining foydalanuvchiga qaysi ketma-ketlikda chiqishini belgilovchi raqam."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_choices',
        verbose_name="Yaratuvchi o'qituvchi",
        help_text="Ushbu variantni tizimga qo'shgan mas'ul xodim yoki o'qituvchi."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")
    
    class Meta:
        verbose_name = "🔘 Javob varianti"
        verbose_name_plural = "✅ Javob variantlari"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=['question'],
                condition=models.Q(is_correct=True),
                name='unique_correct_choice_per_question'
            ),
        ]

    def __str__(self):
        # Markdown belgilari xalaqit bermasligi uchun qisqartirib ko'rsatish
        status = "✅" if self.is_correct else "❌"
        return f"[{status}] {self.text[:40]}..."

    def clean(self):
        super().clean()
        
        if self.is_correct and self.question_id:
            qs = Choice.objects.filter(question=self.question, is_correct=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"is_correct": "Ushbu savolda allaqachon to'g'ri javob varianti mavjud! Bittadan ortiq to'g'ri javob belgilash mumkin emas."}
                )

class UserResponse(models.Model):
    """Talabaning har bir savolga bergan javobi (Ko'p marta javob berishga moslangan versiya)."""

    session = models.ForeignKey(
        "TestSession",
        on_delete=models.CASCADE,
        related_name="responses",
        null=True,
        blank=True,
        verbose_name="Test seansi",
        help_text="Ushbu javob aynan qaysi test topshirish urinishiga (seansiga) tegishli ekanligi."
    )
    user = models.ForeignKey(
        BaseUser, 
        on_delete=models.CASCADE, 
        related_name="quiz_responses",
        verbose_name="Foydalanuvchi",
        help_text="Javob bergan talaba."
    )
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name="user_responses",
        verbose_name="Savol",
        help_text="Javob berilgan test yoki darslik savoli."
    )
    choice = models.ForeignKey(
        Choice, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Tanlangan variant",
        help_text="Talaba tomonidan belgilangan javob varianti (bo'sh qolsa = javobsiz qoldirilgan)."
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Javob berilgan vaqt",
        help_text="Talaba joriy savolga javob tugmasini bosgan aniq vaqt."
    )

    class Meta:
        verbose_name = "🎯 Foydalanuvchi Javobi"
        verbose_name_plural = "🎯 Foydalanuvchi Javoblari"

    def __str__(self):
        status_text = "Javob berilgan" if self.choice else "Javobsiz qoldirilgan"
        username = self.user.username if self.user.username else f"User-{self.user.telegram_id}"
        return f"{username} -> Savol №{self.question_id} [{status_text}]"

    def clean(self):
        super().clean()
        
        if self.choice and self.choice.question_id != self.question_id:
            raise ValidationError(
                {"choice": "Siz buzib kirishga urindingiz! Tanlangan javob varianti ushbu savolga tegishli emas."}
            )