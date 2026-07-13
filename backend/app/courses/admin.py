# courses/admin.py
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count
from django.utils.timezone import now, timedelta
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from mdeditor.fields import MDEditorWidget
import json

from .models import Course, Lecture, Modul, Lesson, Enrollment
from baseuser.utils.admin import BaseOwnerAdmin, BaseOwnerInline


# ============================================================
# INLINES
# ============================================================

class LessonInline(BaseOwnerInline):
    model = Lesson
    extra = 1
    fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    tab = True
    classes = ('collapse',)


class ModulInline(BaseOwnerInline):
    model = Modul
    extra = 1
    fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    tab = True
    classes = ('collapse',)


# ============================================================
# COURSE ADMIN
# ============================================================

@admin.register(Course)
class CourseAdmin(BaseOwnerAdmin):
    list_display = (
        'display_header',
        'display_price',
        'display_stats',
        'is_active',
        'display_image',
    )
    list_filter = ('is_active', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('title', 'description', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 25
    ordering = ('-created_at',)
    inlines = [ModulInline]

    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }

    fieldsets = (
        ("📌 Asosiy ma'lumotlar", {
            'fields': (('title', 'slug'), 'description', 'is_active'),
        }),
        ("💰 Narx va Chegirmalar", {
            'fields': (('price', 'discount_price'),),
            'description': "Kurs narxi va chegirmasini shu yerda boshqaring.",
        }),
        ("🎬 Media", {
            'fields': ('intro_video',),
        }),
        ("📊 Statistika", {
            'fields': ('total_lessons_count', 'total_test_count'),
            'classes': ('collapse',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('total_lessons_count', 'total_test_count')

    # ── Display metodlar ──────────────────────────────────────

    @display(description="Kurs nomi", header=True)
    def display_header(self, obj):
        return [obj.title, f"ID: #{obj.id}"]

    @display(description="Narxi", label=True)
    def display_price(self, obj):
        if obj.discount_price and obj.discount_price < obj.price:
            return format_html(
                '<span style="text-decoration:line-through;color:#94a3b8;font-size:13px;">{} UZS</span> '
                '<span style="color:#22c55e;font-weight:700;font-size:16px;">{} UZS</span>',
                f"{obj.price:,.0f}", f"{obj.discount_price:,.0f}"
            )
        return format_html(
            '<span style="color:#3b82f6;font-weight:600;">{} UZS</span>',
            f"{obj.price:,.0f}"
        )

    @display(description="Statistika")
    def display_stats(self, obj):
        modul_count = obj.modullar.count()
        student_count = obj.enrollments.count()
        return format_html(
            '<div style="display:flex;gap:12px;font-size:13px;">'
            '<span>📚 {} ta modul</span>'
            '<span>👥 {} ta o\'quvchi</span>'
            '</div>',
            modul_count, student_count
        )

    @display(description="Muqova")
    def display_image(self, obj):
        if hasattr(obj, 'image') and obj.image:
            return format_html(
                '<img src="{}" style="width:60px;height:40px;object-fit:cover;'
                'border-radius:6px;border:1px solid #e2e8f0;" />',
                obj.image.url
            )
        return format_html('<span style="color:#94a3b8;font-size:12px;">📷 Yo\'q</span>')

    # ── Changelist ────────────────────────────────────────────

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({
            'total_courses':    Course.objects.count(),
            'active_courses':   Course.objects.filter(is_active=True).count(),
            'inactive_courses': Course.objects.filter(is_active=False).count(),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# MODUL ADMIN
# ============================================================

@admin.register(Modul)
class ModulAdmin(BaseOwnerAdmin):
    list_display = (
        'title_display',
        'course_display',
        'lessons_count_display',
        'created_at_formatted',
    )
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    list_per_page = 25
    ordering = ('-created_at',)
    inlines = [LessonInline]
    prepopulated_fields = {'slug': ('title',)}

    fieldsets = (
        ("📚 Modul Ma'lumotlari", {
            'fields': (('title', 'slug'), 'course'),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "course":
            if not request.user.is_superuser:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(owner=request.user)
            else:
                kwargs["queryset"] = db_field.remote_field.model.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @display(description="Modul nomi", header=True)
    def title_display(self, obj):
        return [obj.title, f"ID: #{obj.id}"]

    @display(description="Kurs")
    def course_display(self, obj):
        return format_html(
            '<a href="/admin/courses/course/{}/change/" style="color:#3b82f6;text-decoration:none;">'
            '📘 {}</a>',
            obj.course.id, obj.course.title[:40]
        )

    @display(description="Darslar")
    def lessons_count_display(self, obj):
        count = obj.lessons.count()
        return format_html(
            '<span style="background:#3b82f6;color:white;padding:2px 12px;'
            'border-radius:20px;font-size:12px;">📝 {}</span>',
            count
        )

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({
            'total_modules': Modul.objects.count(),
            'total_lessons': Lesson.objects.count(),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# LESSON ADMIN
# ============================================================

@admin.register(Lesson)
class LessonAdmin(BaseOwnerAdmin):
    list_display = (
        'title_display',
        'modul_display',
        'total_tasks_count',
        'owner_display',
    )
    list_filter = ('modul__course', 'modul')
    search_fields = ('title', 'modul__title', 'modul__course__title')
    list_per_page = 30
    ordering = ('-id',)
    prepopulated_fields = {'slug': ('title',)}

    # 🔒 KALIT QADAM: Editable=False bo'lgan maydonni readonly ro'yxatiga olamiz
    readonly_fields = ('total_tasks_count',)

    fieldsets = (
        ("📝 Dars Ma'lumotlari", {
            'fields': (('title', 'slug'), 'modul'),
        }),
        ("📊 Statistika", {
            'fields': ('total_tasks_count',),  # Endi bu yerda xato bermaydi!
            'classes': ('collapse',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "modul":
            if not request.user.is_superuser:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(course__owner=request.user)
            else:
                kwargs["queryset"] = db_field.remote_field.model.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @display(description="Dars nomi", header=True)
    def title_display(self, obj):
        return [obj.title, f"ID: #{obj.id}"]

    @display(description="Modul")
    def modul_display(self, obj):
        return format_html(
            '<span style="display:flex;flex-direction:column;">'
            '<span style="font-weight:500;">📚 {}</span>'
            '<span style="font-size:11px;color:#94a3b8;">📘 {}</span>'
            '</span>',
            obj.modul.title[:30],
            obj.modul.course.title[:30]
        )

    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


# LECTURE ADMIN
@admin.register(Lecture)
class LectureAdmin(BaseOwnerAdmin):
    list_display = (
        'title_display',
        'lesson_link',
        'display_type_badge',
        'xp_badge',
        'order_badge',
        'updated_at_formatted',
    )
    list_filter = ('lesson__modul__course', 'lesson', 'created_at')
    search_fields = ('title', 'body', 'lesson__title')
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 40
    ordering = ('lesson', 'order', '-id')

    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }

    fieldsets = (
        ("📌 Asosiy ma'lumotlar", {
            'fields': (('lesson', 'order'), ('title', 'slug')),
        }),
        ("🏆 Mukofot tizimi", {
            'fields': ('xp',),
            'description': "Ushbu ma'ruza muvaffaqiyatli yakunlanganda foydalanuvchiga beriladigan tajriba (XP) ochkosi.",
        }),
        ("🎥 Video darslik integratsiyasi", {
            'fields': ('video',),
            'description': "Agar ushbu bob videoli dars bo'lsa, tegishli videoni biriktiring.",
        }),
        ("📖 Nazariy Konspekt (Markdown)", {
            'fields': ('body',),
            'description': "Ma'ruza matnini, kod namunalarini va qoidalarni Markdown formatida yozing.",
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    # ✅ owner ni avtomatik o'rnatish
    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

    @display(description="Ma'ruza / Video nomi", header=True)
    def title_display(self, obj):
        return [obj.title, f"Slug: /{obj.slug}"]

    @display(description="Tegishli Darslik")
    def lesson_link(self, obj):
        if obj.lesson:
            return format_html(
                '<a href="/admin/courses/lesson/{}/change/" style="color:#10b981;font-weight:500;">📝 {}</a>',
                obj.lesson.id, obj.lesson.title[:30]
            )
        return "—"

    @display(description="Blok Turi")
    def display_type_badge(self, obj):
        if obj.video and obj.body:
            return format_html(
                '<span style="background:#dcfce7;color:#15803d;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">'
                '🎥 Video + 📄 Matn</span>'
            )
        elif obj.video:
            return format_html(
                '<span style="background:#eff6ff;color:#1d4ed8;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">'
                '🎥 Faqat Video</span>'
            )
        return format_html(
            '<span style="background:#f3f4f6;color:#374151;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">'
            '📄 Faqat Matn</span>'
        )

    @display(description="Mukofot XP")  # ✅ Yangi: Rangli chiroyli XP ko'rinishi
    def xp_badge(self, obj):
        # XP miqdoriga qarab rangni o'zgartirish (ko'proq XP beradigan darslar yorqinroq ko'rinadi)
        bg_color = "#fef3c7" if obj.xp < 30 else ("#ffedd5" if obj.xp < 70 else "#fee2e2")
        text_color = "#b45309" if obj.xp < 30 else ("#c2410c" if obj.xp < 70 else "#b91c1c")
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px;">'
            '+{} XP</span>',
            bg_color, text_color, obj.xp
        )

    @display(description="Tartibi")
    def order_badge(self, obj):
        return format_html('<b style="color:#475569;">#{}</b>', obj.order)

    @display(description="Oxirgi yangilanish")
    def updated_at_formatted(self, obj):
        return obj.updated_at.strftime("%d-%m-%Y %H:%M") if obj.updated_at else "—"

# ============================================================
# ENROLLMENT ADMIN (owner yo'q → ModelAdmin)
# ============================================================

@admin.register(Enrollment)
class EnrollmentAdmin(ModelAdmin):  # ✅ unfold.admin.ModelAdmin
    list_display = (
        'user_display',
        'course_display',
        'payment_status',
        'progress_display',
        'created_at_formatted',
    )
    list_filter = ('is_paid', 'is_completed', 'course', 'created_at')
    search_fields = ('user__username', 'user__full_name', 'course__title')
    list_per_page = 30
    ordering = ('-created_at',)
    autocomplete_fields = ('user', 'course')

    fieldsets = (
        ("👤 Foydalanuvchi va Kurs", {
            'fields': (('user', 'course'),),
        }),
        ("💰 To'lov", {
            'fields': ('is_paid',),
        }),
        ("📊 Progress", {
            'fields': (('finished_darslar_soni', 'finished_test_soni'), 'is_completed', 'completed_at'),
        }),
        ("📅 Vaqt", {
            'fields': (('created_at', 'updated_at'),),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'completed_at')

    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return [name, f"Telegram: @{obj.user.username or 'mavjud emas'}"]

    @display(description="Kurs")
    def course_display(self, obj):
        return format_html(
            '<a href="/admin/courses/course/{}/change/" style="color:#3b82f6;text-decoration:none;">'
            '📘 {}</a>',
            obj.course.id, obj.course.title[:40]
        )

    @display(description="To'lov", label={True: "success", False: "danger"})
    def payment_status(self, obj):
        if obj.is_paid:
            return mark_safe(
                '<span style="background:#22c55e;color:white;padding:2px 12px;'
                'border-radius:20px;font-size:12px;">✅ To\'langan</span>'
            )
        return mark_safe(
            '<span style="background:#f59e0b;color:white;padding:2px 12px;'
            'border-radius:20px;font-size:12px;">⏳ Kutilmoqda</span>'
        )

    @display(description="Progress")
    def progress_display(self, obj):
        total = obj.course.total_lessons_count or 1
        pct = int((obj.finished_darslar_soni / total) * 100) if total > 0 else 0
        color = '#22c55e' if pct >= 80 else '#f59e0b' if pct >= 50 else '#3b82f6'
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:100px;height:6px;background:#f1f5f9;border-radius:10px;overflow:hidden;">'
            '<div style="width:{}%;height:100%;background:{};border-radius:10px;"></div>'
            '</div>'
            '<span style="font-size:12px;font-weight:600;color:{};">{}%</span>'
            '</div>',
            pct, color, color, pct
        )

    @display(description="Yozilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        last_7_days = [now().date() - timedelta(days=i) for i in range(6, -1, -1)]
        labels = [d.strftime("%d-%b") for d in last_7_days]
        counts = [Enrollment.objects.filter(created_at__date=d).count() for d in last_7_days]

        course_data = Enrollment.objects.values('course__title').annotate(total=Count('id'))

        extra_context.update({
            "main_chart": json.dumps({
                "labels": labels,
                "datasets": [{
                    "label": "Kunlik yozilishlar",
                    "data": counts,
                    "borderColor": "#4f46e5",
                    "backgroundColor": "rgba(79,70,229,0.1)",
                    "fill": True,
                    "tension": 0.4,
                }]
            }),
            "pie_chart": json.dumps({
                "labels": [c['course__title'][:20] for c in course_data],
                "datasets": [{
                    "data": [c['total'] for c in course_data],
                    "backgroundColor": ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"],
                }]
            }),
            "total_enrollments":     Enrollment.objects.count(),
            "paid_enrollments":      Enrollment.objects.filter(is_paid=True).count(),
            "completed_enrollments": Enrollment.objects.filter(is_completed=True).count(),
        })
        return super().changelist_view(request, extra_context=extra_context)