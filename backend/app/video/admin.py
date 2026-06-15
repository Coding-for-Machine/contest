from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import display
from .models import Video


@admin.register(Video)
class VideoAdmin(ModelAdmin):
    list_display = ["title", "duration_display", "display_image", "hls_url_status"]
    search_fields = ["title", "description", "slug"]
    
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }

    readonly_fields = ["slug", "duration", "thumbnail", "hls_url", "mp4_url"]

    fieldsets = (
        ("📌 Asosiy Ma'lumotlar", {
            "fields": ("title", "description")
        }),
        ("📂 Media Yuklash", {
            "fields": ("video", "image", "backdrop_image"),
        }),
        ("🌐 Tashqi Linklar (Agar qo'lda kiritilsa)", {
            "fields": ("backdrop",),
        }),
        ("⚙️ Avtomat To'ldirilgan Ma'lumotlar", {
            "fields": ("slug", "duration", "thumbnail", "hls_url", "mp4_url"),
        }),
    )

    @display(description="Poster")
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 35px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "Rasm yo'q"

    @display(description="Davomiyligi")
    def duration_display(self, obj):
        return obj.duration if obj.duration else "⏱ Hisoblanmoqda..."

    @display(description="Streaming")
    def hls_url_status(self, obj):
        if obj.hls_url:
            return format_html('<span style="color: #10B981; font-weight: bold;">✅ Tayyor</span>')
        return format_html('<span style="color: #F59E0B; font-weight: bold;">⏳ Navbatda</span>')
