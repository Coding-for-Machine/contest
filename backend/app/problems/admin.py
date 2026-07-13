import json

from django.contrib import admin
from django.db import models
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django import forms
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import display
from unfold.paginator import InfinitePaginator
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    MultipleChoicesDropdownFilter,
    RelatedDropdownFilter,
    MultipleRelatedDropdownFilter,
    DropdownFilter,
    MultipleDropdownFilter
)

from .models import (
    Category, Tags, Language, Problem, Hint, Challenge,
    Function, ExecutionTestCase, TestCase, Like
)


CHART_COLORS = {
    "easy": "#22c55e",
    "medium": "#f59e0b",
    "hard": "#ef4444",
    "primary": "#8b5cf6",
    "blue": "#3b82f6",
}



class DifficultyDropdownFilter(DropdownFilter):
    """Qiyinchilik bo'yicha maxsus filtr"""
    title = _("Qiyinchilik darajasi")
    parameter_name = "difficulty"

    def lookups(self, request, model_admin):
        return [
            ("easy", _("🟢 Oson")),
            ("medium", _("🟡 O'rtacha")),
            ("hard", _("🔴 Qiyin")),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(difficulty=self.value())
        return queryset


class ReactionDropdownFilter(DropdownFilter):
    """Reaksiya turi bo'yicha filtr"""
    title = _("Reaksiya turi")
    parameter_name = "like_or_dislike"

    def lookups(self, request, model_admin):
        return [
            ("1", _("👍 Like")),
            ("0", _("👎 Dislike")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(like_or_dislike=True)
        elif self.value() == "0":
            return queryset.filter(like_or_dislike=False)
        return queryset


class SampleDropdownFilter(DropdownFilter):
    """Test turi bo'yicha filtr"""
    title = _("Test turi")
    parameter_name = "is_sample"

    def lookups(self, request, model_admin):
        return [
            ("1", _("📝 Namuna")),
            ("0", _("🔒 Yashirin")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(is_sample=True)
        elif self.value() == "0":
            return queryset.filter(is_sample=False)
        return queryset
    
# ============================================
# BASE OWNER ADMIN
# ============================================
class BaseOwnerAdmin(ModelAdmin):
    """Xavfsizlik klassi - owner ni avtomatik boshqaradi."""
    list_filter_submit = True
    list_per_page = 20
    show_full_result_count = False
    select_related_fields = ()

    def _is_owner(self, request, obj):
        if obj is None:
            return True
        return obj.owner == request.user

    def _in_group(self, request, group_name):
        return request.user.groups.filter(name=group_name).exists()

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)

        if request.user.is_superuser:
            return qs
        if self._in_group(request, "O'qituvchi"):
            return qs.filter(owner=request.user)
        if self._in_group(request, "Moderator"):
            return qs
        if self._in_group(request, "Kontent Menejer"):
            return qs
        if request.user.is_staff:
            return qs.filter(owner=request.user)
        return qs.none()

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if self._in_group(request, "Moderator"):
            return False
        if self._in_group(request, "O'qituvchi"):
            if obj is None:
                return True
            return self._is_owner(request, obj)
        if self._in_group(request, "Kontent Menejer"):
            return True
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if self._in_group(request, "Moderator"):
            return False
        if self._in_group(request, "O'qituvchi"):
            if obj is None:
                return False
            return self._is_owner(request, obj)
        if self._in_group(request, "Kontent Menejer"):
            return False
        return super().has_delete_permission(request, obj)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        if self._in_group(request, "Moderator"):
            return False
        if self._in_group(request, "O'qituvchi"):
            return True
        if self._in_group(request, "Kontent Menejer"):
            return True
        return super().has_add_permission(request)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if hasattr(form, 'base_fields') and 'owner' in form.base_fields:
            form.base_fields['owner'].widget = forms.HiddenInput()
            form.base_fields['owner'].required = False
        return form

    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        else:
            if not request.user.is_superuser:
                try:
                    old_obj = self.model.objects.get(pk=obj.pk)
                    obj.owner = old_obj.owner
                except self.model.DoesNotExist:
                    obj.owner = request.user
        super().save_model(request, obj, form, change)


# ============================================
# UMUMIY MIXIN: "child" modellar uchun statistika
# ============================================
class ChildStatsMixin:
    """
    Hint/Challenge/Function/ExecutionTestCase/TestCase/Like kabi Problem'ga
    bog'liq modellar uchun umumiy list_before_template mexanizmi.
    Har bir admin faqat `get_child_stats()` ni override qiladi —
    changelist_view boilerplate takrorlanmaydi.
    """
    list_before_template = "admin/problem/child_stats_before_list.html"

    def get_child_stats(self, request):
        """[{"icon": "...", "label": "...", "value": N, "color": "primary"}]"""
        return []

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["child_stats"] = self.get_child_stats(request)
        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# INLINES
# ============================================

class HintInline(TabularInline):
    model = Hint
    extra = 1
    fields = ('text',)
    tab = True
    classes = ('collapse',)


class ChallengeInline(TabularInline):
    model = Challenge
    extra = 1
    fields = ('text',)
    tab = True
    classes = ('collapse',)


class FunctionInline(TabularInline):
    model = Function
    extra = 1
    fields = ('language', 'function')
    tab = True
    classes = ('collapse',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('language')


class ExecutionTestCaseInline(TabularInline):
    model = ExecutionTestCase
    extra = 1
    fields = ('language', 'top_code', 'bottom_code')
    tab = True
    classes = ('collapse',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('language')


class TestCaseInline(TabularInline):
    model = TestCase
    extra = 2
    fields = ('input_txt', 'output_txt')
    tab = True
    classes = ('collapse',)


class LikeInline(TabularInline):
    model = Like
    extra = 0
    fields = ('user', 'like_or_dislike')
    readonly_fields = ('user',)
    tab = True
    classes = ('collapse',)
    can_delete = False
    max_num = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# ============================================
# PROBLEM ADMIN — asosiy dashboard
# ============================================

@admin.register(Problem)
class ProblemAdmin(BaseOwnerAdmin):
    paginator = InfinitePaginator
    show_full_result_count = False

    list_before_template = "admin/problem/problem_stats_before_list.html"
    select_related_fields = ("category", "lesson", "owner")

    list_display = (
        'title_display',
        'difficulty_badge',
        'category_display',
        'lesson_display',
        'is_active',
        'xp_display',
        'likes_display',
        'owner_display',
    )
    list_filter = (
        ('difficulty', ChoicesDropdownFilter),
        ('is_active', ChoicesDropdownFilter),
        ('category', RelatedDropdownFilter),
        ('language', MultipleRelatedDropdownFilter),
        ('tags', MultipleRelatedDropdownFilter),
        ('contest', RelatedDropdownFilter),  # Qo'shildi
        ('lesson', RelatedDropdownFilter),  # Qo'shildi
    )

    search_fields = ('title', 'slug', 'description', 'category__name')
    list_editable = ('is_active',)
    list_display_links = ('title_display',)
    list_per_page = 25
    ordering = ('-id',)
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('category', 'lesson', 'owner')

    inlines = [
        HintInline, ChallengeInline, FunctionInline,
        ExecutionTestCaseInline, TestCaseInline, LikeInline,
    ]

    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }

    fieldsets = (
        ("📌 Asosiy Ma'lumotlar", {
            'fields': (('title', 'slug'), ('category', 'lesson'), 'description', 'is_active'),
        }),
        ("🎯 Qiyinchilik va Mukofot", {
            'fields': (('difficulty', 'xp'), ('contest',)),
        }),
        ("🏷️ Teglar va Tillar", {
            'fields': ('tags', 'language'),
        }),
        ("⏱️ Cheklovlar", {
            'fields': (('time_limit', 'memory_limit'),),
        }),
        ("🎬 Video Yechim", {
            'fields': ('solution_video',),
            'classes': ('collapse',),
        }),
        ("📊 Statistika", {
            'fields': (('likes_count', 'dislikes_count'),),
            'classes': ('collapse',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('likes_count', 'dislikes_count')

    @display(description="Masala nomi", header=True)
    def title_display(self, obj):
        return [obj.title[:50], f"ID: #{obj.id}"]

    @display(description="Qiyinchilik")
    def difficulty_badge(self, obj):
        colors = {
            'easy': ('#22c55e', '🟢 Oson'),
            'medium': ('#f59e0b', '🟡 O\'rta'),
            'hard': ('#ef4444', '🔴 Qiyin'),
        }
        color, label = colors.get(obj.difficulty, ('#6b7280', obj.difficulty))
        return mark_safe(f'<span style="color: {color}; font-weight: 600;">{label}</span>')
    difficulty_badge.admin_order_field = 'difficulty'

    @display(description="Kategoriya")
    def category_display(self, obj):
        if obj.category:
            return format_html(
                '<span style="background: #f1f5f9; padding: 2px 12px; border-radius: 20px; font-size: 12px;">📁 {}</span>',
                obj.category.name
            )
        return "—"

    @display(description="Darslik")
    def lesson_display(self, obj):
        if obj.lesson:
            return format_html(
                '<span style="background: #e0f2fe; padding: 2px 12px; border-radius: 20px; font-size: 12px;">📘 {}</span>',
                obj.lesson.title[:20]
            )
        return "—"

    @display(description="XP")
    def xp_display(self, obj):
        return format_html(
            '<span style="background: #8b5cf6; color: white; padding: 2px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">⚡ {}</span>',
            obj.xp
        )

    @display(description="Reaksiyalar")
    def likes_display(self, obj):
        return format_html(
            '<span style="display: flex; gap: 8px; font-size: 13px;">'
            '<span style="color: #22c55e;">👍 {}</span>'
            '<span style="color: #ef4444;">👎 {}</span></span>',
            obj.likes_count, obj.dislikes_count
        )

    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        if obj.owner:
            name = obj.owner.get_full_name() or obj.owner.username
            return format_html('<span style="font-weight: 500;">{}</span>', name)
        return "—"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        stats = Problem.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            inactive=Count('id', filter=Q(is_active=False)),
            easy=Count('id', filter=Q(difficulty='easy')),
            medium=Count('id', filter=Q(difficulty='medium')),
            hard=Count('id', filter=Q(difficulty='hard')),
        )
        total = stats['total'] or 0

        def pct(count):
            return round((count / total) * 100, 1) if total else 0

        avg_xp = 0
        if total:
            from django.db.models import Avg
            avg_xp = round(Problem.objects.aggregate(avg=Avg('xp'))['avg'] or 0)

        # Top 6 kategoriya — bitta annotate query bilan
        top_categories = (
            Category.objects.annotate(problems_total=Count('problems'))
            .filter(problems_total__gt=0)
            .order_by('-problems_total')[:6]
        )
        top_categories_rows = [[c.name, c.problems_total] for c in top_categories]

        extra_context.update({
            'total_problems': total,
            'active_problems': stats['active'],
            'inactive_problems': stats['inactive'],
            'easy_count': stats['easy'],
            'medium_count': stats['medium'],
            'hard_count': stats['hard'],
            'easy_percent': pct(stats['easy']),
            'medium_percent': pct(stats['medium']),
            'hard_percent': pct(stats['hard']),
            'avg_xp': avg_xp,
            'difficulty_chart_data': json.dumps({
                'labels': ["Oson", "O'rta", "Qiyin"],
                'datasets': [{
                    'data': [stats['easy'], stats['medium'], stats['hard']],
                    'backgroundColor': [CHART_COLORS['easy'], CHART_COLORS['medium'], CHART_COLORS['hard']],
                    'borderWidth': 0,
                }],
            }),
            'top_categories_table': {
                'headers': ["Kategoriya", "Masalalar soni"],
                'rows': top_categories_rows,
            },
        })

        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# CATEGORY ADMIN
# ============================================

@admin.register(Category)
class CategoryAdmin(BaseOwnerAdmin):
    select_related_fields = ("owner",)
    list_before_template = "admin/problem/category_stats_before_list.html"

    list_display = ('name_display', 'problems_count_display', 'owner_display')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 25
    ordering = ('name',)

    fieldsets = (
        ("📁 Kategoriya", {'fields': (('name', 'slug'),)}),
        ("👤 Yaratuvchi", {'fields': ('owner',), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _problems_count=Count('problems', distinct=True)
        )

    @display(description="Kategoriya", header=True)
    def name_display(self, obj):
        return [obj.name, f"Slug: {obj.slug}"]

    @display(description="Masalalar")
    def problems_count_display(self, obj):
        return obj._problems_count
    problems_count_display.admin_order_field = '_problems_count'

    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        categories = (
            Category.objects.annotate(problems_total=Count('problems'))
            .order_by('-problems_total')
        )
        top = categories.first()

        extra_context.update({
            'total_categories': categories.count(),
            'total_problems_in_categories': sum(c.problems_total for c in categories),
            'top_category_name': top.name if top and top.problems_total else None,
            'category_chart_data': json.dumps({
                'labels': [c.name[:15] for c in categories[:8]],
                'datasets': [{
                    'data': [c.problems_total for c in categories[:8]],
                    'backgroundColor': CHART_COLORS['primary'],
                    'borderRadius': 6,
                }],
            }) if categories.exists() else None,
        })

        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# TAGS ADMIN
# ============================================

@admin.register(Tags)
class TagsAdmin(BaseOwnerAdmin):
    select_related_fields = ("owner",)
    list_before_template = "admin/problem/tags_stats_before_list.html"
    list_display = ('name_display', 'problems_count_display', 'owner_display')
    
    search_fields = ('name',)
    list_per_page = 25
    ordering = ('name',)

    fieldsets = (
        ("🏷️ Teg", {'fields': ('name',)}),
        ("👤 Yaratuvchi", {'fields': ('owner',), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _problems_count=Count('problems', distinct=True)
        )

    @display(description="Teg", header=True)
    def name_display(self, obj):
        return [obj.name, f"ID: #{obj.id}"]

    @display(description="Masalalar")
    def problems_count_display(self, obj):
        return obj._problems_count
    problems_count_display.admin_order_field = '_problems_count'

    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        tags = Tags.objects.annotate(problems_total=Count('problems')).order_by('-problems_total')
        top = tags.first()

        extra_context.update({
            'total_tags': tags.count(),
            'tagged_problems_count': Problem.objects.filter(tags__isnull=False).distinct().count(),
            'top_tag_name': top.name if top and top.problems_total else None,
        })

        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# LANGUAGE ADMIN
# ============================================

@admin.register(Language)
class LanguageAdmin(ModelAdmin):
    list_before_template = "admin/problem/language_stats_before_list.html"

    list_display = ('name_display', 'version_display', 'problems_count_display')
    search_fields = ('name', 'version')
    list_per_page = 25
    ordering = ('name',)

    fieldsets = (
        ("💻 Til", {'fields': (('name', 'version'),)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _problems_count=Count('problems', distinct=True)
        )

    @display(description="Til", header=True)
    def name_display(self, obj):
        return [obj.name, f"Id: {obj.id}"]

    @display(description="Versiya")
    def version_display(self, obj):
        return obj.version

    @display(description="Masalalar")
    def problems_count_display(self, obj):
        return obj._problems_count
    problems_count_display.admin_order_field = '_problems_count'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        languages = Language.objects.annotate(problems_total=Count('problems')).order_by('-problems_total')
        top = languages.first()

        extra_context.update({
            'total_languages': languages.count(),
            'most_used_language_name': top.name if top and top.problems_total else None,
            'most_used_language_count': top.problems_total if top else 0,
        })

        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# HINT ADMIN
# ============================================

@admin.register(Hint)
class HintAdmin(ChildStatsMixin, BaseOwnerAdmin):
    select_related_fields = ("problem", "owner")

    list_display = ('problem_display', 'text_preview', 'owner_display')
    search_fields = ('problem__title', 'text')
    list_filter = (
        ('problem', RelatedDropdownFilter),
    )
    ordering = ('-id',)
    autocomplete_fields = ('problem',)

    fieldsets = (
        ("🔑 Yordam", {'fields': ('problem', 'text')}),
        ("👤 Yaratuvchi", {'fields': ('owner',), 'classes': ('collapse',)}),
    )

    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }

    @display(description="Masala")
    def problem_display(self, obj):
        return format_html(
            '<a href="/admin/problems/problem/{}/change/" style="color: #3b82f6;">💡 {}</a>',
            obj.problem.id, obj.problem.title[:40]
        )

    @display(description="Yordam matni")
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"

    def get_child_stats(self, request):
        qs = self.get_queryset(request)
        return [
            {"icon": "lightbulb", "label": _("Jami yordamlar"), "value": qs.count(), "color": "primary"},
            {"icon": "quiz", "label": _("Yordami bor masalalar"),
             "value": qs.values('problem').distinct().count(), "color": "blue"},
        ]


# ============================================
# CHALLENGE ADMIN
# ============================================

@admin.register(Challenge)
class ChallengeAdmin(ChildStatsMixin, BaseOwnerAdmin):
    select_related_fields = ("problem", "owner")

    list_display = ('problem_display', 'text_preview', 'owner_display')
    search_fields = ('problem__title', 'text')
    list_filter = (
        ('problem', RelatedDropdownFilter),
    )
    ordering = ('-id',)
    autocomplete_fields = ('problem',)

    fieldsets = (
        ("🎯 Topshiriq", {'fields': ('problem', 'text')}),
        ("👤 Yaratuvchi", {'fields': ('owner',), 'classes': ('collapse',)}),
    )

    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }

    @display(description="Masala")
    def problem_display(self, obj):
        return format_html(
            '<a href="/admin/problems/problem/{}/change/" style="color: #3b82f6;">💡 {}</a>',
            obj.problem.id, obj.problem.title[:40]
        )

    @display(description="Qo'shimcha shart")
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"

    def get_child_stats(self, request):
        qs = self.get_queryset(request)
        return [
            {"icon": "flag", "label": _("Jami topshiriqlar"), "value": qs.count(), "color": "primary"},
            {"icon": "quiz", "label": _("Topshirig'i bor masalalar"),
             "value": qs.values('problem').distinct().count(), "color": "blue"},
        ]


# ============================================
# FUNCTION ADMIN
# ============================================

@admin.register(Function)
class FunctionAdmin(ChildStatsMixin, BaseOwnerAdmin):
    select_related_fields = ("problem", "language", "owner")

    list_display = ('problem_display', 'language_display', 'function_preview', 'owner_display')
    search_fields = ('problem__title', 'language__name', 'function')
    list_filter = (
        ('problem', RelatedDropdownFilter),
        ('language', RelatedDropdownFilter),
    )
    ordering = ('-id',)
    autocomplete_fields = ('problem', 'language')

    fieldsets = (
        ("🧩 Funksiya Shabloni", {'fields': (('problem', 'language'), 'function')}),
        ("👤 Yaratuvchi", {'fields': ('owner',), 'classes': ('collapse',)}),
    )

    @display(description="Masala")
    def problem_display(self, obj):
        return format_html(
            '<a href="/admin/problems/problem/{}/change/" style="color: #3b82f6;">💡 {}</a>',
            obj.problem.id, obj.problem.title[:30]
        )

    @display(description="Til")
    def language_display(self, obj):
        return format_html(
            '<span style="background: #f1f5f9; padding: 2px 12px; border-radius: 20px; font-size: 12px;">💻 {}</span>',
            obj.language.name
        )

    @display(description="Shablon")
    def function_preview(self, obj):
        return obj.function[:50] + "..." if len(obj.function) > 50 else obj.function

    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"

    def get_child_stats(self, request):
        qs = self.get_queryset(request)
        return [
            {"icon": "functions", "label": _("Jami shablonlar"), "value": qs.count(), "color": "primary"},
            {"icon": "translate", "label": _("Qamrab olingan tillar"),
             "value": qs.values('language').distinct().count(), "color": "blue"},
        ]


# ============================================
# EXECUTION TEST CASE ADMIN
# ============================================

@admin.register(ExecutionTestCase)
class ExecutionTestCaseAdmin(ChildStatsMixin, BaseOwnerAdmin):
    select_related_fields = ("problem", "language", "owner")

    list_display = ('problem_display', 'language_display', 'top_code_preview', 'owner_display')
    search_fields = ('problem__title', 'language__name')
    list_filter = (
        ('problem', RelatedDropdownFilter),
        ('language', RelatedDropdownFilter),
    )
    ordering = ('-id',)
    autocomplete_fields = ('problem', 'language')

    fieldsets = (
        ("🚀 Kod Testi", {'fields': (('problem', 'language'), 'top_code', 'bottom_code')}),
        ("👤 Yaratuvchi", {'fields': ('owner',), 'classes': ('collapse',)}),
    )

    @display(description="Masala")
    def problem_display(self, obj):
        return format_html(
            '<a href="/admin/problems/problem/{}/change/" style="color: #3b82f6;">💡 {}</a>',
            obj.problem.id, obj.problem.title[:30]
        )

    @display(description="Til")
    def language_display(self, obj):
        return format_html(
            '<span style="background: #f1f5f9; padding: 2px 12px; border-radius: 20px; font-size: 12px;">💻 {}</span>',
            obj.language.name
        )

    @display(description="Tepa kod")
    def top_code_preview(self, obj):
        if obj.top_code:
            return obj.top_code[:30] + "..." if len(obj.top_code) > 30 else obj.top_code
        return "—"

    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"

    def get_child_stats(self, request):
        qs = self.get_queryset(request)
        return [
            {"icon": "terminal", "label": _("Jami kod testlari"), "value": qs.count(), "color": "primary"},
            {"icon": "translate", "label": _("Qamrab olingan tillar"),
             "value": qs.values('language').distinct().count(), "color": "blue"},
        ]


# ============================================
# TEST CASE ADMIN
# ============================================

@admin.register(TestCase)
class TestCaseAdmin(ChildStatsMixin, BaseOwnerAdmin):
    select_related_fields = ('problem', 'owner')
    list_filter_submit = True

    # ✅ list_display ga 'is_sample_badge' emas, 'is_sample' ni qo'shing
    list_display = (
        'order_display', 
        'problem_display', 
        'is_sample',  # ✅ 'is_sample_badge' emas, 'is_sample'
        'input_preview', 
        'output_preview', 
        'owner_display'
    )
    list_display_links = ('order_display', 'problem_display')
    list_editable = ('is_sample',)  # ✅ 'is_sample' list_display da bor
    list_per_page = 30
    ordering = ('problem', 'order', '-id')
    autocomplete_fields = ('problem',)
    
    # ✅ TO'G'RI list_filter formati
    list_filter = (
        SampleDropdownFilter,              # ✅ Custom filter - tuple ichida EMAS
        ('problem', RelatedDropdownFilter), # ✅ Unfold filter - tuple ichida
        ('owner', RelatedDropdownFilter),   # ✅ Unfold filter - tuple ichida
        ('is_sample', ChoicesDropdownFilter), # ✅ Qo'shimcha filter
    )
    
    search_fields = ('problem__title', 'problem__slug', 'input_txt', 'output_txt')

    fieldsets = (
        ("🎯 Masala va Tartib", {'fields': (('problem', 'order', 'is_sample'),)}),
        ("🧪 Test Ma'lumotlari", {'fields': ('input_txt', 'output_txt', 'explanation')}),
        ("👤 Ma'muriyat", {'fields': ('owner',), 'classes': ('collapse',)}),
    )

    @admin.display(description="№", ordering='order')
    def order_display(self, obj):
        return format_html(
            '<span class="font-bold text-gray-500 dark:text-gray-400">#{}</span>',
            obj.order if obj.order else obj.id
        )

    @admin.display(description="💡 Masala", ordering='problem__title')
    def problem_display(self, obj):
        title = obj.problem.title
        truncated_title = title[:30] + '...' if len(title) > 30 else title
        return format_html(
            '<a href="/admin/problems/problem/{}/change/" class="text-primary-600 dark:text-primary-400 font-medium hover:underline">{}</a>',
            obj.problem.id, truncated_title
        )

    @admin.display(description="📥 Input (Kirish)")
    def input_preview(self, obj):
        truncated = obj.input_txt[:25] + "..." if len(obj.input_txt) > 25 else obj.input_txt
        return format_html(
            '<code class="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 px-2 py-1 rounded text-xs font-mono border border-gray-200 dark:border-gray-700">{}</code>',
            truncated
        )

    @admin.display(description="📤 Output (Chiqish)")
    def output_preview(self, obj):
        truncated = obj.output_txt[:25] + "..." if len(obj.output_txt) > 25 else obj.output_txt
        return format_html(
            '<code class="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 px-2 py-1 rounded text-xs font-mono border border-gray-200 dark:border-gray-700">{}</code>',
            truncated
        )

    @admin.display(description="✍️ Yaratuvchi", ordering='owner__username')
    def owner_display(self, obj):
        if obj.owner:
            return format_html(
                '<span class="text-success-600 dark:text-success-400 font-medium">{}</span>',
                obj.owner.username
            )
        return "-"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

    def get_child_stats(self, request):
        qs = self.get_queryset(request)
        agg = qs.aggregate(
            total=Count('id'),
            sample=Count('id', filter=Q(is_sample=True)),
            hidden=Count('id', filter=Q(is_sample=False)),
        )
        return [
            {"icon": "science", "label": _("Jami test caselar"), "value": agg['total'], "color": "primary"},
            {"icon": "visibility", "label": _("Namunali (sample)"), "value": agg['sample'], "color": "green"},
            {"icon": "visibility_off", "label": _("Yashirin"), "value": agg['hidden'], "color": "red"},
        ]
# ============================================
# LIKE ADMIN
# ============================================

@admin.register(Like)
class LikeAdmin(ChildStatsMixin, ModelAdmin):
    select_related_fields = ("problem", "user")
    list_filter_submit = True

    list_display = ('problem_display', 'user_display', 'reaction_display')
    search_fields = ('problem__title', 'user__username', 'user__full_name')
    list_per_page = 30
    ordering = ('-id',)
    autocomplete_fields = ('problem', 'user')
    
    list_filter = (
        ReactionDropdownFilter,
        ('problem', RelatedDropdownFilter),
        ('user', RelatedDropdownFilter),
        ('like_or_dislike', ChoicesDropdownFilter),
    )

    fieldsets = (
        ("👍 Reaksiya", {
            'fields': (
                ('problem', 'user'),  # ✅ user ni readonly emas, formada ko'rsatish
                'like_or_dislike'
            )
        }),
    )

    readonly_fields = ('problem',)  # Agar problem ni o'zgartirishni xohlamasangiz

    def get_form(self, request, obj=None, **kwargs):
        """User ni avtomatik to'ldirish"""
        form = super().get_form(request, obj, **kwargs)
        if hasattr(form, 'base_fields') and 'user' in form.base_fields:
            form.base_fields['user'].initial = request.user
            form.base_fields['user'].widget = forms.HiddenInput()  # Yashirin qilish
        return form

    def save_model(self, request, obj, form, change):
        """Agar user berilmagan bo'lsa, current user ni qo'yish"""
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    @display(description="Masala")
    def problem_display(self, obj):
        return format_html(
            '<a href="/admin/problems/problem/{}/change/" style="color: #3b82f6;">💡 {}</a>',
            obj.problem.id, obj.problem.title[:30]
        )

    @display(description="Foydalanuvchi")
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return format_html(
            '<span style="font-weight: 500;">{}</span><br>'
            '<span style="font-size: 11px; color: #94a3b8;">ID: {}</span>',
            name, obj.user.telegram_id
        )

    @display(description="Reaksiya")
    def reaction_display(self, obj):
        if obj.like_or_dislike:
            return mark_safe(
                '<span style="background: #22c55e; color: white; padding: 2px 12px; '
                'border-radius: 20px; font-size: 12px;">👍 Like</span>'
            )
        return mark_safe(
            '<span style="background: #ef4444; color: white; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">👎 Dislike</span>'
        )

    def get_child_stats(self, request):
        qs = self.get_queryset(request)
        agg = qs.aggregate(
            total=Count('id'),
            likes=Count('id', filter=Q(like_or_dislike=True)),
            dislikes=Count('id', filter=Q(like_or_dislike=False)),
        )
        return [
            {"icon": "thumbs_up_down", "label": _("Jami reaksiyalar"), "value": agg['total'], "color": "primary"},
            {"icon": "thumb_up", "label": _("Layklar"), "value": agg['likes'], "color": "green"},
            {"icon": "thumb_down", "label": _("Dislayklar"), "value": agg['dislikes'], "color": "red"},
        ]