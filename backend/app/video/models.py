import uuid
from django.db import models
from django.utils.text import slugify
from mdeditor.fields import MDTextField


class Video(models.Model):
    title = models.CharField(
        max_length=250, 
        verbose_name="Video sarlavhasi",
        help_text="Video darslik yoki yechim tahlili uchun qisqa va tushunarli nom kiriting (Masalan: 'A+B masalasi tahlili')."
    )
    
    slug = models.SlugField(
        unique=True, 
        blank=True, 
        max_length=300,
        verbose_name="URL sarlavha (Slug)",
        help_text="Brauzer havolasi (URL) uchun sarlavhadan avtomatik generatsiya qilinadigan qism. Qo'lda yozish shart emas."
    )
    
    duration = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Davomiyligi",
        help_text="Video darslikning davomiyligi (Masalan: 12:45). Video fayli yuklanganidan so'ng, Celery buni fonda avtomatik to'ldiradi."
    )
    
    description = MDTextField(
        verbose_name="Batafsil tavsif",
        help_text="Video darslik mazmuni haqida batafsil ma'lumot. Markdown belgilari yordamida formula va kodlarni chiroyli yozishingiz mumkin."
    )

    # 🖼 RASMLAR (POSTERS & BACKDROPS) BLOKI
    image = models.ImageField(
        upload_to="movies/posters/", 
        blank=True, 
        null=True, 
        verbose_name="Asosiy rasm (Poster fayl)",
        help_text="Videoning vertikal muqovasi (poster). Kompyuteringizdan rasm faylini yuklang (MinIO/S3 bulutli omboriga saqlanadi)."
    )
    
    thumbnail = models.URLField(
        blank=True, 
        null=True, 
        verbose_name="Tashqi rasm (Poster URL)",
        help_text="Videoning kichik muqovasi uchun tayyor internet havolasi (URL). Video yuklangandan keyin, Celery birinchi sekundlardan qirqib olib avtomat to'ldiradi."
    )
    
    backdrop_image = models.ImageField(
        upload_to="movies/backdrops/", 
        blank=True, 
        null=True, 
        verbose_name="Katta fon rasmi (Backdrop fayl)",
        help_text="Video pleyer orqasida yoki dars sahifasining yuqori qismida fon (background) sifatida turadigan keng formatli (16:9) katta rasm fayli."
    )
    
    backdrop = models.URLField(
        blank=True, 
        null=True, 
        verbose_name="Tashqi fon rasmi (Backdrop URL)",
        help_text="Video sahifasining orqa foni uchun tayyor internet havolasini (URL) kiriting. Bu serverda joy tejashga yordam beradi."
    )

    # 🎥 VIDEO STREAMING FAYLLARI BLOKI
    video = models.FileField(
        upload_to="movies/videos/", 
        blank=True, 
        null=True, 
        verbose_name="Asl video fayli (MP4)",
        help_text="Kompyuteringizdan darslikning asl video faylini (MP4 formatida) yuklang. Tizim uni fonda avtomat HLS formatiga o'giradi."
    )
    
    hls_url = models.URLField(
        blank=True, 
        null=True, 
        verbose_name="HLS (m3u8) oqim manzili",
        help_text="Video darslikning onlayn tezkor oqimli (streaming) uzatish linki. Video yuklangandan keyin, Celery buni avtomat yaratadi."
    )
    
    mp4_url = models.URLField(
        blank=True, 
        null=True, 
        verbose_name="MP4 to'g'ridan-to'g'ri manzili",
        help_text="Videoni foydalanuvchilar yuklab olishi uchun to'g'ridan-to'g'ri link. Celery tomonidan avtomatik to'ldiriladi."
    )

    class Meta:
        verbose_name = "🎬 Video"
        verbose_name_plural = "🎥 Videolar"
        ordering = ["-title"]  # UUID bo'yicha tartiblab bo'lmagani uchun sarlavha bo'yicha teskari tartiblandi
        indexes = [
            models.Index(fields=["slug"]),
        ]

    @property
    def get_thumbnail(self):
        """API va Front-end uchun har doim xavfsiz rasm URL manzilini qaytaradi."""
        if self.image:
            return self.image.url
        return self.thumbnail if self.thumbnail else "https://placehold.co"

    def save(self, *args, **kwargs):
        # O'zbekcha harflarni to'g'ri slugify qilish va unikal slug yaratish
        if not self.slug:
            cleaned_title = self.title.replace("o'", "o").replace("g'", "g").replace("O'", "o").replace("G'", "g")
            base_slug = slugify(cleaned_title)
            slug = base_slug
            counter = 1
            while Video.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
