import os
import uuid
from io import BytesIO
from PIL import Image

from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError

def validate_image_extension(value):
    """Admin noto'g'ri format yoki juda og'ir rasm yuklashini to'sish"""
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if not ext.lower() in valid_extensions:
        raise ValidationError("Faqat JPG, JPEG, PNG yoki WEBP formatidagi rasmlarni yuklash mumkin!")

    # Maksimal hajm cheklovi: 10 MB (Xavfsizlik va tarmoq trafigi uchun)
    if value.size > 10 * 1024 * 1024:
        raise ValidationError("Rasm hajmi 10 MB dan oshmasligi kerak!")


class Video(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.FileField(
        upload_to="movies/videos/", 
        blank=True, 
        null=True, 
        verbose_name="Asl video fayli (MP4)",
        help_text="Kompyuteringizdan darslikning asl video faylini yuklang."
    )
    thumbnail = models.ImageField(
        upload_to="movies/thumbnails/", 
        blank=True, 
        null=True, 
        validators=[validate_image_extension],
        verbose_name="Video muqovasi (Rasm)",
        help_text="Videoga tegishli rasm (poster) yuklang. Avtomat 16:9 qilib kesiladi va siqiladi."
    )
    hls_url = models.URLField(blank=True, null=True, verbose_name="HLS (m3u8) oqim manzili")
    duration = models.CharField(max_length=10, blank=True, null=True, verbose_name="Video davomiyligi")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "🎬 Video"
        verbose_name_plural = "🎥 Videolar"

    def __str__(self):
        return f"video-{self.id}"

    def save(self, *args, **kwargs):
        # 1. Rasm yuklanganini tekshiramiz
        if self.thumbnail:
            if not self.pk:
                # Agar yangi obyekt bo'lsa, rasmni srazi optimallashtiramiz
                self.optimize_thumbnail()
            else:
                # Agar eski obyekt tahrirlanayotgan bo'lsa (Update)
                # Bazadagi eski rasmni xavfsiz tekshiramiz (get o'rniga filter + first)
                old_instance = Video.objects.filter(pk=self.pk).first()
                if old_instance and old_instance.thumbnail != self.thumbnail:
                    self.optimize_thumbnail()
                    
        super().save(*args, **kwargs)


    def optimize_thumbnail(self):
        """
        Admin yuklagan istalgan o'lchamdagi rasmni avtomatik ravishda professional
        16:9 (YouTube standarti) formatga keltirib, o'rtasidan kesadi va WEBP qiladi.
        """
        # Rasmni oqim ko'rinishida Pillow yordamida ochamiz
        img = Image.open(self.thumbnail)
        
        # Agar rasm shaffoflikka ega bo'lsa (RGBA yoki P format), RGB ga o'giramiz (WEBP xatosiz saqlashi uchun)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # 1. AVTOMATIK 16:9 PROPÒRSIYA BO'YICHA O'RTASIDAN KESISH (CROP) MANTIQI
        target_ratio = 16 / 9
        orig_width, orig_height = img.size
        orig_ratio = orig_width / orig_height

        if orig_ratio > target_ratio:
            # Rasm haddan tashqari keng (Panoramma) bo'lsa, ikki chetidan teng kesiladi
            new_width = int(target_ratio * orig_height)
            left = (orig_width - new_width) / 2
            top = 0
            right = left + new_width
            bottom = orig_height
            img = img.crop((left, top, right, bottom))
        elif orig_ratio < target_ratio:
            # Rasm tikka (Portret/Kvadrat) bo'lsa, tepasi va pastidan teng kesiladi
            new_height = int(orig_width / target_ratio)
            left = 0
            top = (orig_height - new_height) / 2
            right = orig_width
            bottom = top + new_height
            img = img.crop((left, top, right, bottom))

        # 2. O'LCHAMNI EXACTLY 1280x720 PIKSELGA KELTIRISH (YouTube 720p HD standarti)
        img = img.resize((1280, 720), Image.Resampling.LANCZOS)
        
        # 3. WEBP FORMATIDA XOTIRANING O'ZIDA SIQIB SAQLASH
        buffer = BytesIO()
        # quality=85 inson ko'zi ilg'ay olmaydigan darajada sifatni saqlaydi, lekin og'irlikni 85-90% gacha kamaytiradi
        img.save(buffer, format="WEBP", quality=85)
        buffer.seek(0)
        
        # Fayl nomining kengaytmasini o'zgartiramiz (.webp qilamiz)
        base_name = os.path.splitext(self.thumbnail.name)[0]
        new_name = f"{base_name}.webp"
        
        # Siqilgan rasmni model maydoniga qayta joylaymiz
        # save=False qilinadi, chunki AWS S3 ga ortiqcha xom fayl yuklanmasligi kerak, oxirida super().save() barchasini bittada yuboradi
        self.thumbnail.save(new_name, ContentFile(buffer.read()), save=False)