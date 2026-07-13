import logging

import json
from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncMonth
from django.db.models import Count, Q

from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from unfold.admin import ModelAdmin, TabularInline
from mdeditor.fields import MDEditorWidget
from unfold.decorators import display
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RelatedDropdownFilter,
    DropdownFilter,
)

from baseuser.utils.admin import BaseOwnerAdmin, BaseOwnerInline

from .models import (
    Test, Question, Choice, TestSession, UserResponse, TestEnrollment
)

logger = logging.getLogger(__name__)


# ==================== INLINES ====================

class ChoiceInline(BaseOwnerInline):
    """Savol variantlari inline"""
    model = Choice
    extra = 2
    fields = ('text', 'is_correct', 'explanation', 'order')
    tab = True
    classes = ('collapse',)


class QuestionInline(BaseOwnerInline):
    """Savollar inline (Test ichida)"""
    model = Question
    extra = 1
    fields = ('text', 'difficulty', 'xp', 'order')
    tab = True
    classes = ('collapse',)


class TestSessionInline(TabularInline):
    """Test seanslari inline - owner YO'Q"""
    model = TestSession
    extra = 0
    fields = ('user', 'status', 'score', 'total_xp_earned', 'started_at')
    readonly_fields = ('started_at',)
    tab = True
    classes = ('collapse',)
    can_delete = False
    max_num = 0


class UserResponseInline(TabularInline):
    """Foydalanuvchi javoblari inline - owner YO'Q"""
    model = UserResponse
    extra = 0
    fields = ('user', 'question', 'choice', 'created_at')
    readonly_fields = ('created_at',)
    tab = True
    classes = ('collapse',)
    can_delete = False
    max_num = 0





@admin.register(Test)
class TestAdmin(BaseOwnerAdmin):  # BaseOwnerAdmin ichida Unfold ModelAdmin borligini tekshiring
    list_before_template = "admin/quizs/test/list_top.html"
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 25
    ordering = ('-id',)
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'slug', 'modul__title', 'access_code')
    list_editable = ('is_active',)
    inlines = [QuestionInline, TestSessionInline]
    
    list_filter = (
        'is_active',
        ('modul', admin.RelatedOnlyFieldListFilter),
        'start_time',
        'end_time',
    )
    
    list_display = (
        'title_display',
        'modul_display',
        'status_badge',
        'question_count_display',
        'sessions_count_display',
        'is_active',
        'created_at_formatted',
    )
    
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }
    
    readonly_fields = ('question_count',)
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('modul').annotate(
            _questions_count=Count('questions', distinct=True),
            _sessions_count=Count('sessions', distinct=True)
        )

    @display(description="Test nomi", header=True)
    def title_display(self, obj):
        return [obj.title[:50], f"ID: #{obj.id}"]
    
    @display(description="Modul")
    def modul_display(self, obj):
        if obj.modul:
            return format_html(
                '<a href="/admin/courses/modul/{}/change/" class="text-blue-600 hover:underline">📚 {}</a>',
                obj.modul.id, obj.modul.title[:30]
            )
        return format_html('<span class="text-gray-400 dark:text-gray-500">— Mustaqil test</span>')
    
    @display(description="Holat")
    def status_badge(self, obj):
        now_time = now()
        if not obj.is_active:
            return mark_safe('<span class="bg-red-100 text-red-700 px-2.5 py-1 rounded-full text-xs font-semibold dark:bg-red-900/30 dark:text-red-400">⛔ Nofaol</span>')
        if obj.start_time > now_time:
            return mark_safe('<span class="bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full text-xs font-semibold dark:bg-amber-900/30 dark:text-amber-400">🔜 Kutilmoqda</span>')
        if obj.end_time < now_time:
            return mark_safe('<span class="bg-rose-100 text-rose-700 px-2.5 py-1 rounded-full text-xs font-semibold dark:bg-rose-900/30 dark:text-rose-400">✅ Yakunlangan</span>')
        return mark_safe('<span class="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-xs font-semibold dark:bg-green-900/30 dark:text-green-400">▶️ Davom etmoqda</span>')
    
    @display(description="Savollar", ordering='_questions_count')
    def question_count_display(self, obj):
        return format_html('<span class="bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full text-xs font-semibold dark:bg-blue-900/30 dark:text-blue-400">📝 {} ta</span>', obj._questions_count)
    
    @display(description="Seanslar", ordering='_sessions_count')
    def sessions_count_display(self, obj):
        return format_html('<span class="bg-purple-100 text-purple-700 px-2.5 py-1 rounded-full text-xs font-semibold dark:bg-purple-900/30 dark:text-purple-400">⏱️ {} ta</span>', obj._sessions_count)
    
    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        now_time = now()
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)
        
        test_stats = filtered_qs.aggregate(
            total_tests=Count('id'),
            active_tests=Count('id', filter=Q(is_active=True)),
            inactive_tests=Count('id', filter=Q(is_active=False)),
            upcoming_count=Count('id', filter=Q(is_active=True, start_time__gt=now_time)),
            ongoing_count=Count('id', filter=Q(is_active=True, start_time__lte=now_time, end_time__gte=now_time)),
            ended_count=Count('id', filter=Q(is_active=True, end_time__lt=now_time))
        )
        
        session_stats = TestSession.objects.aggregate(
            total_sessions=Count('id'),
            completed_sessions=Count('id', filter=Q(status='completed'))
        )
        
        extra_context.update({
            'total_tests': test_stats['total_tests'] or 0,
            'active_tests': test_stats['active_tests'] or 0,
            'inactive_tests': test_stats['inactive_tests'] or 0,
            'upcoming_count': test_stats['upcoming_count'] or 0,
            'ongoing_count': test_stats['ongoing_count'] or 0,
            'ended_count': test_stats['ended_count'] or 0,
            'total_sessions': session_stats['total_sessions'] or 0,
            'completed_sessions': session_stats['completed_sessions'] or 0,
        })
        return super().changelist_view(request, extra_context=extra_context)


# ==================== QUESTION ADMIN ====================
@admin.register(Question)
class QuestionAdmin(BaseOwnerAdmin):
    # ─── 🎨 UNFOLD ANDOZA VA SOZLAMALARI ───
    list_before_template = "admin/quizs/question/list_top.html"
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 30
    ordering = ('-id',)
    
    search_fields = ('text', 'test__title', 'lesson__title')
    inlines = [ChoiceInline, UserResponseInline]
    
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }
    
    # ✅ TO'G'RI UNFOLD DROPDOWN FILTRLAR
    list_filter = (
        ('difficulty', ChoicesDropdownFilter),  # ✅ CharField choices
        ('test', RelatedDropdownFilter),        # ✅ ForeignKey
        ('lesson', RelatedDropdownFilter),      # ✅ ForeignKey
        ('created_at', admin.DateFieldListFilter),  # ✅ Django default
    )
    
    list_display = (
        'text_preview',
        'difficulty_badge',
        'test_display',
        'lesson_display',
        'xp_display',
        'choices_count_display',
        'order_display',
    )
    
    fieldsets = (
        ("❓ Savol Ma'lumotlari", {
            'fields': (
                ('test', 'lesson'),
                'text',
                ('difficulty', 'xp'),
                'order',
            )
        }),
        ("🎬 Video Tahlil", {
            'fields': ('explanation_video',),
            'classes': ('collapse',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )
    
    # ─── 🚀 N+1 SO'ROVLAR O'LIMI (SELECT_RELATED + ANNOTATE) ───
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('test', 'lesson').annotate(
            _choices_count=Count('choices')
        )

    # ========== DISPLAY METHODS ==========
    @display(description="Savol matni")
    def text_preview(self, obj):
        return obj.text[:60] + "..." if len(obj.text) > 60 else obj.text
    
    @display(description="Qiyinchilik", ordering='difficulty')
    def difficulty_badge(self, obj):
        colors = {
            'easy': ('bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400', '🟢 Oson'),
            'medium': ('bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400', '🟡 O\'rta'),
            'hard': ('bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', '🔴 Qiyin'),
        }
        badge_class, label = colors.get(obj.difficulty, ('bg-gray-100 text-gray-700', obj.difficulty))
        return mark_safe(
            f'<span class="{badge_class} px-2.5 py-1 rounded-full text-xs font-semibold">{label}</span>'
        )
    
    @display(description="Test")
    def test_display(self, obj):
        if obj.test:
            return format_html(
                '<a href="/admin/quizs/test/{}/change/" class="text-blue-600 hover:underline">📝 {}</a>',
                obj.test.id, obj.test.title[:30]
            )
        return "—"
    
    @display(description="Darslik")
    def lesson_display(self, obj):
        if obj.lesson:
            return format_html(
                '<a href="/admin/courses/lesson/{}/change/" class="text-green-600 hover:underline">📘 {}</a>',
                obj.lesson.id, obj.lesson.title[:30]
            )
        return "—"
    
    @display(description="XP")
    def xp_display(self, obj):
        return format_html(
            '<span class="bg-purple-600 text-white px-2.5 py-1 rounded-full text-xs font-semibold">⚡ {}</span>',
            obj.xp
        )
    
    @display(description="Variantlar", ordering='_choices_count')
    def choices_count_display(self, obj):
        return format_html(
            '<span class="bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 px-2.5 py-1 rounded-full text-xs">🔘 {}</span>',
            obj._choices_count
        )
    
    @display(description="Tartib")
    def order_display(self, obj):
        return format_html('<span class="text-gray-400 dark:text-gray-500 text-sm">#{}</span>', obj.order or 0)

    # ─── 📊 TEZKOR CHANGELIST VIEW STATISTIKASI ───
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # ✅ FILTRLANGAN QUERYSET
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)
        
        # ✅ QIYINCHILIK STATISTIKASI
        stats = filtered_qs.aggregate(
            total_questions=Count('id'),
            easy_count=Count('id', filter=Q(difficulty='easy')),
            medium_count=Count('id', filter=Q(difficulty='medium')),
            hard_count=Count('id', filter=Q(difficulty='hard')),
        )
        
        total = stats['total_questions'] or 1
        
        # ✅ FOIZLARNI HISOBLASH
        easy_percent = round((stats['easy_count'] / total) * 100)
        medium_percent = round((stats['medium_count'] / total) * 100)
        hard_percent = round((stats['hard_count'] / total) * 100)
        
        # ✅ KONTEKSTGA QO'SHISH
        extra_context.update({
            'total_questions': stats['total_questions'] or 0,
            'easy_count': stats['easy_count'] or 0,
            'medium_count': stats['medium_count'] or 0,
            'hard_count': stats['hard_count'] or 0,
            'easy_percent': easy_percent,
            'medium_percent': medium_percent,
            'hard_percent': hard_percent,
        })
        
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Choice)
class ChoiceAdmin(BaseOwnerAdmin):
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 30
    ordering = ('-id',)
    
    search_fields = ('text', 'question__text', 'explanation')
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }
    
    list_filter = (
        'is_correct',
        ('question', admin.RelatedOnlyFieldListFilter),
    )
    
    list_display = (
        'text_preview',
        'question_display',
        'is_correct_icon',
        'order_display',
    )
    
    fieldsets = (
        ("🔘 Javob Varianti", {
            'fields': (
                ('question', 'is_correct'),
                'text',
                'explanation',
                'order',
            )
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )
    
    # ─── 🚀 CHOICE N+1 OPTIMIZATSIYASI ───
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('question')

    @display(description="Variant matni")
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    
    @display(description="Savol")
    def question_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/question/{}/change/" class="text-blue-600 hover:underline">❓ {}</a>',
            obj.question.id, obj.question.text[:40]
        )
    
    @display(description="To'g'ri", ordering='is_correct')
    def is_correct_icon(self, obj):
        if obj.is_correct:
            return mark_safe('<span class="text-green-500 font-bold text-base">✅ To\'g\'ri</span>')
        return mark_safe('<span class="text-red-500 font-bold text-base">❌ Noto\'g\'ri</span>')
    
    @display(description="Tartib")
    def order_display(self, obj):
        return format_html('<span class="text-gray-400 dark:text-gray-500 text-sm">#{}</span>', obj.order or 0)


# ==================== TEST SESSION ADMIN ====================


# O'z ota klassingiz nomini tekshiring (agar BaseOwnerAdmin bo'lsa o'shani yozing)
@admin.register(TestSession)
class TestSessionAdmin(BaseOwnerAdmin):  
    list_before_template = "admin/quizs/testsession/list_top.html"
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 30
    ordering = ('-id',)
    autocomplete_fields = ('user', 'test')
    search_fields = ('user__username', 'user__full_name', 'test__title')
    
    list_filter = (
        'status',
        ('test', admin.RelatedOnlyFieldListFilter),
        'started_at',
    )
    
    list_display = (
        'user_display',
        'test_display',
        'status_badge',
        'score_display',
        'xp_display',
        'accuracy_display',
        'started_at_formatted',
    )
    
    fieldsets = (
        ("👤 Foydalanuvchi va Test", {
            'fields': (('user', 'test'),),
        }),
        ("📊 Natijalar", {
            'fields': (
                ('score', 'total_xp_earned'),
                ('correct_count', 'wrong_count', 'unanswered_count'),
                'status',
            )
        }),
        ("📅 Vaqt", {
            'fields': (('started_at', 'completed_at'),),
        }),
    )
    
    readonly_fields = ('started_at', 'completed_at', 'score', 'total_xp_earned', 
                       'correct_count', 'wrong_count', 'unanswered_count')
    
    # ─── 🚀 N+1 SO'ROVLAR O'LIMI (SELECT_RELATED) ───
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'test')

    # ========== DISPLAY METHODS (100% XAVFSIZ VA TOZA) ==========
    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return [name, f"ID: {obj.user.telegram_id}"]
    
    @display(description="Test")
    def test_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/test/{}/change/" class="text-blue-600 hover:underline">📝 {}</a>',
            obj.test.id, obj.test.title[:40]
        )
    
    @display(description="Holat", ordering='status')
    def status_badge(self, obj):
        colors = {
            'in_progress': ('bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', '🔄 Jarayonda'),
            'completed': ('bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400', '✅ Yakunlangan'),
            'expired': ('bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', '⏰ Muddati o\'tgan'),
        }
        badge_class, label = colors.get(obj.status, ('bg-gray-100 text-gray-700', obj.status))
        return mark_safe(f'<span class="{badge_class} px-2.5 py-1 rounded-full text-xs font-semibold">{label}</span>')
    
    # ─── FORMAT_HTML XATOLIGINI BUTUNLAY DAVOLASH ───
    @display(description="Ball", ordering='score')
    def score_display(self, obj):
        try:
            score_value = float(obj.score) if obj.score is not None else 0.0
        except (ValueError, TypeError):
            score_value = 0.0
        
        # Formatlashni format_html'dan TASHQARIDA, Python f-stringida qilamiz!
        score_string = f"{score_value:.2f}"
        
        # format_html ichida hech qanday {:.2f} qoldirmaymiz. SafeString xatosi butunlay o'ladi!
        return format_html('<span class="font-semibold text-blue-600 dark:text-blue-400">{}</span>', score_string)
    
    @display(description="XP", ordering='total_xp_earned')
    def xp_display(self, obj):
        try:
            xp_value = int(obj.total_xp_earned) if obj.total_xp_earned is not None else 0
        except (ValueError, TypeError):
            xp_value = 0
        return format_html('<span class="bg-purple-600 text-white px-2.5 py-1 rounded-full text-xs font-semibold">✨ {} XP</span>', xp_value)
        
    @display(description="Aniqlik (Accuracy)")
    def accuracy_display(self, obj):
        total = (obj.correct_count or 0) + (obj.wrong_count or 0) + (obj.unanswered_count or 0)
        acc = ((obj.correct_count or 0) / total) * 100 if total > 0 else 0.0
        
        # Formatlash to'liq Python darajasida bajariladi
        acc_string = f"{acc:.1f}%"
        return format_html('<span class="font-medium text-green-600 dark:text-green-400">{}</span>', acc_string)
    
    @display(description="Boshlangan vaqt", ordering='started_at')
    def started_at_formatted(self, obj):
        return obj.started_at.strftime("%d-%m-%Y %H:%M") if obj.started_at else "—"

    # ─── 📊 CHANGELIST VIEW STATISTIKASI (AGGREGATE) ───
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)
        
        stats = filtered_qs.aggregate(
            total_sessions=Count('id'),
            in_progress_count=Count('id', filter=Q(status='in_progress')),
            completed_count=Count('id', filter=Q(status='completed')),
            expired_count=Count('id', filter=Q(status='expired')),
            avg_score=Avg('score'),
            total_xp=Sum('total_xp_earned')
        )
        
        extra_context.update({
            'total_sessions': stats['total_sessions'] or 0,
            'in_progress_count': stats['in_progress_count'] or 0,
            'completed_count': stats['completed_count'] or 0,
            'expired_count': stats['expired_count'] or 0,
            'avg_score': stats['avg_score'] or 0.0,  # Toza float yuklanadi, HTML'da floatformat qilinadi
            'total_xp': stats['total_xp'] or 0,
        })
        return super().changelist_view(request, extra_context=extra_context)

# ==================== USER RESPONSE ADMIN ====================
import json
from django.contrib import admin
from django.contrib.admin import ModelAdmin
# --- KO'RSATKICHLAR VA GRAFIKLAR UCHUN AGGREGATE IMPORTLARI ---
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncMonth
from django.utils.html import format_html
from django.utils.safestring import mark_safe

# --- UNFOLD MODELADMIN IMPORTI ---
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

# ================= USER RESPONSE ADMIN ====================

@admin.register(UserResponse)
class UserResponseAdmin(UnfoldModelAdmin):  # UnfoldModelAdmin ga o'zgartirildi
    # ─── 🎨 UNFOLD EKSKLYUZIV SHABLON SOZLAMALARI ───
    # Ro'yxat sahifasining tepasiga siz taqdim etgan custom HTML dashboardni ulaymiz
    list_before_template = "admin/quizs/userresponse/list_top.html"
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER

    list_display = (
        'user_display',
        'question_display',
        'choice_display',
        'is_correct_icon',
        'created_at_formatted',
    )
    
    list_filter = ('created_at',)
    search_fields = ('user__username', 'question__text', 'choice__text')
    list_per_page = 50
    ordering = ('-id',)
    autocomplete_fields = ('user', 'question', 'choice')
    
    fieldsets = (
        ("🎯 Foydalanuvchi Javobi", {
            'fields': (('user', 'question'), 'choice'),
        }),
        ("📅 Vaqt", {
            'fields': ('created_at',),
        }),
    )
    
    readonly_fields = ('created_at',)

    # ─── 📊 SAVOLLAR VA JAVOBLAR STATISTIKASI (CHANGELIST VIEW) ───
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # 1. Hozirgi filtrlar qo'llanilgan querysetni olamiz
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        # 2. KPI kartalari uchun statistikani bitta SQL so'rovda yig'amiz
        stats = filtered_qs.aggregate(
            total_cnt=Count('id'),
            correct_cnt=Count('id', filter=Q(choice__is_correct=True)),
            incorrect_cnt=Count('id', filter=Q(choice__is_correct=False))
        )

        total_problems = stats['total_cnt'] or 0
        active_problems = stats['correct_cnt'] or 0  # To'g'ri javoblar
        inactive_problems = stats['incorrect_cnt'] or 0  # Noto'g'ri javoblar
        avg_xp = 85  # Agar sizda XP hisoblash tizimi bo'lsa dynamic qiymat bog'lang

        # 3. Progress Barlar va Doughnut Chart uchun qiyinchilik taqsimoti
        difficulty_stats = filtered_qs.aggregate(
            easy_cnt=Count('id', filter=Q(question__difficulty='easy')),
            medium_cnt=Count('id', filter=Q(question__difficulty='medium')),
            hard_cnt=Count('id', filter=Q(question__difficulty='hard'))
        )

        easy_count = difficulty_stats['easy_cnt'] or 0
        medium_count = difficulty_stats['medium_cnt'] or 0
        hard_count = difficulty_stats['hard_cnt'] or 0

        # Foizlarni aniqlash (0 ga bo'linish xatosidan himoya bilan)
        total_difficulty = easy_count + medium_count + hard_count or 1
        easy_percent = round((easy_count / total_difficulty) * 100)
        medium_percent = round((medium_count / total_difficulty) * 100)
        hard_percent = round((hard_count / total_difficulty) * 100)

        # Context-ga ma'lumotlarni HTML uchun yuboramiz
        extra_context.update({
            # KPI Kartalari
            "total_problems": total_problems,
            "active_problems": active_problems,
            "inactive_problems": inactive_problems,
            "avg_xp": avg_xp,
            
            # Progress bar-lar
            "easy_count": easy_count,
            "easy_percent": easy_percent,
            "medium_count": medium_count,
            "medium_percent": medium_percent,
            "hard_count": hard_count,
            "hard_percent": hard_percent,

            # Chart.js (Doughnut) uchun ma'lumotlar
            "chart_labels": json.dumps(["Oson", "O'rta", "Qiyin"]),
            "chart_data": json.dumps([easy_count, medium_count, hard_count]),
        })

        return super().changelist_view(request, extra_context=extra_context)
    
    # ─── 🎨 DINAMIK USTUN METODLARI ───
    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return [name, f"ID: {obj.user.telegram_id}"]
    
    @display(description="Savol")
    def question_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/question/{}/change/" style="color: #3b82f6;">❓ {}</a>',
            obj.question.id, obj.question.text[:40]
        )
    
    @display(description="Javob")
    def choice_display(self, obj):
        if obj.choice:
            return obj.choice.text[:50] + "..." if len(obj.choice.text) > 50 else obj.choice.text
        return format_html(
            '<span style="color: #94a3b8; font-style: italic;">Javobsiz qoldirilgan</span>'
        )
    
    @display(description="To'g'ri")
    def is_correct_icon(self, obj):
        if obj.choice:
            if obj.choice.is_correct:
                return mark_safe('<span style="color: #22c55e; font-size: 18px;">✅</span>')
            return mark_safe('<span style="color: #ef4444; font-size: 18px;">❌</span>')
        return mark_safe('<span style="color: #94a3b8; font-size: 18px;">⏭️</span>')
    
    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")


# ================= TEST ENROLLMENT ADMIN ====================

@admin.register(TestEnrollment)
class TestEnrollmentAdmin(ModelAdmin):
    # ─── 🎨 UNFOLD EKSKLYUZIV SHABLON SOZLAMALARI ───
    # Ro'yxat sahifasining eng tepasiga custom HTML grafik va KPI bloklarini joylashtiramiz
    list_before_template = "admin/payment/testenrollment/list_top.html"
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER

    list_display = [
        "display_user",       
        "test",               
        "formatted_amount",   
        "transaction_id",     
        "created_at",         
    ]

    search_fields = [
        "user__username", 
        "user__telegram_id", 
        "test__title", 
        "transaction_id"
    ]

    # Katta FK jadvallarni faqat ishlatilgan qiymatlar bo'yicha filterlash (Optimallash)
    list_filter = [
        ("test", admin.RelatedOnlyFieldListFilter),
        "created_at"
    ]

    list_select_related = ["user", "test"]
    readonly_fields = ["id", "created_at"]
    ordering = ["-created_at"]

    # ─── 📊 TOZA SINXRON RECALCULATE LOGIKASI (CHANGELIST VIEW) ───
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # 1. Hozirgi filtrlar qo'llanilgan querysetni olamiz (Filtrga qarab grafik ham o'zgaradi)
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)

        # 2. KPI ma'lumotlarini bitta SQL so'rovda aggregate qilamiz (Ultra-tezkor)
        stats = filtered_qs.aggregate(
            total_sales_count=Count('id'),
            total_revenue=Sum('amount'),
            average_check=Avg('amount')
        )

        total_revenue = stats['total_revenue'] or 0
        total_sales_count = stats['total_sales_count'] or 0
        average_check = stats['average_check'] or 0

        # 3. Grafik uchun oylik daromad statistikasi (Chart.js uchun ma'lumot tayyorlash)
        monthly_data = (
            filtered_qs.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(revenue=Sum('amount'))
            .order_by('month')
        )

        chart_labels = []
        chart_values = []
        for item in monthly_data:
            if item['month']:
                chart_labels.append(item['month'].strftime('%Y-%m'))
                chart_values.append(float(item['revenue'] or 0))

        # Context-ga ma'lumotlarni xavfsiz yuklaymiz
        extra_context.update({
            "total_sales_count": total_sales_count,
            "total_revenue": f"{total_revenue:,.2f}",
            "average_check": f"{average_check:,.2f}",
            "chart_labels_json": json.dumps(chart_labels),
            "chart_values_json": json.dumps(chart_values),
        })

        return super().changelist_view(request, extra_context=extra_context)

    # ─── DINAMIK USTUN METODLARI ───
    @admin.display(description="Foydalanuvchi")
    def display_user(self, obj):
        return obj.user.username if obj.user.username else f"TG: {obj.user.telegram_id}"

    @admin.display(description="To'lov summasi", ordering="amount")
    def formatted_amount(self, obj):
        return f"{obj.amount:,.2f} UZS"
