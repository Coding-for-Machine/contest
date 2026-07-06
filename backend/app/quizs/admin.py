import logging
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from unfold.admin import ModelAdmin, TabularInline
from mdeditor.fields import MDEditorWidget
from unfold.decorators import display

from baseuser.utils.admin import BaseOwnerAdmin, BaseOwnerInline

from .models import (
    Test, Question, Choice, TestSession, UserResponse,
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


# ==================== TEST ADMIN ====================

@admin.register(Test)
class TestAdmin(BaseOwnerAdmin):
    change_list_template = "admin/quiz/test_changelist.html"
    
    list_display = (
        'title_display',
        'modul_display',
        'status_badge',
        'question_count_display',
        'sessions_count_display',
        'is_active',
        'created_at_formatted',
    )
    
    list_filter = (
        'is_active',
        'modul',
        'start_time',
        'end_time',
    )
    
    search_fields = ('title', 'slug', 'modul__title', 'access_code')
    list_editable = ('is_active',)
    list_per_page = 25
    ordering = ('-id',)
    prepopulated_fields = {'slug': ('title',)}
    
    # ✅ Inlinelar qo'shildi
    inlines = [QuestionInline, TestSessionInline]
    
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }
    
    fieldsets = (
        ("📌 Asosiy Ma'lumotlar", {
            'fields': (
                ('title', 'slug'),
                ('modul', 'intro_video'),
                'is_active',
            )
        }),
        ("⏰ Vaqt va Davomiylik", {
            'fields': (
                ('start_time', 'end_time'),
                ('duration_minutes', 'question_count'),
                ('random_questions_count', 'max_attempts'),
            ),
            'description': "⚠️ Barcha vaqtlar joriy vaqt zonasida ko'rsatiladi"
        }),
        ("🎯 Baholash va Cheklovlar", {
            'fields': (
                ('min_pass_percentage', 'penalty_coefficient'),
                ('max_lifelines',),
            ),
            'description': "Penalty koeffitsiyenti: 0-1 oralig'ida"
        }),
        ("💰 Narx va Kirish", {
            'fields': (
                ('price', 'discount_price'),
                ('access_code',),
            ),
            'classes': ('collapse',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('question_count',)
    
    # ========== DISPLAY METHODS ==========
    
    @display(description="Test nomi", header=True)
    def title_display(self, obj):
        return [obj.title[:50], f"ID: #{obj.id}"]
    
    @display(description="Modul")
    def modul_display(self, obj):
        if obj.modul:
            return format_html(
                '<a href="/admin/courses/modul/{}/change/" style="color: #3b82f6;">'
                '📚 {}</a>',
                obj.modul.id, obj.modul.title[:30]
            )
        return format_html(
            '<span style="color: #94a3b8;">— Mustaqil test</span>'
        )
    
    @display(description="Holat")
    def status_badge(self, obj):
        now_time = now()
        if not obj.is_active:
            return mark_safe(
                '<span style="background: #ef4444; color: white; padding: 2px 12px; '
                'border-radius: 20px; font-size: 12px;">⛔ Nofaol</span>'
            )
        if obj.start_time > now_time:
            return mark_safe(
                '<span style="background: #f59e0b; color: white; padding: 2px 12px; '
                'border-radius: 20px; font-size: 12px;">🔜 Kutilmoqda</span>'
            )
        if obj.end_time < now_time:
            return mark_safe(
                '<span style="background: #ef4444; color: white; padding: 2px 12px; '
                'border-radius: 20px; font-size: 12px;">✅ Yakunlangan</span>'
            )
        return mark_safe(
            '<span style="background: #22c55e; color: white; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">▶️ Davom etmoqda</span>'
        )
    
    @display(description="Savollar")
    def question_count_display(self, obj):
        count = obj.questions.count()
        return format_html(
            '<span style="background: #3b82f6; color: white; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">📝 {}</span>',
            count
        )
    
    @display(description="Seanslar")
    def sessions_count_display(self, obj):
        count = obj.sessions.count()
        return format_html(
            '<span style="background: #8b5cf6; color: white; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">⏱️ {}</span>',
            count
        )
    
    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")
    
    # ========== CHANGELIST VIEW ==========
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        total_tests = Test.objects.count()
        active_tests = Test.objects.filter(is_active=True).count()
        inactive_tests = Test.objects.filter(is_active=False).count()
        
        now_time = now()
        upcoming = Test.objects.filter(is_active=True, start_time__gt=now_time).count()
        ongoing = Test.objects.filter(is_active=True, start_time__lte=now_time, end_time__gte=now_time).count()
        ended = Test.objects.filter(is_active=True, end_time__lt=now_time).count()
        
        total_sessions = TestSession.objects.count()
        completed_sessions = TestSession.objects.filter(status=TestSession.Status.COMPLETED).count()
        
        extra_context.update({
            'total_tests': total_tests,
            'active_tests': active_tests,
            'inactive_tests': inactive_tests,
            'upcoming_count': upcoming,
            'ongoing_count': ongoing,
            'ended_count': ended,
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
        })
        
        return super().changelist_view(request, extra_context=extra_context)


# ==================== QUESTION ADMIN ====================

@admin.register(Question)
class QuestionAdmin(BaseOwnerAdmin):
    list_display = (
        'text_preview',
        'difficulty_badge',
        'test_display',
        'lesson_display',
        'xp_display',
        'choices_count_display',
        'order_display',
    )
    
    list_filter = (
        'difficulty',
        'test',
        'lesson',
        'created_at',
    )
    
    search_fields = ('text', 'test__title', 'lesson__title')
    list_per_page = 30
    ordering = ('-id',)
    
    inlines = [ChoiceInline, UserResponseInline]
    
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }
    
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
    
    # ========== DISPLAY METHODS ==========
    
    @display(description="Savol matni")
    def text_preview(self, obj):
        return obj.text[:60] + "..." if len(obj.text) > 60 else obj.text
    
    @display(description="Qiyinchilik")
    def difficulty_badge(self, obj):
        colors = {
            'easy': ('#22c55e', '🟢 Oson'),
            'medium': ('#f59e0b', '🟡 O\'rta'),
            'hard': ('#ef4444', '🔴 Qiyin'),
        }
        color, label = colors.get(obj.difficulty, ('#6b7280', obj.difficulty))
        return mark_safe(
            f'<span style="color: {color}; font-weight: 600;">{label}</span>'
        )
    difficulty_badge.admin_order_field = 'difficulty'
    
    @display(description="Test")
    def test_display(self, obj):
        if obj.test:
            return format_html(
                '<a href="/admin/quizs/test/{}/change/" style="color: #3b82f6;">📝 {}</a>',
                obj.test.id, obj.test.title[:30]
            )
        return "—"
    
    @display(description="Darslik")
    def lesson_display(self, obj):
        if obj.lesson:
            return format_html(
                '<a href="/admin/courses/lesson/{}/change/" style="color: #10b981;">📘 {}</a>',
                obj.lesson.id, obj.lesson.title[:30]
            )
        return "—"
    
    @display(description="XP")
    def xp_display(self, obj):
        return format_html(
            '<span style="background: #8b5cf6; color: white; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px; font-weight: 600;">⚡ {}</span>',
            obj.xp
        )
    
    @display(description="Variantlar")
    def choices_count_display(self, obj):
        count = obj.choices.count()
        return format_html(
            '<span style="background: #f1f5f9; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">🔘 {}</span>',
            count
        )
    
    @display(description="Tartib")
    def order_display(self, obj):
        return format_html(
            '<span style="color: #94a3b8; font-size: 13px;">#{}</span>',
            obj.order or 0
        )


# ==================== CHOICE ADMIN ====================

@admin.register(Choice)
class ChoiceAdmin(BaseOwnerAdmin):
    list_display = (
        'text_preview',
        'question_display',
        'is_correct_icon',
        'order_display',
    )
    
    list_filter = ('is_correct', 'question__difficulty')
    search_fields = ('text', 'question__text', 'explanation')
    list_per_page = 30
    ordering = ('-id',)
    
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }
    
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
    
    @display(description="Variant matni")
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    
    @display(description="Savol")
    def question_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/question/{}/change/" style="color: #3b82f6;">❓ {}</a>',
            obj.question.id, obj.question.text[:40]
        )
    
    @display(description="To'g'ri")
    def is_correct_icon(self, obj):
        if obj.is_correct:
            return mark_safe(
                '<span style="color: #22c55e; font-size: 18px;">✅</span>'
            )
        return mark_safe(
            '<span style="color: #ef4444; font-size: 18px;">❌</span>'
        )
    is_correct_icon.admin_order_field = 'is_correct'
    
    @display(description="Tartib")
    def order_display(self, obj):
        return format_html(
            '<span style="color: #94a3b8; font-size: 13px;">#{}</span>',
            obj.order or 0
        )


# ==================== TEST SESSION ADMIN ====================

@admin.register(TestSession)
class TestSessionAdmin(ModelAdmin):
    change_list_template = "admin/quiz/testsession_changelist.html"
    
    list_display = (
        'user_display',
        'test_display',
        'status_badge',
        'score_display',
        'xp_display',
        'accuracy_display',
        'started_at_formatted',
    )
    
    list_filter = (
        'status',
        'test',
        'started_at',
    )
    
    search_fields = ('user__username', 'user__full_name', 'test__title')
    list_per_page = 30
    ordering = ('-id',)
    autocomplete_fields = ('user', 'test')
    
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
    
    # ========== DISPLAY METHODS ==========
    
    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return [name, f"ID: {obj.user.telegram_id}"]
    
    @display(description="Test")
    def test_display(self, obj):
        return format_html(
            '<a href="/admin/quizs/test/{}/change/" style="color: #3b82f6;">📝 {}</a>',
            obj.test.id, obj.test.title[:40]
        )
    
    @display(description="Holat")
    def status_badge(self, obj):
        colors = {
            'in_progress': ('#3b82f6', '🔄 Jarayonda'),
            'completed': ('#22c55e', '✅ Yakunlangan'),
            'expired': ('#ef4444', '⏰ Muddati o\'tgan'),
        }
        color, label = colors.get(obj.status, ('#6b7280', obj.status))
        return mark_safe(
            f'<span style="background: {color}; color: white; padding: 2px 12px; '
            f'border-radius: 20px; font-size: 12px;">{label}</span>'
        )
    status_badge.admin_order_field = 'status'
    
    @display(description="Ball", ordering='score')
    def score_display(self, obj):
        try:
            score_value = float(obj.score) if obj.score is not None else 0.0
        except (ValueError, TypeError):
            score_value = 0.0
        score_string = f"{score_value:.2f}"
        return format_html(
            '<span style="font-weight: 600; color: #3b82f6;">{}</span>',
            score_string
        )
    
    @display(description="XP", ordering='total_xp_earned')
    def xp_display(self, obj):
        try:
            xp_value = int(obj.total_xp_earned) if obj.total_xp_earned is not None else 0
        except (ValueError, TypeError):
            xp_value = 0
        return format_html(
            '<span style="background: #8b5cf6; color: white; padding: 2px 12px; border-radius: 20px; font-size: 12px;">✨ {} XP</span>',
            xp_value
        )
        
    @display(description="Aniqlik (Accuracy)")
    def accuracy_display(self, obj):
        total = (obj.correct_count or 0) + (obj.wrong_count or 0) + (obj.unanswered_count or 0)
        if total > 0:
            acc = ((obj.correct_count or 0) / total) * 100
        else:
            acc = 0.0
        acc_string = f"{acc:.1f}%"
        return format_html(
            '<span style="font-weight: 500; color: #10b981;">{}</span>',
            acc_string
        )
    
    @display(description="Boshlangan vaqt", ordering='started_at')
    def started_at_formatted(self, obj):
        return obj.started_at.strftime("%d-%m-%Y %H:%M") if obj.started_at else "—"


# ==================== USER RESPONSE ADMIN ====================

@admin.register(UserResponse)
class UserResponseAdmin(ModelAdmin):
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
                return mark_safe(
                    '<span style="color: #22c55e; font-size: 18px;">✅</span>'
                )
            return mark_safe(
                '<span style="color: #ef4444; font-size: 18px;">❌</span>'
            )
        return mark_safe(
            '<span style="color: #94a3b8; font-size: 18px;">⏭️</span>'
        )
    
    @display(description="Yaratilgan")
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")