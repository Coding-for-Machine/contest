from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from problems.models import Problem

class Video(models.Model):
    problem = models.ForeignKey(
        Problem,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="problem_videos",
        help_text="Agar video konkret bir masalaga tegishli bo'lsa tanlang"
    )

    title = models.CharField(
        max_length=250, 
        verbose_name="Video sarlavhasi",
        help_text="Video uchun qisqa va tushunarli nom"
    )
    
    slug = models.SlugField(
        unique=True, 
        blank=True, 
        max_length=300,
        help_text="URL uchun avtomatik yaratiladigan qism"
    )

    duration = models.CharField(
        max_length=50,
        help_text="Davomiyligi (masalan: 12:45)",
        blank=True,
        null=True,
    )

    description = models.TextField(
        verbose_name="Tavsif",
        help_text="Video haqida batafsil ma'lumot"
    )

    # ✅ Tasvirlar (MinIO/S3 ga ketadi)
    image = models.ImageField(
        upload_to="movies/posters/",
        verbose_name="Asosiy rasm",
        help_text="Video ro'yxatda ko'ringanda chiqadigan rasm"
    )
    thumbnail = models.URLField(
        blank=True, 
        null=True,
        help_text="Tashqi manbadagi kichik rasm (URL)"
    )
    
    backdrop_image = models.ImageField(
        upload_to="movies/backdrops/",
        blank=True, 
        null=True,
        verbose_name="Fon rasmi",
        help_text="Video pleyer orqasida ko'rinadigan katta rasm"
    )
    backdrop = models.URLField(
        blank=True, 
        null=True,
        help_text="Tashqi manbadagi fon rasmi (URL)"
    )

    video = models.FileField(
        upload_to="movies/videos/", 
        blank=True, 
        null=True,
        verbose_name="Video fayli",
        help_text="Asl video faylini yuklang (mp4)"
    )
    hls_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name="HLS (m3u8) manzili",
        help_text="Video oqimi (streaming) uchun link"
    )
    mp4_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name="MP4 manzili",
        help_text="Video yuklab olish uchun to'g'ridan-to'g'ri link"
    )

    class Meta:
        verbose_name = "🎬 Video"
        verbose_name_plural = "🎥 Videolar"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["id"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title