# admin.py
from django.contrib import admin
from django.db import models
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.forms.widgets import WysiwygWidget  # Django Unfold vizual muharriri
from .models import Contest, ContestRegistration


class ContestRegistrationInline(TabularInline):
    model = ContestRegistration
    extra = 0  # Bo'sh qo'shimcha qator ko'rsatmaslik
    autocomplete_fields = ["user"]
    fields = ["user", "total_score", "rank", "is_active"]
    tab = True


@admin.register(Contest)
class ContestAdmin(ModelAdmin):
    # Ro'yxat ko'rinishi (List View)
    list_display = [
        "title", 
        "status", 
        "type", 
        "difficulty", 
        "start_time", 
        "end_time",  # Ro'yxatda tugash vaqti ham ko'rinadi
        "is_featured"
    ]
    list_filter = ["status", "type", "difficulty", "is_featured"]
    search_fields = ["title", "description"]
    list_editable = ["status", "is_featured"]

    # ✅ Faqat kerakli maydon (description) uchun WysiwygWidget'ni sozlash
    # Bu orqali rasmda ko'ringan input torayib qolishi butunlay hal qilinadi
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "description":
            kwargs["widget"] = WysiwygWidget(
                attrs={
                    "class": "w-full min-h-[320px]",  # Tailwind orqali 100% kenglik va balandlik beriladi
                    "placeholder": "Tanlov tavsifini batafsil, rasm yoki havolalar bilan kiriting..."
                }
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    # ✅ Inputlar ostiga dinamik ravishda Timezone eslatmasini qo'shish
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # settings.py dagi joriy vaqt zonasi nomini oladi (masalan: Asia/Tashkent)
        current_tz = timezone.get_current_timezone_name()
        
        form.base_fields['start_time'].help_text = f"Musobaqa boshlanishini joriy [{current_tz}] vaqti bilan kiriting."
        form.base_fields['end_time'].help_text = f"Musobaqa tugashini joriy [{current_tz}] vaqti bilan kiriting."
        return form

    # Inline ulanishi
    inlines = [ContestRegistrationInline]

    # Ma'lumotlarni guruhlash (Layout)
    fieldsets = (
        ("📌 Asosiy Ma'lumotlar", {
            "fields": (
                ("title", "category"),  # Bular yonma-yon parallel qatorda
                "description",          # 🚀 MUHIM: Qavssiz yozildi, ekranda to'liq kenglikni egallaydi
                "is_featured",
            )
        }),
        ("⏰ Vaqt va Davomiylik", {
            "fields": (
                "start_time",  # 🚀 TO'G'RILANDI: Alohida qatorda (Nomi aniq chiqadi)
                "end_time",    # 🚀 TO'G'RILANDI: Alohida qatorda (Nomi aniq chiqadi)
                "duration",
            ),
        }),
        ("⚙️ Sozlamalar va Kirish", {
            "fields": (
                ("type", "status", "difficulty"),
                ("max_participants", "access_key"),
            ),
        }),
        ("🏆 Mukofotlar va Sovg'alar", {
            "fields": ("prizes",), 
            "classes": ["collapse"],  # Standart holatda yopiq turadi
        }),
    )


# Ro'yxatdan o'tishlar uchun alohida admin
@admin.register(ContestRegistration)
class ContestRegistrationAdmin(ModelAdmin):
    list_display = ["user", "contest", "total_score", "rank", "is_active"]
    search_fields = ["user__username", "contest__title"]
    list_filter = ["contest", "is_active"]
    autocomplete_fields = ["user", "contest"]
