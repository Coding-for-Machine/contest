import uuid
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from mdeditor.fields import MDTextField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from centers.models import CenterScopedMixin
from baseuser.models import BaseUser
from video.models import Video


# ==========================================================
# YORDAMCHI: unikal slug generatsiyasi (DRY)
# ==========================================================

def generate_unique_slug(model_cls, title, **extra_filter):
    """
    Berilgan model uchun unikal slug hosil qiladi.
    extra_filter orqali scope (masalan, course=..., lesson=...) beriladi.
    """
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while model_cls.objects.filter(slug=slug, **extra_filter).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqti", auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class Course(CenterScopedMixin, TimeStampedModel):
    title = models.CharField(
        "Kurs nomi",
        max_length=200,
        help_text="Kursning aniq va qisqa nomini kiriting"
    )
    slug = models.SlugField(
        "Slug",
        unique=True,
        blank=True,
        help_text="Kurs URL uchun avtomatik hosil qilinadi"
    )
    description = MDTextField(
        "Tavsif",
        help_text="Kurs haqida batafsil ma’lumot kiriting"
    )
    is_active = models.BooleanField(default=False)

    # NARX QISMI
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

    intro_video = models.ForeignKey(
        'video.Video', on_delete=models.SET_NULL, null=True, blank=True,
        related_name="intro_courses", verbose_name="Kirish yoki qoidalar videosi",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses',
    )
    level = models.CharField(
        max_length=20,
        choices=[('beginner', "Boshlang'ich"), ('intermediate', "O'rta"), ('advanced', "Yuqori")],
        default='beginner'
    )
    total_modules_count = models.PositiveSmallIntegerField(default=0, editable=False)
    total_lessons_count = models.PositiveSmallIntegerField(default=0, verbose_name="Jami darslar soni")
    total_test_count = models.PositiveSmallIntegerField(default=0, verbose_name="Jami test soni")

    class Meta:
        verbose_name = "✨ Kurs"
        verbose_name_plural = "✨ Kurslar"
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if self.discount_price is not None and self.discount_price >= self.price:
            raise ValidationError({
                "discount_price": "Chegirma narxi asosiy narxdan kichik bo'lishi kerak."
            })
        if self.price is not None and self.price < 0:
            raise ValidationError({"price": "Narx manfiy bo'lishi mumkin emas."})

    @property
    def current_price(self):
        if self.discount_price is not None and self.discount_price < self.price:
            return self.discount_price
        return self.price

    def __str__(self):
        return f"{self.title} - {self.current_price} UZS"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Course, self.title)
        super().save(*args, **kwargs)


class Modul(TimeStampedModel):
    course = models.ForeignKey(
        Course,
        related_name='modullar',
        on_delete=models.CASCADE,
        verbose_name="Kurs",
        help_text="Modul qaysi kursga tegishli ekanligini tanlang"
    )
    title = models.CharField(
        "Modul nomi",
        max_length=200,
        help_text="Modulning qisqa nomi"
    )
    slug = models.SlugField(
        "Slug",
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Modul URL uchun (ixtiyoriy, avtomatik hosil bo'ladi)"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Tartib raqami"),
        help_text=_("Ushbu blok dars interfeysida qaysi ketma-ketlikda chiqishini tartiblovchi raqam.")
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Faol"),
        help_text=_("Agar false bo'lsa, bu modul foydalanuvchilarga ko'rinmaydi.")
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moduls',
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "📚 Kurs Bobi"
        verbose_name_plural = "📚 Kurs boblari"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"],
                name="unique_module_order_per_course",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.course.title})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Modul, self.title, course=self.course)
        super().save(*args, **kwargs)


class Lesson(TimeStampedModel):
    modul = models.ForeignKey(
        Modul,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name="Modul",
        help_text="Dars qaysi modulga tegishli"
    )
    title = models.CharField("Darslik nomi", max_length=100)
    slug = models.SlugField(
        "Slug",
        blank=True,
        db_index=True,
        help_text="URL uchun slug, avtomatik hosil qilinadi"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lessons',
    )
    order = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_("Tartib raqami"),
        help_text=_(
            "1 dan boshlanadigan natural son. "
            "Masalan: 1, 2, 3, 4..."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Faol"),
        help_text=_("Agar false bo'lsa, bu dars foydalanuvchilarga ko'rinmaydi.")
    )
    total_tasks_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Jami vazifalar soni",
        editable=False,
        help_text="Problem + Question(lesson) + Lecture sonlarining avtomatik yig'indisi."
    )
    estimated_minutes = models.PositiveSmallIntegerField(default=10, verbose_name="Taxminiy vaqt (daqiqa)")

    def __str__(self):
        return f"kurs-{self.modul.course.title[:20]}:modul-{self.modul.title[:15]}:dars-{self.title[:15]}"

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "📚 Darslik"
        verbose_name_plural = "📚 Darslik"
        constraints = [
            models.UniqueConstraint(
                fields=["modul", "order"],
                name="unique_lesson_order_per_module",
            ),
        ]

    async def get_previous(self):
        """Shu darsdan oldingi bitta darsni qaytaradi."""
        prev = await Lesson.objects.filter(
            modul=self.modul, order__lt=self.order, is_active=True
        ).order_by("-order").afirst()
        if prev:
            return prev
        prev_modul = await Modul.objects.filter(
            course=self.modul.course, order__lt=self.modul.order, is_active=True
        ).order_by("-order").afirst()
        if prev_modul:
            return await Lesson.objects.filter(
                modul=prev_modul, is_active=True
            ).order_by("-order").afirst()
        return None

    async def get_next(self):
        """Shu darsdan keyingi bitta darsni qaytaradi."""
        next_lesson = await Lesson.objects.filter(
            modul=self.modul, order__gt=self.order, is_active=True
        ).order_by("order").afirst()
        if next_lesson:
            return next_lesson
        next_modul = await Modul.objects.filter(
            course=self.modul.course, order__gt=self.modul.order, is_active=True
        ).order_by("order").afirst()
        if next_modul:
            return await Lesson.objects.filter(
                modul=next_modul, is_active=True
            ).order_by("order").afirst()
        return None

    def save(self, *args, **kwargs):
        if not self.slug:
            if self._state.adding and not self.order:
                last_order = (
                    Lesson.objects
                    .filter(modul=self.modul)
                    .aggregate(max_order=models.Max("order"))
                )["max_order"] or 0

                self.order = last_order + 1

            self.slug = generate_unique_slug(Lesson, self.title, modul=self.modul)
        super().save(*args, **kwargs)


class Enrollment(TimeStampedModel):
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    is_paid = models.BooleanField("To'langan", default=False)

    class Meta:
        unique_together = ('user', 'course')
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["course", "is_paid"]),
        ]
        verbose_name = "✨ Kursga yozilish"
        verbose_name_plural = "✨ Kursga yozilishlar"


class Lecture(TimeStampedModel):
    lesson = models.ForeignKey(
        'courses.Lesson',
        on_delete=models.CASCADE,
        related_name='lectures',
        verbose_name=_("Darslik"),
        help_text=_("Ushbu ma'ruza/video qaysi dars tarkibiga kirishini tanlang.")
    )

    video = models.ForeignKey(
        'video.Video',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lectures",
        verbose_name=_("Video darslik"),
        help_text=_("Agar ushbu mavzuda video darslik bo'lsa, tanlang. Bo'sh qolsa, faqat matnli ma'ruza bo'ladi.")
    )

    title = models.CharField(
        _("Mavzu sarlavhasi"),
        max_length=200,
        help_text=_("Mavzu nomi (masalan: 1.2. *args va **kwargs argumentlari)")
    )
    slug = models.SlugField(
        _("Slug"),
        max_length=255,
        blank=True,
        help_text=_("URL va frontend navigatsiyasi uchun avtomatik hosil qilinadi.")
    )
    body = MDTextField(
        verbose_name=_("Ma'ruza matni (Konspekt)"),
        blank=True,
        null=True,
        help_text=_("Markdown formatida ma'ruza matnini, qoidalarni va kod namunalarini yozing.")
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Tartib raqami"),
        help_text=_("Ushbu blok dars interfeysida qaysi ketma-ketlikda chiqishini tartiblovchi raqam.")
    )

    reading_time = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("O'qish vaqti (daqiqa)"),
        help_text=_("Faqat matnni o'qish uchun taxminiy vaqt.")
    )

    xp = models.PositiveIntegerField(
        verbose_name=_("XP mukofoti"),
        default=10,
        validators=[MinValueValidator(5), MaxValueValidator(20)],
        help_text=_(
            "Ushbu ma'ruza muvaffaqiyatli yakunlanganda (video ko'rilganda yoki "
            "konspekt o'qib bo'linganda) foydalanuvchiga beriladigan XP miqdori. "
            "Faqat birinchi marta yakunlaganda beriladi. Qiymat diapazoni: 5 dan 20 gacha."
        )
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lectures',
    )

    class Meta:
        verbose_name = _("📖 Ma'ruza va Video dars")
        verbose_name_plural = _("📖 Ma'ruzalar va Video darslar")
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=['lesson', 'order']),
            models.Index(fields=['slug']),
            models.Index(fields=['video']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "order"],
                name="unique_lecture_order_per_lesson",
            ),
        ]

    def __str__(self):
        type_prefix = "🎥 Video+Matn" if self.video and self.body else ("🎥 Faqat Video" if self.video else "📄 Faqat Matn")
        return f"[{type_prefix}] {self.lesson.title[:15]} -> {self.title[:25]}"

    def clean(self):
        if not self.video and not self.body:
            raise ValidationError(
                _("Ma'ruza bloki bo'sh bo'lishi mumkin emas! Kamida Video darslik yuklang yoki Matn kiriting.")
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Lecture, self.title, lesson=self.lesson)
        super().save(*args, **kwargs)


class CourseTestSession(models.Model):
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
        "CourseTest",
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="Test",
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
            models.Index(fields=["user", "test"]),
            models.Index(fields=["-started_at"]),
            # calculate_mathematical_score() dagi "eng yaxshi urinish"
            # (user, test bo'yicha eng katta total_xp_earned) so'rovini
            # to'liq qamrab oladigan composite indeks.
            models.Index(fields=["user", "test", "-total_xp_earned"], name="test_session_best_lookup"),
        ]

    def __str__(self):
        username = self.user.username if self.user.username else f"User-{self.user.telegram_id}"
        return f"{username} - {self.test.title})"

    def calculate_mathematical_score(self):
        """
        Seansdagi barcha javoblarni (MULTIPLE_CHOICE, MATCHING, ARRANGE_WORDS,
        FILL_BLANKS) tekshiradi, ball hisoblaydi va XP beradi.
        Har bir savol turi CourseUserResponse.check_and_score() orqali
        o'zini tekshiradi — bu yerda faqat yig'indi hisoblanadi.
        """
        from status.models import UserStats

        with transaction.atomic():
            session = (
                CourseTestSession.objects
                .select_for_update()
                .select_related("test", "user")
                .get(pk=self.pk)
            )

            if session.completed_at is not None:
                return session.total_xp_earned

            penalty_k = session.test.penalty_coefficient

            correct_count = 0
            wrong_count = 0
            total_score = 0.0

            test_questions = list(session.test.questions.all())
            test_question_ids = [q.id for q in test_questions]

            user_responses = (
                CourseUserResponse.objects
                .filter(
                    session=session,
                    question_id__in=test_question_ids,
                )
                .select_related("question", "choice")
                .prefetch_related(
                    "question__matching_pairs",
                    "question__arrange_items",
                    # Chuqurroq prefetch: Blank.is_correct_answer() endi
                    # .answers.all() orqali shu keshdan foydalanadi va
                    # javob boshiga alohida so'rov yubormaydi.
                    "question__blanks__answers",
                )
            )

            responses_by_question = {r.question_id: r for r in user_responses}
            answered_ids = set()

            for question in test_questions:
                response = responses_by_question.get(question.id)
                if response is None:
                    continue

                is_answered, is_correct = response.check_and_score()
                if not is_answered:
                    continue

                answered_ids.add(question.id)

                if is_correct:
                    correct_count += 1
                    total_score += question.xp
                else:
                    wrong_count += 1
                    total_score -= question.xp * penalty_k

            unanswered_count = len(test_question_ids) - len(answered_ids)

            rounded_score = round(total_score, 2)
            new_xp_earned = max(0, int(rounded_score))

            previous_best = (
                CourseTestSession.objects
                .filter(
                    user=session.user,
                    test=session.test,
                    completed_at__isnull=False,
                )
                .exclude(pk=session.pk)
                .order_by("-total_xp_earned")
                .first()
            )

            xp_to_add = (
                new_xp_earned
                if not previous_best
                else max(0, new_xp_earned - previous_best.total_xp_earned)
            )

            if xp_to_add > 0:
                UserStats.add_xp(
                    user=session.user,
                    xp_amount=xp_to_add,
                )

            session.correct_count = correct_count
            session.wrong_count = wrong_count
            session.unanswered_count = unanswered_count
            session.total_xp_earned = new_xp_earned
            session.completed_at = timezone.now()

            session.save(
                update_fields=[
                    "correct_count",
                    "wrong_count",
                    "unanswered_count",
                    "total_xp_earned",
                    "completed_at",
                ]
            )

            return rounded_score


class CourseTest(TimeStampedModel):
    """Imtihonlar va bob (Modul) yakunidagi testlarni boshqaruvchi asosiy model."""

    modul = models.OneToOneField(
        Modul,
        on_delete=models.CASCADE,
        related_name="test",
        verbose_name="Bob (Modul)",
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
        blank=True,
        help_text="URL manzillari uchun avtomatik hosil bo'luvchi qisqa nom."
    )
    description = MDTextField(
        null=True,
        blank=True,
        verbose_name="test sharti (Matn)",
        help_text="Markdown formatida masalaning to'liq shartini yozing."
    )
    duration = models.PositiveIntegerField(
        "Davomiyligi (daqiqa)",
        default=60,
        help_text="Testni yechish uchun foydalanuvchiga beriladigan umumiy vaqt (daqiqa hisobida)."
    )
    question_count = models.PositiveIntegerField(
        "Bazasidagi jami savollar soni",
        default=0,
        help_text="Ushbu test tarkibiga qo'shilgan jami umumiy savollar soni (avtomatik yoki qo'lda yangilanadi)."
    )

    min_pass_percentage = models.PositiveIntegerField(
        "O'tish foizi",
        default=60,
        validators=[MaxValueValidator(100)],
        help_text="Testdan muvaffaqiyatli o'tish uchun talaba to'plashi kerak bo'lgan eng kam foiz ko'rsatkichi (0-100)."
    )
    is_active = models.BooleanField(
        "Faol",
        default=True,
        db_index=True,
        help_text="Test talabalarga ko'rinishi yoki vaqtincha yashirib qo'yilishi uchun boshqaruv belgisi."
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
        related_name='course_tests',
        verbose_name="Yaratuvchi o'qituvchi",
        help_text="Ushbu test majmuasini yaratgan va unga egalik qiluvchi o'qituvchi/admin."
    )

    class Meta:
        verbose_name = "📋 Test"
        verbose_name_plural = "📋 Testlar"
        ordering = ["-id", "created_at"]

    def __str__(self):
        return f"Test — {self.title}"

    @property
    def total_possible_xp(self):
        """Test tarkibidagi barcha savollarning jami maksimal ballarini hisoblab beradi (Circular importlarsiz)."""
        return sum(self.questions.values_list('xp', flat=True))

    def clean(self):
        super().clean()
        if self.penalty_coefficient is not None and not (0.0 <= self.penalty_coefficient <= 1.0):
            raise ValidationError({
                "penalty_coefficient": "Jarima koeffitsiyenti 0 va 1 oralig'ida bo'lishi kerak."
            })

    def validate_ready_to_activate(self):
        """
        Testni faollashtirishdan (is_active=True) oldin chaqirish uchun:
        testda kamida bitta savol borligini va har bir savol o'zi
        to'liq (nashrga tayyor) ekanligini tekshiradi.
        """
        questions = list(self.questions.all())
        if not questions:
            raise ValidationError("Testda kamida bitta savol bo'lishi kerak.")

        errors = []
        for question in questions:
            try:
                question.validate_children_completeness()
            except ValidationError as e:
                messages = e.message_dict if hasattr(e, "message_dict") else e.messages
                errors.append(f"Savol #{question.pk}: {messages}")

        if errors:
            raise ValidationError(errors)
        return True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(CourseTest, self.title)
        super().save(*args, **kwargs)


class CourseQuestion(TimeStampedModel):
    """Test yoki Lesson uchun ishlatiladigan savol modeli."""

    class QuestionType(models.TextChoices):
        SINGLE_CHOICE = ("SINGLE_CHOICE", "Bitta tanlov")
        MULTIPLE_CHOICE = ("MULTIPLE_CHOICE", "Ko'p tanlov")
        ARRANGE_WORDS = ("ARRANGE_WORDS", "So'zlarni tartiblash")
        MATCHING = ("MATCHING", "Moslashtirish")
        FILL_BLANKS = ("FILL_BLANKS", "Bo'shliqlarni to'ldirish")

    class Difficulty(models.TextChoices):
        EASY = "easy", "Oson"
        MEDIUM = "medium", "O'rtacha"
        HARD = "hard", "Qiyin"

    DEFAULT_XP_BY_DIFFICULTY = {
        Difficulty.EASY: 3,
        Difficulty.MEDIUM: 6,
        Difficulty.HARD: 10,
    }

    MIN_CHOICES = 2
    MAX_CHOICES = 6
    MIN_MATCHING_PAIRS = 2
    MIN_ARRANGE_ITEMS = 2

    text = MDTextField(
        verbose_name="Savol matni",
        help_text="Savol matnini Markdown formatida kiriting.",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="questions",
        null=True,
        blank=True,
        verbose_name="Darslik",
    )

    test = models.ForeignKey(
        CourseTest,
        on_delete=models.CASCADE,
        related_name="questions",
        null=True,
        blank=True,
        verbose_name="Test",
    )
    instruction = models.TextField(
        blank=True,
        verbose_name="Ko'rsatma",
        help_text=(
            "O'quvchiga beriladigan ko'rsatmani kiriting. "
            "Masalan: 'So'zlarni to'g'ri tartibda joylashtiring.'"
        )
    )

    question_type = models.CharField(
        max_length=30,
        choices=QuestionType.choices,
        verbose_name="Savol turi",
        help_text=(
            "Savol turini tanlang: "
            "Ko'p tanlovli test, So'zlarni tartiblash, "
            "Moslashtirish yoki Bo'shliqlarni to'ldirish."
        )
    )

    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
        verbose_name="Qiyinchilik darajasi",
    )

    explanation_video = models.ForeignKey(
        Video,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="question_explanations",
        verbose_name="Savol video tahlili",
    )

    explanation = MDTextField(
        verbose_name="Javob izohi",
        blank=True,
        null=True,
    )

    xp = models.PositiveIntegerField(
        verbose_name="XP mukofoti",
        default=3,
        validators=[MinValueValidator(2), MaxValueValidator(20)],
    )
    is_embeddable = models.BooleanField(
        default=False,
        verbose_name="Description ichida ishlatish mumkin",
        help_text=(
            "Agar yoqilgan bo'lsa, savol description/body ichida "
            "{{savol:id:get}} placeholder orqali ishlatilishi mumkin."
        ),
    )

    # Difficulty o'zgarganda xp ni qayta hisoblash kerakligini aniqlash uchun:
    # agar admin xp ni difficulty bo'yicha standart qiymatdan boshqacha
    # qo'lda kiritgan bo'lsa, keyingi difficulty o'zgarishlarida xp avtomatik
    # qayta yozib yuborilmaydi.
    xp_is_custom = models.BooleanField(
        default=False,
        editable=False,
        verbose_name="XP qo'lda o'zgartirilganmi",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='course_created_questions',
    )

    class Meta:
        ordering = ["created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_difficulty = self.difficulty
        self._original_xp = self.xp

    def clean(self):
        super().clean()

        if not self.text or not str(self.text).strip():
            raise ValidationError({"text": "Savol matni bo'sh bo'lishi mumkin emas."})

    def validate_children_completeness(self):
        """
        Savolni "nashrga tayyor"ligini tekshiradi: savol turiga qarab
        yetarli sonli va to'g'ri to'ldirilgan child-obyektlar (Choice,
        MatchingPair, ArrangeItem, Blank/BlankAnswer) mavjudligini
        tasdiqlaydi. Bu tekshiruv `clean()` ichida emas, alohida chaqiriladi,
        chunki savol va uning child-obyektlari odatda bosqichma-bosqich
        (bir nechta so'rov davomida) yaratiladi.
        """
        errors = []

        if self.question_type in (
                self.QuestionType.SINGLE_CHOICE,
                self.QuestionType.MULTIPLE_CHOICE,
            ):
            choices = list(self.choices.all())

            if len(choices) < self.MIN_CHOICES:
                errors.append(
                    f"Kamida {self.MIN_CHOICES} ta javob varianti bo'lishi kerak "
                    f"(hozir {len(choices)} ta)."
                )

            correct_count = sum(1 for c in choices if c.is_correct)

            if self.question_type == self.QuestionType.SINGLE_CHOICE:
                if correct_count != 1:
                    errors.append(
                        f"Single Choice uchun aynan 1 ta to'g'ri javob "
                        f"bo'lishi kerak (hozir {correct_count} ta)."
                    )

            elif self.question_type == self.QuestionType.MULTIPLE_CHOICE:
                if correct_count < 1:
                    errors.append(
                        "Multiple Choice uchun kamida 1 ta to'g'ri javob "
                        "bo'lishi kerak."
                    )

            empty_texts = [
                c for c in choices
                if not c.text or not str(c.text).strip()
            ]

            if empty_texts:
                errors.append(
                    "Bo'sh matnli javob variant(lar)i mavjud."
                )

        elif self.question_type == self.QuestionType.MATCHING:
            pairs = list(self.matching_pairs.all())
            if len(pairs) < self.MIN_MATCHING_PAIRS:
                errors.append(
                    f"Kamida {self.MIN_MATCHING_PAIRS} ta moslashtirish juftligi bo'lishi kerak "
                    f"(hozir {len(pairs)} ta)."
                )
            lefts = [p.left.strip().lower() for p in pairs if p.left]
            rights = [p.right.strip().lower() for p in pairs if p.right]
            if len(lefts) != len(set(lefts)):
                errors.append("Takrorlanuvchi 'chap tomon' qiymatlari mavjud.")
            if len(rights) != len(set(rights)):
                errors.append("Takrorlanuvchi 'o'ng tomon' qiymatlari mavjud.")

        elif self.question_type == self.QuestionType.ARRANGE_WORDS:
            items = sorted(self.arrange_items.all(), key=lambda i: i.correct_position)
            if len(items) < self.MIN_ARRANGE_ITEMS:
                errors.append(
                    f"Kamida {self.MIN_ARRANGE_ITEMS} ta so'z bo'lishi kerak (hozir {len(items)} ta)."
                )
            else:
                positions = [i.correct_position for i in items]
                expected = list(range(1, len(positions) + 1))
                if positions != expected:
                    errors.append(
                        "correct_position qiymatlari 1 dan boshlab uzilishsiz ketma-ket bo'lishi kerak "
                        f"(kutilgan: {expected}, mavjud: {positions})."
                    )

        elif self.question_type == self.QuestionType.FILL_BLANKS:
            blanks = list(self.blanks.all())
            if not blanks:
                errors.append("Kamida 1 ta bo'sh joy (Blank) bo'lishi kerak.")
            else:
                for blank in blanks:
                    if not blank.answers.exists():
                        errors.append(
                            f"{blank.position}-bo'sh joy uchun kamida 1 ta to'g'ri javob kiritilishi kerak."
                        )

        if errors:
            raise ValidationError(errors)
        return True

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.xp = self.DEFAULT_XP_BY_DIFFICULTY[self.difficulty]
        else:
            difficulty_changed = self.difficulty != self._original_difficulty
            was_default_xp = self._original_xp == self.DEFAULT_XP_BY_DIFFICULTY.get(
                self._original_difficulty
            )
            xp_changed_manually = self.xp != self._original_xp

            if xp_changed_manually and not difficulty_changed:
                # Admin xp ni qo'lda o'zgartirdi -> bundan buyon avtomatik qayta yozilmasin
                self.xp_is_custom = True
            elif difficulty_changed and was_default_xp and not self.xp_is_custom:
                # Difficulty o'zgardi va xp hali standart qiymatda edi -> yangi standartga o'tkazamiz
                self.xp = self.DEFAULT_XP_BY_DIFFICULTY[self.difficulty]

        super().save(*args, **kwargs)
        self._original_difficulty = self.difficulty
        self._original_xp = self.xp

    def __str__(self):
        location = f"Lesson #{self.lesson_id}" if self.lesson_id else f"Test #{self.test_id}"
        return f"Savol #{self.pk} — {location}"


class CourseChoice(models.Model):
    """Savol javoblari variantlari (Choice) — faqat MULTIPLE_CHOICE uchun."""

    question = models.ForeignKey(
        "CourseQuestion",
        on_delete=models.CASCADE,
        related_name="choices",
        verbose_name="Tegishli savol",
    )

    text = MDTextField(
        verbose_name="Variant matni",
        help_text="Markdown formatida javob variantining matnini kiriting."
    )

    is_correct = models.BooleanField(
        "To'g'ri javob",
        default=False,
        db_index=True,
        help_text="Agar ushbu variant savolning to'g'ri javobi bo'lsa, belgilang."
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_choices",
        verbose_name="Yaratuvchi",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    class Meta:
        verbose_name = "🔘 Javob varianti"
        verbose_name_plural = "✅ Javob variantlari"
       

    def __str__(self):
        status = "✅" if self.is_correct else "❌"
        return f"[{status}] {self.text[:40]}..."

    def clean(self):
        super().clean()

        if not self.question_id:
            return

        question = self.question

        if question.question_type not in (
            CourseQuestion.QuestionType.SINGLE_CHOICE,
            CourseQuestion.QuestionType.MULTIPLE_CHOICE,
        ):
            raise ValidationError(
                "Choice faqat Single Choice yoki Multiple Choice savollarda ishlatiladi."
            )

        if not self.text or not str(self.text).strip():
            raise ValidationError({
                "text": "Variant matni bo'sh bo'lishi mumkin emas."
            })

        duplicate_qs = CourseChoice.objects.filter(
            question_id=self.question_id,
            text__iexact=str(self.text).strip(),
        )

        if self.pk:
            duplicate_qs = duplicate_qs.exclude(pk=self.pk)

        if duplicate_qs.exists():
            raise ValidationError({
                "text": "Ushbu savolda xuddi shunday variant allaqachon mavjud."
            })

        # SINGLE_CHOICE -> faqat 1 ta correct
        if (
            question.question_type == CourseQuestion.QuestionType.SINGLE_CHOICE
            and self.is_correct
        ):
            qs = CourseChoice.objects.filter(
                question_id=self.question_id,
                is_correct=True,
            )

            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    "is_correct": (
                        "Single Choice savolda faqat 1 ta to'g'ri "
                        "javob bo'lishi mumkin."
                    )
                })


class MatchingPair(models.Model):
    """
    Matching turidagi savollar uchun moslashtirish juftligi.

    Masalan:
    Apple -> Olma
    Book  -> Kitob
    """

    question = models.ForeignKey(
        CourseQuestion,
        on_delete=models.CASCADE,
        related_name="matching_pairs",
        verbose_name="Savol",
        help_text="Ushbu juftlik tegishli bo'lgan Matching savolini tanlang."
    )

    left = models.CharField(
        max_length=255,
        verbose_name="Chap tomon",
        help_text="Moslashtirishning chap tomonidagi elementni kiriting."
    )

    right = models.CharField(
        max_length=255,
        verbose_name="O'ng tomon",
        help_text="Chap tomonga mos keladigan javobni kiriting."
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Tartib raqami",
        help_text="Juftlikning savol ichidagi tartibini belgilang."
    )

    class Meta:
        verbose_name = "🔗 Moslashtirish juftligi"
        verbose_name_plural = "🔗 Moslashtirish juftliklari"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "order"],
                name="unique_matching_order_per_question",
            ),
        ]

    def __str__(self):
        return f"{self.left} → {self.right}"

    def clean(self):
        super().clean()
        if self.question_id and self.question.question_type != CourseQuestion.QuestionType.MATCHING:
            raise ValidationError(
                "Moslashtirish juftligi faqat 'Moslashtirish' turidagi savollarga qo'shilishi mumkin."
            )

        if not self.left or not self.left.strip():
            raise ValidationError({"left": "Chap tomon bo'sh bo'lishi mumkin emas."})
        if not self.right or not self.right.strip():
            raise ValidationError({"right": "O'ng tomon bo'sh bo'lishi mumkin emas."})

        if self.question_id:
            duplicate_left = MatchingPair.objects.filter(
                question_id=self.question_id, left__iexact=self.left.strip()
            )
            duplicate_right = MatchingPair.objects.filter(
                question_id=self.question_id, right__iexact=self.right.strip()
            )
            if self.pk:
                duplicate_left = duplicate_left.exclude(pk=self.pk)
                duplicate_right = duplicate_right.exclude(pk=self.pk)
            if duplicate_left.exists():
                raise ValidationError({"left": "Bu savolda xuddi shu 'chap tomon' qiymati allaqachon mavjud."})
            if duplicate_right.exists():
                raise ValidationError({"right": "Bu savolda xuddi shu 'o'ng tomon' qiymati allaqachon mavjud."})


class ArrangeItem(models.Model):
    """
    Arrange Words savollari uchun so'zlar.
    """

    question = models.ForeignKey(
        CourseQuestion,
        on_delete=models.CASCADE,
        related_name="arrange_items",
        verbose_name="Savol",
        help_text="Ushbu so'z tegishli bo'lgan Arrange Words savolini tanlang."
    )

    text = models.CharField(
        max_length=255,
        verbose_name="So'z",
        help_text="Tartiblanadigan so'zni kiriting."
    )

    correct_position = models.PositiveIntegerField(
        verbose_name="To'g'ri pozitsiya",
        validators=[MinValueValidator(1)],
        help_text=(
            "Ushbu so'zning to'g'ri gapdagi pozitsiyasini kiriting (1 dan boshlab). "
            "Masalan: 1, 2, 3, 4."
        )
    )

    class Meta:
        verbose_name = "🔤 Tartiblanadigan so'z"
        verbose_name_plural = "🔤 Tartiblanadigan so'zlar"
        ordering = ["correct_position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "correct_position"],
                name="unique_arrange_position_per_question"
            ),
            models.CheckConstraint(
                condition=models.Q(correct_position__gte=1),
                name="arrange_item_position_gte_1",
            ),
        ]

    def __str__(self):
        return f"{self.correct_position}. {self.text}"

    def clean(self):
        super().clean()
        if self.question_id and self.question.question_type != CourseQuestion.QuestionType.ARRANGE_WORDS:
            raise ValidationError(
                "Bu element faqat 'So'zlarni tartiblash' turidagi savollarga qo'shilishi mumkin."
            )
        if not self.text or not self.text.strip():
            raise ValidationError({"text": "So'z bo'sh bo'lishi mumkin emas."})


class Blank(models.Model):
    """
    Fill in the Blanks savolidagi bo'sh joy.
    Har bir Blank bir nechta to'g'ri javobga ega bo'lishi mumkin (sinonimlar) —
    ular BlankAnswer orqali saqlanadi.
    """

    question = models.ForeignKey(
        CourseQuestion,
        on_delete=models.CASCADE,
        related_name="blanks",
        verbose_name="Savol",
        help_text="Ushbu bo'sh joy tegishli bo'lgan savolni tanlang."
    )

    position = models.PositiveIntegerField(
        verbose_name="Bo'sh joy tartibi",
        validators=[MinValueValidator(1)],
        help_text="Bo'sh joyning gap ichidagi tartib raqamini kiriting (1 dan boshlab)."
    )

    case_sensitive = models.BooleanField(
        default=False,
        verbose_name="Katta-kichik harfga sezgir",
        help_text="Yoqilsa, javob tekshirilganda harflar registri ham hisobga olinadi."
    )

    class Meta:
        verbose_name = "◻️ Bo'sh joy"
        verbose_name_plural = "◻️ Bo'sh joylar"
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"],
                name="unique_blank_position_per_question"
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1),
                name="blank_position_gte_1",
            ),
        ]

    def __str__(self):
        return f"{self.question.text[:30]} - {self.position}-bo'sh joy"

    def clean(self):
        super().clean()
        if self.question_id and self.question.question_type != CourseQuestion.QuestionType.FILL_BLANKS:
            raise ValidationError(
                "Bo'sh joy faqat 'Bo'shliqlarni to'ldirish' turidagi savollarga qo'shilishi mumkin."
            )

    def is_correct_answer(self, submitted_text: str) -> bool:
        """
        Berilgan matn ushbu bo'sh joy uchun qabul qilinadigan javoblardan
        biriga mos kelishini tekshiradi.

        MUHIM: `.answers.all()` ishlatiladi (`.values_list()` emas), chunki
        `.all()` Django'ning prefetch_related keshidan foydalanadi —
        chaqiruvchi (masalan, CourseTestSession.calculate_mathematical_score)
        `question__blanks__answers` ni oldindan prefetch qilgan bo'lsa, bu
        yerda hech qanday qo'shimcha DB so'rovi yubormaydi. `.values_list()`
        esa har doim yangi so'rov yuborardi.
        """
        if submitted_text is None:
            return False

        candidates = [a.answer for a in self.answers.all()]

        if self.case_sensitive:
            return submitted_text.strip() in [c.strip() for c in candidates]

        submitted_norm = submitted_text.strip().lower()
        return submitted_norm in [c.strip().lower() for c in candidates]


class BlankAnswer(models.Model):
    """
    Bitta bo'sh joy uchun qabul qilinadigan to'g'ri javob(lar).

    Masalan (bitta Blank uchun bir nechta yozuv):
    am
    I'm
    """

    blank = models.ForeignKey(
        Blank,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Bo'sh joy",
        help_text="Javob tegishli bo'lgan bo'sh joyni tanlang."
    )

    answer = models.CharField(
        max_length=255,
        verbose_name="To'g'ri javob",
        help_text="Ushbu bo'sh joy uchun qabul qilinadigan to'g'ri javobni kiriting."
    )

    class Meta:
        verbose_name = "◻️ Bo'sh joy javobi"
        verbose_name_plural = "◻️ Bo'sh joy javoblari"
        constraints = [
            models.UniqueConstraint(
                fields=["blank", "answer"],
                name="unique_answer_per_blank",
            )
        ]

    def __str__(self):
        return self.answer

    def clean(self):
        super().clean()
        if not self.answer or not self.answer.strip():
            raise ValidationError({"answer": "Javob matni bo'sh bo'lishi mumkin emas."})

class CourseUserResponse(models.Model):
    """
    Talabaning har bir savolga bergan javobi.

    SINGLE_CHOICE
        -> `choice` orqali bitta variant.

    MULTIPLE_CHOICE
        -> `selected_choices` orqali bir nechta variant.

    MATCHING
        -> answer_data = {
            "1": "Olma",
            "2": "Kitob",
        }

    ARRANGE_WORDS
        -> answer_data = {
            "order": [item_id1, item_id2, ...]
        }

    FILL_BLANKS
        -> answer_data = {
            "blank_id": "javob matni"
        }
    """

    session = models.ForeignKey(
        "CourseTestSession",
        on_delete=models.CASCADE,
        related_name="responses",
        null=True,
        blank=True,
        verbose_name="Test seansi",
    )

    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="quiz_responses",
        verbose_name="Foydalanuvchi",
        help_text="Javob bergan talaba.",
    )

    question = models.ForeignKey(
        CourseQuestion,
        on_delete=models.CASCADE,
        related_name="user_responses",
        verbose_name="Savol",
        help_text="Javob berilgan test yoki darslik savoli.",
    )

    # ======================================================
    # SINGLE_CHOICE
    # ======================================================

    choice = models.ForeignKey(
        CourseChoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="single_choice_responses",
        verbose_name="Tanlangan variant",
        help_text=(
            "SINGLE_CHOICE savol uchun talaba tanlagan "
            "bitta javob varianti."
        ),
    )

    # ======================================================
    # MULTIPLE_CHOICE
    # ======================================================

    selected_choices = models.ManyToManyField(
        CourseChoice,
        blank=True,
        related_name="multiple_choice_responses",
        verbose_name="Tanlangan variantlar",
        help_text=(
            "MULTIPLE_CHOICE savol uchun talaba tanlagan "
            "bir yoki bir nechta javob variantlari."
        ),
    )

    # ======================================================
    # MATCHING / ARRANGE_WORDS / FILL_BLANKS
    # ======================================================

    answer_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Javob (JSON)",
        help_text=(
            "Matching, Arrange Words yoki Fill Blanks "
            "savollarining javob ma'lumotlari."
        ),
    )

    is_correct = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="To'g'ri javob",
        help_text=(
            "Tekshirilgandan so'ng avtomatik hisoblab qo'yiladi "
            "(null = hali tekshirilmagan)."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Javob berilgan vaqt",
        help_text=(
            "Talaba joriy savolga javob tugmasini bosgan "
            "aniq vaqt."
        ),
    )

    class Meta:
        verbose_name = "🎯 Foydalanuvchi Javobi"
        verbose_name_plural = "🎯 Foydalanuvchi Javoblari"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question"],
                name="unique_response_per_question_per_session",
            ),
        ]

    def __str__(self):
        is_answered = (
            bool(self.choice_id)
            or bool(self.answer_data)
            or (
                self.pk is not None
                and self.selected_choices.exists()
            )
        )

        status_text = (
            "Javob berilgan"
            if is_answered
            else "Javobsiz qoldirilgan"
        )

        username = (
            self.user.username
            if self.user.username
            else f"User-{self.user.telegram_id}"
        )

        return (
            f"{username} -> "
            f"Savol №{self.question_id} "
            f"[{status_text}]"
        )

    # ======================================================
    # VALIDATION
    # ======================================================

    def clean(self):
        super().clean()

        if not self.question_id:
            return

        question = self.question
        q_type = question.question_type

        # --------------------------------------------------
        # choice boshqa savolga tegishli emasligini tekshirish
        # --------------------------------------------------

        if self.choice_id:
            if self.choice.question_id != self.question_id:
                raise ValidationError({
                    "choice": (
                        "Siz buzib kirishga urindingiz! "
                        "Tanlangan javob varianti ushbu "
                        "savolga tegishli emas."
                    )
                })

        # --------------------------------------------------
        # session security
        # --------------------------------------------------

        if self.session_id:
            if (
                question.test_id
                and question.test_id != self.session.test_id
            ):
                raise ValidationError({
                    "question": (
                        "Bu savol ushbu test seansiga "
                        "tegishli test tarkibida emas."
                    )
                })

        # --------------------------------------------------
        # SINGLE_CHOICE
        # --------------------------------------------------

        if q_type == CourseQuestion.QuestionType.SINGLE_CHOICE:

            if self.answer_data:
                raise ValidationError({
                    "answer_data": (
                        "SINGLE_CHOICE savolda "
                        "answer_data ishlatilmaydi."
                    )
                })

            # selected_choices yangi objectda hali mavjud bo'lmaydi.
            # Agar mavjud response update qilinayotgan bo'lsa tekshiramiz.
            if self.pk and self.selected_choices.exists():
                raise ValidationError({
                    "selected_choices": (
                        "SINGLE_CHOICE savolda "
                        "selected_choices ishlatilmaydi. "
                        "choice ishlatiladi."
                    )
                })

            if self.choice_id:
                if self.choice.question_id != self.question_id:
                    raise ValidationError({
                        "choice": (
                            "Tanlangan variant ushbu "
                            "savolga tegishli emas."
                        )
                    })

        # --------------------------------------------------
        # MULTIPLE_CHOICE
        # --------------------------------------------------

        elif q_type == CourseQuestion.QuestionType.MULTIPLE_CHOICE:

            if self.choice_id:
                raise ValidationError({
                    "choice": (
                        "MULTIPLE_CHOICE savolda "
                        "choice ishlatilmaydi. "
                        "selected_choices ishlatiladi."
                    )
                })

            if self.answer_data:
                raise ValidationError({
                    "answer_data": (
                        "MULTIPLE_CHOICE savolda "
                        "answer_data ishlatilmaydi."
                    )
                })

            # M2M validation save()dan keyingi bosqichda
            # serializer/service orqali ham bajarilishi kerak.

        # --------------------------------------------------
        # MATCHING / ARRANGE / FILL
        # --------------------------------------------------

        elif q_type in (
            CourseQuestion.QuestionType.MATCHING,
            CourseQuestion.QuestionType.ARRANGE_WORDS,
            CourseQuestion.QuestionType.FILL_BLANKS,
        ):

            if self.choice_id:
                raise ValidationError({
                    "choice": (
                        "Ushbu savol turi uchun "
                        "choice ishlatilmaydi."
                    )
                })

            if self.pk and self.selected_choices.exists():
                raise ValidationError({
                    "selected_choices": (
                        "Ushbu savol turi uchun "
                        "selected_choices ishlatilmaydi."
                    )
                })

    # ======================================================
    # SINGLE CHOICE CHECK
    # ======================================================

    def _check_single_choice(self) -> bool:
        """
        SINGLE_CHOICE uchun:

        Student:
            B

        Correct:
            B

        => True
        """

        if not self.choice_id:
            return False

        if self.choice.question_id != self.question_id:
            return False

        return bool(self.choice.is_correct)

    # ======================================================
    # MULTIPLE CHOICE CHECK
    # ======================================================

    def _check_multiple_choice(self) -> bool:
        """
        MULTIPLE_CHOICE uchun tanlangan variantlar
        correct variantlar bilan aynan bir xil bo'lishi kerak.

        Masalan:

        Correct:
            B
            D

        Student:
            B + D
                -> True

        Student:
            B
                -> False

        Student:
            B + C + D
                -> False
        """

        selected_ids = set(
            self.selected_choices.values_list(
                "id",
                flat=True,
            )
        )

        if not selected_ids:
            return False

        # Buzib kirishni oldini olish:
        # barcha tanlangan choice aynan shu savolniki bo'lishi kerak.

        question_choice_ids = set(
            self.question.choices.values_list(
                "id",
                flat=True,
            )
        )

        if not selected_ids.issubset(question_choice_ids):
            return False

        correct_ids = set(
            self.question.choices
            .filter(is_correct=True)
            .values_list(
                "id",
                flat=True,
            )
        )

        if not correct_ids:
            return False

        # Strict matching:
        # tanlanganlar == to'g'ri javoblar
        return selected_ids == correct_ids

    # ======================================================
    # MATCHING
    # ======================================================

    def _check_matching(self) -> bool:
        """
        Kutilgan answer_data:

        {
            "1": "Olma",
            "2": "Kitob"
        }
        """

        if not self.answer_data:
            return False

        pairs = {
            str(p.id): p.right
            for p in self.question.matching_pairs.all()
        }

        if not pairs:
            return False

        for pair_id, correct_right in pairs.items():
            submitted = self.answer_data.get(pair_id)

            if (
                not isinstance(submitted, str)
                or submitted.strip().lower()
                != correct_right.strip().lower()
            ):
                return False

        return True

    # ======================================================
    # ARRANGE WORDS
    # ======================================================

    def _check_arrange_words(self) -> bool:
        """
        Kutilgan:

        {
            "order": [7, 3, 9, 2]
        }
        """

        if not self.answer_data:
            return False

        submitted_order = self.answer_data.get("order")

        if not submitted_order:
            return False

        items = sorted(
            self.question.arrange_items.all(),
            key=lambda i: i.correct_position,
        )

        correct_order = [
            item.id
            for item in items
        ]

        try:
            submitted_order = [
                int(item_id)
                for item_id in submitted_order
            ]
        except (TypeError, ValueError):
            return False

        return submitted_order == correct_order

    # ======================================================
    # FILL BLANKS
    # ======================================================

    def _check_fill_blanks(self) -> bool:
        """
        Kutilgan:

        {
            "11": "am",
            "12": "Python"
        }
        """

        if not self.answer_data:
            return False

        blanks = list(
            self.question.blanks.all()
        )

        if not blanks:
            return False

        for blank in blanks:
            submitted = self.answer_data.get(
                str(blank.id)
            )

            if not blank.is_correct_answer(submitted):
                return False

        return True

    # ======================================================
    # CHECK + SCORE
    # ======================================================

    def check_and_score(self):
        """
        Javobni savol turiga qarab tekshiradi.

        Return:

            (is_answered, is_correct)
        """

        q_type = self.question.question_type

        # --------------------------------------------------
        # Javob berilganligini aniqlash
        # --------------------------------------------------

        if q_type == CourseQuestion.QuestionType.SINGLE_CHOICE:
            is_answered = bool(self.choice_id)

        elif q_type == CourseQuestion.QuestionType.MULTIPLE_CHOICE:
            is_answered = self.selected_choices.exists()

        else:
            is_answered = bool(self.answer_data)

        # --------------------------------------------------
        # Javobsiz
        # --------------------------------------------------

        if not is_answered:
            if self.is_correct is not None:
                self.is_correct = None
                self.save(
                    update_fields=["is_correct"]
                )

            return False, False

        # --------------------------------------------------
        # Checker
        # --------------------------------------------------

        checkers = {
            CourseQuestion.QuestionType.SINGLE_CHOICE:
                self._check_single_choice,

            CourseQuestion.QuestionType.MULTIPLE_CHOICE:
                self._check_multiple_choice,

            CourseQuestion.QuestionType.MATCHING:
                self._check_matching,

            CourseQuestion.QuestionType.ARRANGE_WORDS:
                self._check_arrange_words,

            CourseQuestion.QuestionType.FILL_BLANKS:
                self._check_fill_blanks,
        }

        checker = checkers.get(q_type)

        result = (
            bool(checker())
            if checker
            else False
        )

        # --------------------------------------------------
        # is_correct update
        # --------------------------------------------------

        if self.is_correct != result:
            self.is_correct = result

            self.save(
                update_fields=["is_correct"]
            )

        return True, result