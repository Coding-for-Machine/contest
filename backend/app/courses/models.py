from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from baseuser.models import BaseUser
from problems.models import Problem
from mdeditor.fields import MDTextField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqti", auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class Course(TimeStampedModel):
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
    total_lessons_count = models.PositiveSmallIntegerField(default=0, verbose_name="Jami darslar soni")
    total_test_count = models.PositiveSmallIntegerField(default=0, verbose_name="Jami test soni")

    class Meta:
        verbose_name = "✨ Kurs"
        verbose_name_plural = "✨ Kurslar"

    @property
    def current_price(self):
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    def __str__(self):
        return f"{self.title} - {self.current_price} UZS"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Course.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
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
        help_text="Modul URL uchun (ixtiyoriy, avtomatik hosil bo'ladi)"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moduls',
    )

    class Meta:
        verbose_name = "📚 Kurs Bobi"
        verbose_name_plural = "📚 Kurs boblari"

    def __str__(self):
        return f"{self.title} ({self.course.title})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Modul.objects.filter(course=self.course, slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Lesson(TimeStampedModel):
    modul = models.ForeignKey(
        Modul,
        on_delete=models.CASCADE,
        related_name='lessons',  # Ko'plik shakliga keltirildi
        verbose_name="Modul",
        help_text="Dars qaysi modulga tegishli"
    )
    title = models.CharField("Darslik nomi", max_length=100)
    slug = models.SlugField(
        "Slug",
        blank=True,
        help_text="URL uchun slug, avtomatik hosil qilinadi"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lessons',
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Tartib raqami"),
        help_text=_("Ushbu blok dars interfeysida qaysi ketma-ketlikda chiqishini tartiblovchi raqam.")
    )
    total_tasks_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Jami vazifalar soni",
        editable=False,  # faqat signal orqali yangilanadi, admin panelda qo'lda o'zgartirilmasin
        help_text="Problem + Question(lesson) + Lecture sonlarining avtomatik yig'indisi."
    )
    def __str__(self):
        return f"kurs-{self.modul.course.title[:20]}:modul-{self.modul.title[:15]}:dasrlik-{self.title[:15]}"
    
    class Meta:
        verbose_name = "📝 Dars"
        verbose_name_plural = "📝 Darslar"


class Enrollment(TimeStampedModel):
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    is_paid = models.BooleanField("To'langan", default=False)

    finished_darslar_soni = models.PositiveSmallIntegerField(default=0)
    finished_test_soni = models.PositiveSmallIntegerField(default=0)
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'course')
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
        blank=True,  # Video bor joyda matn majburiy bo'lmasligi uchun True qilindi
        null=True,
        help_text=_("Markdown formatida ma'ruza matnini, qoidalarni va kod namunalarini yozing.")
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Tartib raqami"),
        help_text=_("Ushbu blok dars interfeysida qaysi ketma-ketlikda chiqishini tartiblovchi raqam.")
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
        related_name='lecture',
    )


    class Meta:
        verbose_name = _("📖 Ma'ruza va Video dars")
        verbose_name_plural = _("📖 Ma'ruzalar va Video darslar")
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['lesson', 'order']),
            models.Index(fields=['slug']),
            models.Index(fields=['video']),
        ]

    def __str__(self):
        type_prefix = "🎥 Video+Matn" if self.video and self.body else ("🎥 Faqat Video" if self.video else "📄 Faqat Matn")
        return f"[{type_prefix}] {self.lesson.title[:15]} -> {self.title[:25]}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.video and not self.body:
            raise ValidationError(
                _("Ma'ruza bloki bo'sh bo'lishi mumkin emas! Kamida Video darslik yuklang yoki Matn kiriting.")
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Lecture.objects.filter(lesson=self.lesson, slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
