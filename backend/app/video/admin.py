from django.contrib import admin
from django.db import models # Bu shart!
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget
from .models import Video

@admin.register(Video)
class VideoAdmin(ModelAdmin):
    # Ro'yxatda ko'rinadigan ustunlar
    list_display = [
        "title", 
        "problem", 
        "duration", 
        "display_image",  # Rasmni kichik preview qilish
        "hls_url_status"  # HLS bormi yoki yo'qmi tekshirish
    ]
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
    }

    
    # Qidiruv maydonlari
    search_fields = ["title", "description", "slug"]
    
    # Filtrlar (o'ng tomonda)
    list_filter = ["problem", "duration"]
    
    # Avtomatik slug yaratish (admin panelda yozayotganda)
    prepopulated_fields = {"slug": ("title",)}
    
    # Ma'lumotlarni guruhlash (Fieldsets)
    fieldsets = (
        ("Asosiy Ma'lumotlar", {
            "fields": ("title", "slug", "problem", "description", "duration")
        }),
        ("Media Fayllar (Yuklash)", {
            "fields": ("image", "backdrop_image", "video"),
            "classes": ["tab"], # Unfold uchun maxsus klass
        }),
        ("Tashqi Linklar (URL)", {
            "fields": ("thumbnail", "backdrop", "hls_url", "mp4_url"),
        }),
    )

    # Rasmni admin panelda ko'rsatish uchun funksiya
    def display_image(self, obj):
        if obj.image:
            from django.utils.html import format_html
            # Bu yerda ikkinchi argument (obj.image.url) bor, shuning uchun bu qism to'g'ri
            return format_html('<img src="{}" style="width: 50px; height: auto; border-radius: 4px;" />', obj.image.url)
        return "Rasm yo'q"
    display_image.short_description = "Poster"

    # HLS statusini rangli ko'rsatish
    def hls_url_status(self, obj):
        from django.utils.html import format_html
        if obj.hls_url:
            # TO'G'IRLANDI: Matnni argument sifatida uzatish shart
            return format_html('<span style="color: green;">{}</span>', "✅ Tayyor")
        # TO'G'IRLANDI: Matnni argument sifatida uzatish shart
        return format_html('<span style="color: red;">{}</span>', "❌ Yo'q")
    hls_url_status.short_description = "Streaming"


    # Tahrirlashda osonroq tanlash uchun
    autocomplete_fields = ["problem"] 
