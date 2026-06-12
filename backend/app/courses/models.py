from django.db import models
from django.utils.text import slugify
from baseuser.models import BaseUser


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
    description = models.TextField(
        "Tavsif",
        help_text="Kurs haqida batafsil ma’lumot kiriting"
    )
    is_active = models.BooleanField(default=False)
    # To'g'ri variant
    image = models.ImageField(upload_to="course/images/")
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

    class Meta:
        verbose_name = "✨ Kurs"
        verbose_name_plural = "✨ Kurslar"

    # Hozirgi amal qilayotgan narxni olish uchun funksiya
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
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")
    class Meta:
        verbose_name = "📚 Kurs"
        verbose_name_plural = "📚 Kurslar"

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


class Enrilliment(TimeStampedModel):
    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name='kursga_yozilishlar',
        verbose_name="Foydalanuvchi",
        help_text="Kursga yozilayotgan talaba"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='kursga_yozilishlar',
        verbose_name="Kurs",
        help_text="Qaysi kursga yozilmoqda"
    )
    is_paid = models.BooleanField(
        "To‘langan",
        default=False,
        help_text="Agar kurs pullik bo‘lsa, bu yerda belgilash mumkin"
    )

    class Meta:
        unique_together = ('user', 'course')
        verbose_name = "✨ Kursga yozilish"
        verbose_name_plural = "✨ Kursga yozilishlar"

    def __str__(self):
        return f"{self.user.telegram_id} → {self.course.title}"
    

class Lesson(models.Model):
    modul = models.ForeignKey(
        Modul,
        on_delete=models.CASCADE,
        related_name='lesson',
        verbose_name="Kurs",
        help_text="Qaysi kursga yozilmoqda"
    )
    title = models.CharField("Darslik nomi", max_length=100)
    slug = models.SlugField(
        "Slug",
        blank=True,
        help_text="URL uchun slug, avtomatik hosil qilinadi"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")
    def __str__(self):
        return f"kurs-{self.modul.course.title[:20]}:modul-{self.modul.title[:15]}:dasrlik-{self.title[:15]}"
    
    class Meta:
        verbose_name = "📝 Dars"
        verbose_name_plural = "📝 Darslar"
