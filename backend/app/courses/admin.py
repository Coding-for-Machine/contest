# courses/admin.py
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from django.utils.timezone import now, timedelta
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from mdeditor.fields import MDEditorWidget
from mdeditor.fields import MDTextField
import json
from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import (
    Course, Modul, Lesson, Enrollment,
    Lecture, CourseTest, CourseQuestion, CourseChoice,
    CourseTestSession, CourseUserResponse,
    MatchingPair, ArrangeItem, Blank, BlankAnswer,
)
from baseuser.utils.admin import BaseOwnerAdmin, BaseOwnerInline


# ============================================================
# INLINES
# ============================================================

class LessonInline(BaseOwnerInline):
    model = Lesson
    extra = 1
    fields = ('title', 'slug', 'order', 'is_active')
    prepopulated_fields = {'slug': ('title',)}
    tab = True
    classes = ('collapse',)


class ModulInline(BaseOwnerInline):
    model = Modul
    extra = 1
    fields = ('title', 'slug', 'order', 'is_active')
    prepopulated_fields = {'slug': ('title',)}
    tab = True
    classes = ('collapse',)


class LectureInline(BaseOwnerInline):
    model = Lecture
    extra = 1
    fields = ('title', 'slug', 'order', 'xp', 'video')
    prepopulated_fields = {'slug': ('title',)}
    tab = True
    classes = ('collapse',)


# --- Test tizimi uchun ---

class CourseChoiceInline(TabularInline):
    model = CourseChoice
    extra = 1
    fields = ('text', 'is_correct', 'owner')
    classes = ('collapse',)


class CourseQuestionInline(TabularInline):
    model = CourseQuestion
    extra = 1
    fields = (
        'text', 'question_type', 'difficulty', 'xp',
        'lesson', 'explanation_video', 'owner',
    )
    classes = ('collapse',)


class CourseUserResponseInline(TabularInline):
    model = CourseUserResponse
    extra = 0
    fields = ('question', 'choice', 'answer_data', 'is_correct', 'created_at')
    readonly_fields = ('question', 'choice', 'answer_data', 'is_correct', 'created_at')
    classes = ('collapse',)


# --- Yangi savol turlari uchun inlinelar ---

class MatchingPairInline(TabularInline):
    model = MatchingPair
    extra = 1
    fields = ('left', 'right', 'order')
    classes = ('collapse',)


class ArrangeItemInline(TabularInline):
    model = ArrangeItem
    extra = 1
    fields = ('text', 'correct_position')
    classes = ('collapse',)


class BlankAnswerInline(TabularInline):
    model = BlankAnswer
    extra = 1
    fields = ('answer',)
    classes = ('collapse',)


class BlankInline(TabularInline):
    model = Blank
    extra = 1
    fields = ('position', 'case_sensitive')
    classes = ('collapse',)


# ============================================================
# COURSE ADMIN
# ============================================================

@admin.register(Course)
class CourseAdmin(BaseOwnerAdmin):
    list_display = (
        'display_header',
        'center_display',
        'display_price',
        'display_stats',
        'is_active',
        'display_image',
    )
    list_filter = ('is_active', 'level', 'center', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('title', 'description', 'slug', 'owner__username', 'center__name')
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 25
    ordering = ('-created_at',)
    inlines = [ModulInline]
    autocomplete_fields = ('intro_video',)

    formfield_overrides = {
        MDTextField: {"widget": MDEditorWidget},
    }

    fieldsets = (
        ("📌 Asosiy ma'lumotlar", {
            'fields': (('title', 'slug'), 'description', 'level', 'is_active'),
        }),
        ("🏢 Markaz", {
            'fields': ('center',),
            'description': (
                "Ushbu kurs qaysi o'quv markaziga tegishli ekanligini tanlang. "
                "Agar hisobingiz faqat bitta markazga bog'langan bo'lsa, bu maydon "
                "avtomatik to'ldiriladi va yashiriladi."
            ),
        }),
        ("💰 Narx va Chegirmalar", {
            'fields': (('price', 'discount_price'),),
            'description': "Kurs narxi va chegirmasini shu yerda boshqaring.",
        }),
        ("🎬 Media", {
            'fields': ('intro_video',),
        }),
        ("📊 Statistika", {
            'fields': ('total_modules_count', 'total_lessons_count', 'total_test_count'),
            'classes': ('collapse',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('total_modules_count', 'total_lessons_count', 'total_test_count')

    @display(description="Kurs nomi", header=True)
    def display_header(self, obj):
        return [obj.title, f"ID: #{obj.id}"]

    @display(description="Markaz")
    def center_display(self, obj):
        if obj.center_id:
            return format_html(
                '<span style="background:#eef2ff;color:#4338ca;padding:2px 10px;'
                'border-radius:12px;font-size:12px;font-weight:600;">🏢 {}</span>',
                obj.center.name
            )
        return format_html(
            '<span style="background:#fee2e2;color:#b91c1c;padding:2px 10px;'
            'border-radius:12px;font-size:12px;font-weight:600;">⚠️ Markaz yo\'q</span>'
        )

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

    @display(description="Rasm")
    def display_image(self, obj):
        return format_html(
            '<span style="color:#94a3b8;font-size:12px;background:#f1f5f9;'
            'padding:4px 10px;border-radius:4px;">📷 Rasm yo\'q</span>'
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)
        extra_context.update({
            'total_courses':    qs.count(),
            'active_courses':   qs.filter(is_active=True).count(),
            'inactive_courses': qs.filter(is_active=False).count(),
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
        'is_active',
        'created_at_formatted',
    )
    list_filter = ('course', 'is_active')
    search_fields = ('title', 'course__title', 'owner__username')
    list_per_page = 25
    ordering = ('course', 'order', 'id')
    inlines = [LessonInline]
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('course',)

    fieldsets = (
        ("📚 Modul Ma'lumotlari", {
            'fields': (('title', 'slug'), 'course', 'order', 'is_active'),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "course":
            if not request.user.is_superuser:
                center, is_cross = self._get_center_scope(request)
                qs = db_field.remote_field.model.objects.all()
                if not is_cross and center:
                    qs = qs.filter(center=center)
                kwargs["queryset"] = qs.filter(owner=request.user) if self._get_record_scope(request) == 'owner' else qs
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
        qs = self.get_queryset(request)
        extra_context.update({
            'total_modules': qs.count(),
            'total_lessons': Lesson.objects.filter(modul__in=qs).count(),
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
        'is_active',
        'estimated_minutes',
        'owner_display',
    )
    list_filter = ('modul__course', 'modul', 'is_active')
    search_fields = ('title', 'modul__title', 'modul__course__title', 'owner__username')
    list_per_page = 30
    ordering = ('modul', 'order', 'id')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('modul',)

    readonly_fields = ('total_tasks_count',)

    fieldsets = (
        ("📝 Dars Ma'lumotlari", {
            'fields': (('title', 'slug'), 'modul', 'order', 'is_active'),
        }),
        ("⏱️ Vaqt", {
            'fields': ('estimated_minutes',),
        }),
        ("📊 Statistika", {
            'fields': ('total_tasks_count',),
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
                center, is_cross = self._get_center_scope(request)
                qs = db_field.remote_field.model.objects.all()
                if not is_cross and center:
                    qs = qs.filter(course__center=center)
                kwargs["queryset"] = qs
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
        if not change and not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


# ============================================================
# LECTURE ADMIN
# ============================================================

@admin.register(Lecture)
class LectureAdmin(BaseOwnerAdmin):
    list_display = (
        'title_display',
        'lesson_link',
        'display_type_badge',
        'xp_badge',
        'order_badge',
        'reading_time',
        'updated_at_formatted',
    )
    list_filter = ('lesson__modul__course', 'lesson', 'created_at')
    search_fields = ('title', 'body', 'lesson__title', 'owner__username')
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 40
    ordering = ('lesson', 'order', 'id')
    autocomplete_fields = ('lesson', 'video')

    formfield_overrides = {
        MDTextField: {"widget": MDEditorWidget},
    }

    fieldsets = (
        ("📌 Asosiy ma'lumotlar", {
            'fields': (('lesson', 'order'), ('title', 'slug')),
        }),
        ("🏆 Mukofot tizimi", {
            'fields': ('xp',),
            'description': "Ushbu ma'ruza muvaffaqiyatli yakunlanganda foydalanuvchiga beriladigan tajriba (XP) ochkosi.",
        }),
        ("⏱️ Vaqt", {
            'fields': ('reading_time',),
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

    def save_model(self, request, obj, form, change):
        if not change and not obj.owner_id:
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

    @display(description="Mukofot XP")
    def xp_badge(self, obj):
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

    @display(description="O'qish vaqti")
    def reading_time(self, obj):
        return format_html('<span style="color:#64748b;">{} daq</span>', obj.reading_time)

    @display(description="Oxirgi yangilanish")
    def updated_at_formatted(self, obj):
        return obj.updated_at.strftime("%d-%m-%Y %H:%M") if obj.updated_at else "—"


# ============================================================
# ENROLLMENT ADMIN
# ============================================================

@admin.register(Enrollment)
class EnrollmentAdmin(ModelAdmin):
    list_display = (
        'user_display',
        'course_display',
        'payment_status',
        'progress_display',
        'created_at_formatted',
    )
    list_filter = ('is_paid', 'course', 'created_at')
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
        ("📅 Vaqt", {
            'fields': (('created_at', 'updated_at'),),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.id}"
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
        pct = 100 if obj.is_paid else 0
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
        qs = self.get_queryset(request)

        last_7_days = [now().date() - timedelta(days=i) for i in range(6, -1, -1)]
        labels = [d.strftime("%d-%b") for d in last_7_days]
        counts = [qs.filter(created_at__date=d).count() for d in last_7_days]

        course_data = qs.values('course__title').annotate(total=Count('id'))

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
            "total_enrollments": qs.count(),
            "paid_enrollments":  qs.filter(is_paid=True).count(),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# COURSE TEST ADMIN
# ============================================================

@admin.register(CourseTest)
class CourseTestAdmin(BaseOwnerAdmin):
    list_display = (
        'title_display',
        'modul_link',
        'duration_badge',
        'question_count_display',
        'pass_rate_display',
        'is_active',
        'penalty_display',
    )
    list_filter = ('is_active', 'modul__course', 'created_at')
    search_fields = ('title', 'description', 'modul__title', 'modul__course__title', 'owner__username')
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 25
    ordering = ('-id', 'created_at')
    inlines = [CourseQuestionInline]
    autocomplete_fields = ('modul', 'intro_video')

    formfield_overrides = {
        MDTextField: {"widget": MDEditorWidget},
    }

    fieldsets = (
        ("📋 Test ma'lumotlari", {
            'fields': (('title', 'slug'), 'modul', 'description', 'is_active'),
        }),
        ("⏱️ Vaqt va O'tish mezoni", {
            'fields': (('duration', 'min_pass_percentage'),),
        }),
        ("🎯 Ballar tizimi", {
            'fields': ('penalty_coefficient', 'max_lifelines'),
            'description': "Noto'g'ri javoblar uchun jarima koeffitsiyenti va yordam (Lifeline) soni.",
        }),
        ("🎬 Media", {
            'fields': ('intro_video',),
            'classes': ('collapse',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    @display(description="Test nomi", header=True)
    def title_display(self, obj):
        return [obj.title, f"ID: #{obj.id}"]

    @display(description="Modul")
    def modul_link(self, obj):
        if obj.modul:
            return format_html(
                '<a href="/admin/courses/modul/{}/change/" style="color:#8b5cf6;text-decoration:none;">'
                '📚 {}</a>',
                obj.modul.id, obj.modul.title[:35]
            )
        return "—"

    @display(description="Davomiyligi")
    def duration_badge(self, obj):
        return format_html(
            '<span style="background:#e0e7ff;color:#4338ca;padding:2px 10px;'
            'border-radius:20px;font-size:12px;font-weight:600;">⏱ {} daq</span>',
            obj.duration
        )

    @display(description="Savollar")
    def question_count_display(self, obj):
        count = obj.questions.count()
        return format_html(
            '<span style="background:#f3e8ff;color:#7c3aed;padding:2px 10px;'
            'border-radius:20px;font-size:12px;font-weight:600;">❓ {} ta</span>',
            count
        )

    @display(description="O'tish foizi")
    def pass_rate_display(self, obj):
        return format_html(
            '<span style="color:#059669;font-weight:700;">{}%</span>',
            obj.min_pass_percentage
        )

    @display(description="Jarima (K)")
    def penalty_display(self, obj):
        return format_html(
            '<span style="color:#dc2626;font-weight:600;">{}x</span>',
            obj.penalty_coefficient
        )
    actions = ["check_test_readiness"]
 
    @admin.action(description="✅ Testni faollashtirishga tayyorligini tekshirish")
    def check_test_readiness(self, request, queryset):
        for test in queryset:
            try:
                test.validate_ready_to_activate()
                self.message_user(
                    request, f"✅ Test '{test.title}' faollashtirishga tayyor.",
                    level=messages.SUCCESS,
                )
            except ValidationError as e:
                error_text = "; ".join(str(m) for m in (e.messages if hasattr(e, "messages") else [str(e)]))
                self.message_user(
                    request, f"❌ Test '{test.title}': {error_text}",
                    level=messages.ERROR,
                )

# ============================================================
# COURSE QUESTION ADMIN
# ============================================================

@admin.register(CourseQuestion)
class CourseQuestionAdmin(BaseOwnerAdmin):
    list_display = (
        'id_display',
        'question_type_badge',
        'location_badge',
        'difficulty_badge',
        'xp_badge',
        'choices_count',
        'created_at_formatted',
    )
    list_filter = ('question_type', 'difficulty', 'test__modul__course', 'lesson__modul__course')
    search_fields = ('text', 'test__title', 'lesson__title', 'owner__username', 'explanation')
    list_per_page = 30
    ordering = ('created_at',)
    inlines = [
        CourseChoiceInline,
        MatchingPairInline,
        ArrangeItemInline,
        BlankInline,
    ]
    autocomplete_fields = ('lesson', 'test', 'explanation_video')

    formfield_overrides = {
        MDTextField: {"widget": MDEditorWidget},
    }

    fieldsets = (
        ("❓ Savol ma'lumotlari", {
            'fields': ('text', 'question_type', 'difficulty', 'xp', 'explanation'),
        }),
        ("🔗 Tegishliligi (faqat bittasi)", {
            'fields': (('lesson', 'test'),),
            'description': "Savol faqat Lesson YOKI Testga tegishli bo'lishi kerak. Ikkisiga birdan emas!",
        }),
        ("🎬 Video tushuntirish", {
            'fields': ('explanation_video',),
            'classes': ('collapse',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    @display(description="Savol matni", header=True)
    def id_display(self, obj):
        location = f"Lesson #{obj.lesson_id}" if obj.lesson_id else f"Test #{obj.test_id}"
        preview = (obj.text[:60] + "…") if obj.text and len(obj.text) > 60 else (obj.text or f"Savol #{obj.pk}")
        return [preview, f"#{obj.pk} · {location}"]

    @display(description="Turi")
    def question_type_badge(self, obj):
        colors = {
            'MULTIPLE_CHOICE': ('#dbeafe', '#1e40af', '🔘'),
            'MATCHING': ('#fce7f3', '#9d174d', '🔗'),
            'ARRANGE_WORDS': ('#fef9c3', '#a16207', '🔤'),
            'FILL_BLANKS': ('#dcfce7', '#15803d', '◻️'),
        }
        bg, fg, emoji = colors.get(obj.question_type, ('#f3f4f6', '#374151', '❓'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:6px;font-size:11px;font-weight:600;">{} {}</span>',
            bg, fg, emoji, obj.get_question_type_display()
        )

    @display(description="Joylashuv")
    def location_badge(self, obj):
        if obj.lesson:
            return format_html(
                '<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;'
                'border-radius:6px;font-size:11px;">📝 Darslik</span>'
            )
        return format_html(
            '<span style="background:#fce7f3;color:#9d174d;padding:2px 8px;'
            'border-radius:6px;font-size:11px;">📋 Test</span>'
        )

    @display(description="Qiyinchilik")
    def difficulty_badge(self, obj):
        colors = {
            'easy':   ('#dcfce7', '#15803d', '🟢'),
            'medium': ('#fef9c3', '#a16207', '🟡'),
            'hard':   ('#fee2e2', '#b91c1c', '🔴'),
        }
        bg, fg, emoji = colors.get(obj.difficulty, ('#f3f4f6', '#374151', '⚪'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:6px;font-size:11px;font-weight:600;">{} {}</span>',
            bg, fg, emoji, obj.get_difficulty_display()
        )

    @display(description="XP")
    def xp_badge(self, obj):
        return format_html(
            '<span style="background:#fef3c7;color:#b45309;padding:2px 8px;'
            'border-radius:6px;font-size:11px;font-weight:700;">+{} XP</span>',
            obj.xp
        )

    @display(description="Variantlar")
    def choices_count(self, obj):
        if obj.question_type == 'MULTIPLE_CHOICE':
            count = obj.choices.count()
            has_correct = obj.choices.filter(is_correct=True).exists()
            color = '#22c55e' if has_correct else '#ef4444'
            icon = '✅' if has_correct else '⚠️'
            return format_html(
                '<span style="color:{};font-weight:600;">{} {} ta</span>',
                color, icon, count
            )
        elif obj.question_type == 'MATCHING':
            count = obj.matching_pairs.count()
            return format_html('<span style="color:#8b5cf6;font-weight:600;">🔗 {} juftlik</span>', count)
        elif obj.question_type == 'ARRANGE_WORDS':
            count = obj.arrange_items.count()
            return format_html('<span style="color:#a16207;font-weight:600;">🔤 {} so\'z</span>', count)
        elif obj.question_type == 'FILL_BLANKS':
            count = obj.blanks.count()
            return format_html('<span style="color:#15803d;font-weight:600;">◻️ {} bo\'sh joy</span>', count)
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    actions = ["check_publish_readiness"]
 
    @admin.action(description="✅ Nashrga tayyorligini tekshirish")
    def check_publish_readiness(self, request, queryset):
        ok_count = 0
        for question in queryset:
            try:
                question.validate_children_completeness()
                ok_count += 1
            except ValidationError as e:
                error_text = "; ".join(e.messages) if hasattr(e, "messages") else str(e)
                self.message_user(
                    request,
                    f"❌ Savol #{question.pk}: {error_text}",
                    level=messages.ERROR,
                )
        if ok_count:
            self.message_user(
                request,
                f"✅ {ok_count} ta savol nashrga tayyor.",
                level=messages.SUCCESS,
            )

    def get_urls(self):

        urls = super().get_urls()

        custom_urls = [
            path(
                "create-question/",
                self.admin_site.admin_view(
                    CreateQuestionView.as_view(
                        model_admin=self,
                    )
                ),
                name="create_question",
            ),
        ]

        return custom_urls + urls

# ============================================================
# COURSE CHOICE ADMIN
# ============================================================

@admin.register(CourseChoice)
class CourseChoiceAdmin(ModelAdmin):
    list_display = (
        'text_preview',
        'question_link',
        'correct_badge',
        'owner_display',
        'created_at_formatted',
    )
    list_filter = ('is_correct', 'question__test__modul__course')
    search_fields = ('text', 'question__text', 'owner__username')
    list_per_page = 40
    ordering = ('-created_at',)
    autocomplete_fields = ('question',)

    fieldsets = (
        ("🔘 Variant ma'lumotlari", {
            'fields': ('question', 'text', 'is_correct'),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    @display(description="Variant matni", header=True)
    def text_preview(self, obj):
        text = obj.text[:50] if obj.text else "—"
        return [text, f"ID: #{obj.id}"]

    @display(description="Tegishli savol")
    def question_link(self, obj):
        if obj.question:
            return format_html(
                '<a href="/admin/courses/coursequestion/{}/change/" style="color:#7c3aed;text-decoration:none;">'
                '❓ Savol #{}</a>',
                obj.question.id, obj.question.id
            )
        return "—"

    @display(description="Holati")
    def correct_badge(self, obj):
        if obj.is_correct:
            return format_html(
                '<span style="background:#dcfce7;color:#15803d;padding:2px 10px;'
                'border-radius:20px;font-size:12px;font-weight:600;">✅ To\'g\'ri</span>'
            )
        return format_html(
            '<span style="background:#f3f4f6;color:#6b7280;padding:2px 10px;'
            'border-radius:20px;font-size:12px;">❌ Noto\'g\'ri</span>'
        )

    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"

    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    def save_model(self, request, obj, form, change):
        if not change and not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


# ============================================================
# MATCHING PAIR ADMIN
# ============================================================

@admin.register(MatchingPair)
class MatchingPairAdmin(ModelAdmin):
    list_display = ('left', 'right', 'question_link', 'order')
    list_filter = ('question__test__modul__course',)
    search_fields = ('left', 'right', 'question__text')
    ordering = ('question', 'order', 'id')
    autocomplete_fields = ('question',)

    fieldsets = (
        ("🔗 Juftlik", {
            'fields': ('question', ('left', 'right'), 'order'),
        }),
    )

    @display(description="Tegishli savol")
    def question_link(self, obj):
        if obj.question:
            return format_html(
                '<a href="/admin/courses/coursequestion/{}/change/" style="color:#7c3aed;text-decoration:none;">'
                '❓ Savol #{}</a>',
                obj.question.id, obj.question.id
            )
        return "—"


# ============================================================
# ARRANGE ITEM ADMIN
# ============================================================

@admin.register(ArrangeItem)
class ArrangeItemAdmin(ModelAdmin):
    list_display = ('text', 'correct_position', 'question_link')
    list_filter = ('question__test__modul__course',)
    search_fields = ('text', 'question__text')
    ordering = ('question', 'correct_position', 'id')
    autocomplete_fields = ('question',)

    fieldsets = (
        ("🔤 So'z", {
            'fields': ('question', 'text', 'correct_position'),
        }),
    )

    @display(description="Tegishli savol")
    def question_link(self, obj):
        if obj.question:
            return format_html(
                '<a href="/admin/courses/coursequestion/{}/change/" style="color:#a16207;text-decoration:none;">'
                '❓ Savol #{}</a>',
                obj.question.id, obj.question.id
            )
        return "—"


# ============================================================
# BLANK & BLANK ANSWER ADMIN
# ============================================================

@admin.register(Blank)
class BlankAdmin(ModelAdmin):
    list_display = ('position', 'question_link', 'case_sensitive', 'answers_count')
    list_filter = ('case_sensitive', 'question__test__modul__course')
    search_fields = ('question__text',)
    ordering = ('question', 'position', 'id')
    autocomplete_fields = ('question',)
    inlines = [BlankAnswerInline]

    fieldsets = (
        ("◻️ Bo'sh joy", {
            'fields': ('question', 'position', 'case_sensitive'),
        }),
    )

    @display(description="Tegishli savol")
    def question_link(self, obj):
        if obj.question:
            return format_html(
                '<a href="/admin/courses/coursequestion/{}/change/" style="color:#15803d;text-decoration:none;">'
                '❓ Savol #{}</a>',
                obj.question.id, obj.question.id
            )
        return "—"

    @display(description="Javoblar soni")
    def answers_count(self, obj):
        count = obj.answers.count()
        return format_html(
            '<span style="background:#dcfce7;color:#15803d;padding:2px 8px;'
            'border-radius:6px;font-size:11px;font-weight:600;">{} ta</span>',
            count
        )


@admin.register(BlankAnswer)
class BlankAnswerAdmin(ModelAdmin):
    list_display = ('answer', 'blank_link')
    search_fields = ('answer', 'blank__question__text')
    autocomplete_fields = ('blank',)

    fieldsets = (
        ("✅ Javob", {
            'fields': ('blank', 'answer'),
        }),
    )

    @display(description="Bo'sh joy")
    def blank_link(self, obj):
        if obj.blank:
            return format_html(
                '<a href="/admin/courses/blank/{}/change/" style="color:#15803d;text-decoration:none;">'
                '◻️ #{} (Pozitsiya: {})</a>',
                obj.blank.id, obj.blank.id, obj.blank.position
            )
        return "—"


# ============================================================
# Custom Filter (Yakunlangan / Yakunlanmagan)
# ============================================================

class CompletionStatusFilter(SimpleListFilter):
    title = _("Holati")
    parameter_name = "completion_status"

    def lookups(self, request, model_admin):
        return (
            ("completed", _("✅ Yakunlangan")),
            ("in_progress", _("🔄 Davom etmoqda")),
        )

    def queryset(self, request, queryset):
        if self.value() == "completed":
            return queryset.filter(completed_at__isnull=False)
        if self.value() == "in_progress":
            return queryset.filter(completed_at__isnull=True)
        return queryset


# ============================================================
# COURSE TEST SESSION ADMIN
# ============================================================

@admin.register(CourseTestSession)
class CourseTestSessionAdmin(ModelAdmin):
    list_display = (
        'user_display',
        'test_link',
        'result_badge',
        'score_display',
        'duration_display',
        'completed_badge',
    )
    list_filter = (
        CompletionStatusFilter,
        'test__modul__course',
        'started_at',
    )
    search_fields = (
        'user__username', 'user__full_name',
        'test__title', 'test__modul__title',
    )
    list_per_page = 30
    ordering = ('-started_at',)
    inlines = [CourseUserResponseInline]

    fieldsets = (
        ("👤 Foydalanuvchi va Test", {
            'fields': (('user', 'test'),),
        }),
        ("📊 Natija", {
            'fields': (
                'correct_count', 'wrong_count',
                'unanswered_count', 'total_xp_earned',
            ),
        }),
        ("🆘 Lifeline", {
            'fields': ('lifelines_used',),
            'classes': ('collapse',),
        }),
        ("⏱️ Vaqt", {
            'fields': (('started_at', 'completed_at'),),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = (
        'user', 'test', 'correct_count', 'wrong_count',
        'unanswered_count', 'total_xp_earned',
        'lifelines_used', 'started_at', 'completed_at',
    )

    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = obj.user.username or obj.user.full_name or f"User#{obj.user.id}"
        return [name, f"ID: {obj.user.id}"]

    @display(description="Test")
    def test_link(self, obj):
        if obj.test:
            return format_html(
                '<a href="/admin/courses/coursetest/{}/change/" style="color:#4f46e5;text-decoration:none;">'
                '📋 {}</a>',
                obj.test.id, obj.test.title[:35]
            )
        return "—"

    @display(description="Natija")
    def result_badge(self, obj):
        if obj.completed_at is None:
            return format_html(
                '<span style="background:#dbeafe;color:#1e40af;padding:2px 10px;'
                'border-radius:20px;font-size:12px;font-weight:600;">🔄 Davom etmoqda</span>'
            )
        total = obj.correct_count + obj.wrong_count + obj.unanswered_count or 1
        pct = (obj.correct_count / total) * 100
        if pct >= obj.test.min_pass_percentage:
            return format_html(
                '<span style="background:#dcfce7;color:#15803d;padding:2px 10px;'
                'border-radius:20px;font-size:12px;font-weight:600;">✅ O\'tdi ({:.0f}%)</span>',
                pct
            )
        return format_html(
            '<span style="background:#fee2e2;color:#b91c1c;padding:2px 10px;'
            'border-radius:20px;font-size:12px;font-weight:600;">❌ O\'ta olmadi ({:.0f}%)</span>',
            pct
        )

    @display(description="Ball")
    def score_display(self, obj):
        return format_html(
            '<div style="display:flex;gap:8px;font-size:12px;">'
            '<span style="color:#22c55e;font-weight:600;">✓ {}</span>'
            '<span style="color:#ef4444;font-weight:600;">✗ {}</span>'
            '<span style="color:#f59e0b;font-weight:600;">? {}</span>'
            '</div>',
            obj.correct_count, obj.wrong_count, obj.unanswered_count
        )

    @display(description="Davomiyligi")
    def duration_display(self, obj):
        if obj.completed_at:
            delta = obj.completed_at - obj.started_at
            minutes = int(delta.total_seconds() // 60)
            seconds = int(delta.total_seconds() % 60)
            return format_html(
                '<span style="color:#64748b;">{}:{} daq</span>',
                minutes, f"{seconds:02d}"
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description="Yakunlangan")
    def completed_badge(self, obj):
        if obj.completed_at:
            return obj.completed_at.strftime("%d-%m-%Y %H:%M")
        return format_html(
            '<span style="color:#f59e0b;font-weight:600;">⏳ Yakunlanmagan</span>'
        )

    def has_add_permission(self, request):
        return False


# ============================================================
# COURSE USER RESPONSE ADMIN
# ============================================================

@admin.register(CourseUserResponse)
class CourseUserResponseAdmin(ModelAdmin):
    list_display = (
        'user_display',
        'question_preview',
        'answer_status',
        'session_link',
        'created_at_formatted',
    )
    list_filter = ('choice__is_correct', 'created_at')
    search_fields = (
        'user__username', 'user__full_name',
        'question__text', 'choice__text',
    )
    list_per_page = 50
    ordering = ('-created_at',)

    fieldsets = (
        ("🎯 Javob ma'lumotlari", {
            'fields': (('user', 'session'), 'question', 'choice', 'answer_data', 'is_correct'),
        }),
        ("📅 Vaqt", {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at', 'user', 'session', 'question', 'choice', 'answer_data', 'is_correct')

    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = obj.user.username or obj.user.full_name or f"User#{obj.user.id}"
        return [name, f"Savol #{obj.question_id}"]

    @display(description="Savol")
    def question_preview(self, obj):
        return f"Savol #{obj.question_id}"

    @display(description="Javob holati")
    def answer_status(self, obj):
        if obj.choice is None and not obj.answer_data:
            return format_html(
                '<span style="background:#fef3c7;color:#b45309;padding:2px 10px;'
                'border-radius:20px;font-size:12px;">⏸ Javobsiz</span>'
            )
        if obj.is_correct:
            return format_html(
                '<span style="background:#dcfce7;color:#15803d;padding:2px 10px;'
                'border-radius:20px;font-size:12px;font-weight:600;">✅ To\'g\'ri</span>'
            )
        return format_html(
            '<span style="background:#fee2e2;color:#b91c1c;padding:2px 10px;'
            'border-radius:20px;font-size:12px;font-weight:600;">❌ Xato</span>'
        )

    @display(description="Seans")
    def session_link(self, obj):
        if obj.session:
            return format_html(
                '<a href="/admin/courses/coursetestsession/{}/change/" style="color:#4f46e5;text-decoration:none;">'
                '⏱ Seans {}</a>',
                obj.session.id, str(obj.session.id)[:8]
            )
        return "—"

    @display(description="Javob vaqti")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    def has_add_permission(self, request):
        return False

# ============================================================
# ADMIN.PY GA QO'SHISH KERAK BO'LGAN KODLAR
# ============================================================
# courses/admin.py

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse_lazy

from unfold.admin import ModelAdmin
from unfold.views import UnfoldModelAdminViewMixin
from django.views.generic import FormView

from .models import (
    CourseQuestion,
    Lesson,
    CourseTest,
)

from .forms import (
    QuestionCreateForm,
    ChoiceFormSet,
    MatchingPairFormSet,
    ArrangeItemFormSet,
    BlankFormSet,
)

from .services import QuestionCreateService


# ============================================================
# CUSTOM PAGE
# ============================================================

class CreateQuestionView(
    UnfoldModelAdminViewMixin,
    FormView,
):
    """
    Unfold Custom Page:
    yangi savol yaratish.
    """

    title = "Yangi savol yaratish"

    permission_required = (
        "courses.add_coursequestion",
    )

    template_name = (
        "admin/courses/question/create.html"
    )

    form_class = QuestionCreateForm

    # --------------------------------------------------------
    # SUCCESS URL
    # --------------------------------------------------------

    def get_success_url(self):
        return reverse_lazy(
            "admin:courses_coursequestion_changelist"
        )

    # --------------------------------------------------------
    # FORM
    # --------------------------------------------------------

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        request = self.request

        # Superuser barcha Lesson/Testlarni ko'radi
        if request.user.is_superuser:

            form.fields["lesson"].queryset = (
                Lesson.objects
                .all()
                .select_related("modul__course")
            )

            form.fields["test"].queryset = (
                CourseTest.objects
                .all()
                .select_related("modul__course")
            )

        # Oddiy admin faqat o'z obyektlarini ko'radi
        else:

            form.fields["lesson"].queryset = (
                Lesson.objects
                .filter(owner=request.user)
                .select_related("modul__course")
            )

            form.fields["test"].queryset = (
                CourseTest.objects
                .filter(owner=request.user)
                .select_related("modul__course")
            )

        return form

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # POST bo'lsa yuborilgan ma'lumotlarni qayta ishlatamiz
        if self.request.POST:

            context["choice_formset"] = (
                ChoiceFormSet(
                    self.request.POST,
                    prefix="choices",
                )
            )

            context["matching_formset"] = (
                MatchingPairFormSet(
                    self.request.POST,
                    prefix="matching",
                )
            )

            context["arrange_formset"] = (
                ArrangeItemFormSet(
                    self.request.POST,
                    prefix="arrange",
                )
            )

            context["blank_formset"] = (
                BlankFormSet(
                    self.request.POST,
                    prefix="blanks",
                )
            )

        # GET bo'lsa bo'sh formset
        else:

            context["choice_formset"] = (
                ChoiceFormSet(
                    prefix="choices",
                )
            )

            context["matching_formset"] = (
                MatchingPairFormSet(
                    prefix="matching",
                )
            )

            context["arrange_formset"] = (
                ArrangeItemFormSet(
                    prefix="arrange",
                )
            )

            context["blank_formset"] = (
                BlankFormSet(
                    prefix="blanks",
                )
            )

        context["title"] = self.title

        context["subtitle"] = (
            "Yangi test savolini yaratish"
        )

        return context

    # --------------------------------------------------------
    # FORM VALID
    # --------------------------------------------------------

    def form_valid(self, form):

        context = self.get_context_data()

        question_type = (
            form.cleaned_data["question_type"]
        )

        # Savol turiga mos formsetni tanlaymiz
        formsets = {

            "MULTIPLE_CHOICE": (
                "choice_formset",
                context["choice_formset"],
            ),

            "MATCHING": (
                "matching_formset",
                context["matching_formset"],
            ),

            "ARRANGE_WORDS": (
                "arrange_formset",
                context["arrange_formset"],
            ),

            "FILL_BLANKS": (
                "blank_formset",
                context["blank_formset"],
            ),
        }

        target_name, target_formset = formsets.get(
            question_type,
            (None, None),
        )

        # ----------------------------------------------------
        # FORMSET VALIDATION
        # ----------------------------------------------------

        if target_formset is not None:

            if not target_formset.is_valid():

                # Xatolarni ko'rsatish uchun
                context[target_name] = target_formset

                return self.render_to_response(
                    context
                )

        # ----------------------------------------------------
        # SERVICE
        # ----------------------------------------------------

        try:

            service = (
                QuestionCreateService()
            )

            kwargs = {
                "user": self.request.user,
                "form_data": form.cleaned_data,
            }

            # ------------------------------------------------
            # MULTIPLE CHOICE
            # ------------------------------------------------

            if question_type == "MULTIPLE_CHOICE":

                kwargs["choice_data"] = (
                    target_formset.cleaned_data
                )

            # ------------------------------------------------
            # MATCHING
            # ------------------------------------------------

            elif question_type == "MATCHING":

                kwargs["matching_data"] = (
                    target_formset.cleaned_data
                )

            # ------------------------------------------------
            # ARRANGE WORDS
            # ------------------------------------------------

            elif question_type == "ARRANGE_WORDS":

                kwargs["arrange_data"] = (
                    target_formset.cleaned_data
                )

            # ------------------------------------------------
            # FILL BLANKS
            # ------------------------------------------------

            elif question_type == "FILL_BLANKS":

                kwargs["blank_data"] = (
                    target_formset.cleaned_data
                )

            # ------------------------------------------------
            # CREATE
            # ------------------------------------------------

            question = service.create(
                **kwargs
            )

            messages.success(
                self.request,
                f"Savol #{question.id} muvaffaqiyatli yaratildi.",
            )

            # Yaratilgan savolning change sahifasiga
            # o'tkazamiz
            return redirect(
                "admin:courses_coursequestion_change",
                question.id,
            )

        except Exception as e:

            messages.error(
                self.request,
                f"Savol yaratishda xatolik: {str(e)}",
            )

            return self.render_to_response(
                context
            )

    # --------------------------------------------------------
    # FORM INVALID
    # --------------------------------------------------------

    def form_invalid(self, form):

        messages.warning(
            self.request,
            "Formada xatoliklar mavjud.",
        )

        return super().form_invalid(form)

