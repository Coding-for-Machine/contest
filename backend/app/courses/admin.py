from django.contrib import admin
from django.db import models
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import display
from .models import Course, Modul, Enrilliment, Lesson
from django.utils.timezone import now, timedelta
import json

# 🔹 Darslarni Modul ichida ko'rsatish
class LessonInline(TabularInline):
    model = Lesson
    extra = 1
    fields = ('order', 'title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    tab = True

# 🔹 Modulni Kurs ichida ko‘rsatish
class ModulInline(TabularInline):
    model = Modul
    extra = 1
    fields = ('order', 'title')
    tab = True

from django.db.models import Count, Sum
from unfold.admin import ModelAdmin, TabularInline
from django.utils.html import format_html

@admin.register(Course)
class KursAdmin(ModelAdmin):
    # ✅ Ro'yxatda muhim ma'lumotlarni ko'rsatish
    list_display = (
        'display_header', 
        'display_price',      # Narxni chiroyli chiqarish
        'display_stats',      # O'quvchilar va modullar soni
        'is_active', 
        'display_image'
    )
    
    list_filter = ('is_active', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    
    # ✅ Modullarni kurs ichida boshqarish
    inlines = [ModulInline]

    # ✅ WYSIWYG va boshqa UI sozlamalari
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }

    # ✅ Fieldsetlarni mantiqiy guruhlash
    fieldsets = (
        ("📌 Asosiy ma’lumotlar", {
            'fields': (('title', 'slug'), 'description', 'is_active'),
            'classes': ('tab',), 
        }),
        ("💰 Narx va Chegirmalar", {
            'fields': (('price', 'discount_price'),),
            'description': "Kurs narxi va chegirmasini shu yerda boshqaring.",
        }),
        ("🖼 Media", {
            'fields': ('image',),
        }),
    )

    # 1️⃣ Kurs nomi va ID (Unfold Header)
    @display(description="Kurs nomi", header=True)
    def display_header(self, obj):
        return [obj.title, f"Sarlavha: {obj.title[:30]}..."]

    # 2️⃣ Narxni chiroyli formatda chiqarish
    @display(description="Narxi", label=True)
    def display_price(self, obj):
        if obj.discount_price:
            return f"{obj.discount_price:,} UZS"
        return f"{obj.price:,} UZS"

    # 3️⃣ Dinamik statistika (O'quvchilar va Modullar soni)
    @display(description="Statistika")
    def display_stats(self, obj):
        modul_count = obj.modullar.count()
        student_count = obj.kursga_yozilishlar.count()
        return [f"📚 {modul_count} ta modul", f"👥 {student_count} ta o'quvchi"]

    # 4️⃣ Rasm preview (yaxshilangan)
    @display(description="Muqova")
    def display_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 60px; height: 40px; object-fit: cover; '
                'border: 2px solid #e5e7eb; border-radius: 6px;" />', 
                obj.image.url
            )
        return "Rasm yo'q"

    # ✅ Bazadan ma'lumotni optimallashtirib olish (Select Related)
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            modul_cnt=Count('modullar', distinct=True),
            student_cnt=Count('kursga_yozilishlar', distinct=True)
        )


@admin.register(Modul)
class ModulAdmin(ModelAdmin):
    list_display = ('order', 'title', 'course', 'lessons_count')
    list_display_links = ('title',) 
    list_filter = ('course',)
    list_editable = ('order',)
    search_fields = ('title', 'course__title')
    inlines = [LessonInline]

    @display(description="Darslar soni")
    def lessons_count(self, obj):
        return f"{obj.lesson.count()} ta dars"


@admin.register(Enrilliment)
class EnrillimentAdmin(ModelAdmin):
    change_list_template = "admin/enrilliment_changelist.html" # Maxsus template
    list_display = ('user_display', 'course', 'is_paid_status', 'created_at')
    list_filter = ('is_paid', 'course', 'created_at')
    
    @display(description="To'lov", label={True: "success", False: "danger"})
    def is_paid_status(self, obj):
        return "Muvaffaqiyatli" if obj.is_paid else "Kutilmoqda"

    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        return [obj.user.full_name or "Ismsiz", f"ID: {obj.user.telegram_id}"]

    def changelist_view(self, request, extra_context=None):
        # 1. So'nggi 7 kunlik yozilishlar (Line Chart)
        last_7_days = [now().date() - timedelta(days=i) for i in range(6, -1, -1)]
        labels = [d.strftime("%d-%b") for d in last_7_days]
        
        counts = []
        for day in last_7_days:
            count = Enrilliment.objects.filter(created_at__date=day).count()
            counts.append(count)

        # 2. Kurslar bo'yicha o'quvchilar taqsimoti (Pie Chart)
        course_data = Enrilliment.objects.values('course__title').annotate(total=models.Count('id'))
        course_labels = [c['course__title'] for c in course_data]
        course_counts = [c['total'] for c in course_data]

        extra_context = extra_context or {}
        extra_context["main_chart"] = json.dumps({
            "labels": labels,
            "datasets": [{
                "label": "Kunlik yozilishlar",
                "data": counts,
                "borderColor": "#4f46e5",
                "backgroundColor": "rgba(79, 70, 229, 0.1)",
                "fill": True,
                "tension": 0.4
            }]
        })
        
        extra_context["pie_chart"] = json.dumps({
            "labels": course_labels,
            "datasets": [{
                "data": course_counts,
                "backgroundColor": ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"]
            }]
        })
        
        # 3. Mini statistika kartalari
        extra_context["total_revenue"] = Enrilliment.objects.filter(is_paid=True).count() # Soni
        extra_context["active_courses"] = Course.objects.filter(is_active=True).count()

        return super().changelist_view(request, extra_context=extra_context)

# Lesson uchun ham alohida admin (ixtiyoriy)
@admin.register(Lesson)
class LessonAdmin(ModelAdmin):
    list_display = ('title', 'modul', 'order')
    list_filter = ('modul__course', 'modul')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
