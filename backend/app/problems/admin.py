# apps/problems/admin.py
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django import forms
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import display
from unfold.paginator import InfinitePaginator

from .models import (
    Category, Tags, Language, Problem, Hint, Challenge,
    Function, ExecutionTestCase, TestCase, Like
)


# ============================================
# BASE OWNER ADMIN (UNFOLD MODELADMIN)
# ============================================
class BaseOwnerAdmin(ModelAdmin):
    """Xavfsizlik klassi - owner ni avtomatik boshqaradi"""

    def _is_owner(self, request, obj):
        if obj is None:
            return True
        return obj.owner == request.user

    def _in_group(self, request, group_name):
        return request.user.groups.filter(name=group_name).exists()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
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
# INLINES (MASALA QO'SHISH SAHIFASI UCHUN)
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


class ExecutionTestCaseInline(TabularInline):
    model = ExecutionTestCase
    extra = 1
    fields = ('language', 'top_code', 'bottom_code')
    tab = True
    classes = ('collapse',)


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


# ============================================
# PROBLEM ADMIN
# ============================================

@admin.register(Problem)
class ProblemAdmin(BaseOwnerAdmin):
    paginator = InfinitePaginator
    show_full_result_count = False
    change_list_template = "admin/problem/problem_changelist.html"
    
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
        'difficulty',
        'is_active',
        'category',
        'language',
        'tags',
    )
    
    search_fields = ('title', 'slug', 'description', 'category__name')
    list_editable = ('is_active',)
    list_per_page = 25
    ordering = ('-id',)
    prepopulated_fields = {'slug': ('title',)}
    
    inlines = [
        HintInline,
        ChallengeInline,
        FunctionInline,
        ExecutionTestCaseInline,
        TestCaseInline,
        LikeInline,
    ]
    
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }
    
    fieldsets = (
        ("📌 Asosiy Ma'lumotlar", {
            'fields': (
                ('title', 'slug'),
                ('category', 'lesson'),
                'description',
                'is_active',
            )
        }),
        ("🎯 Qiyinchilik va Mukofot", {
            'fields': (
                ('difficulty', 'xp'),
                ('contest',),
            ),
        }),
        ("🏷️ Teglar va Tillar", {
            'fields': (
                'tags',
                'language',
            ),
        }),
        ("⏱️ Cheklovlar", {
            'fields': (
                ('time_limit', 'memory_limit'),
            ),
        }),
        ("🎬 Video Yechim", {
            'fields': ('solution_video',),
            'classes': ('collapse',),
        }),
        ("📊 Statistika", {
            'fields': (
                ('likes_count', 'dislikes_count'),
            ),
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
        return mark_safe(
            f'<span style="color: {color}; font-weight: 600;">{label}</span>'
        )
    difficulty_badge.admin_order_field = 'difficulty'
    
    @display(description="Kategoriya")
    def category_display(self, obj):
        if obj.category:
            return format_html(
                '<span style="background: #f1f5f9; padding: 2px 12px; '
                'border-radius: 20px; font-size: 12px;">📁 {}</span>',
                obj.category.name
            )
        return "—"
    
    @display(description="Darslik")
    def lesson_display(self, obj):
        if obj.lesson:
            return format_html(
                '<span style="background: #e0f2fe; padding: 2px 12px; '
                'border-radius: 20px; font-size: 12px;">📘 {}</span>',
                obj.lesson.title[:20]
            )
        return "—"
    
    @display(description="XP")
    def xp_display(self, obj):
        return format_html(
            '<span style="background: #8b5cf6; color: white; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px; font-weight: 600;">⚡ {}</span>',
            obj.xp
        )
    
    @display(description="Reaksiyalar")
    def likes_display(self, obj):
        return format_html(
            '<span style="display: flex; gap: 8px; font-size: 13px;">'
            '<span style="color: #22c55e;">👍 {}</span>'
            '<span style="color: #ef4444;">👎 {}</span>'
            '</span>',
            obj.likes_count, obj.dislikes_count
        )
    
    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        if obj.owner:
            name = obj.owner.get_full_name() or obj.owner.username
            return format_html(
                '<span style="font-weight: 500;">{}</span>',
                name
            )
        return "—"
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        total_problems = Problem.objects.count()
        active_problems = Problem.objects.filter(is_active=True).count()
        inactive_problems = Problem.objects.filter(is_active=False).count()
        
        easy_count = Problem.objects.filter(difficulty='easy').count()
        medium_count = Problem.objects.filter(difficulty='medium').count()
        hard_count = Problem.objects.filter(difficulty='hard').count()
        
        extra_context.update({
            'total_problems': total_problems,
            'active_problems': active_problems,
            'inactive_problems': inactive_problems,
            'easy_count': easy_count,
            'medium_count': medium_count,
            'hard_count': hard_count,
        })
        
        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# CATEGORY ADMIN
# ============================================

@admin.register(Category)
class CategoryAdmin(BaseOwnerAdmin):
    list_display = ('name_display', 'problems_count_display', 'owner_display')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 25
    ordering = ('name',)
    
    fieldsets = (
        ("📁 Kategoriya", {
            'fields': (('name', 'slug'),),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )
    
    @display(description="Kategoriya", header=True)
    def name_display(self, obj):
        return [obj.name, f"Slug: {obj.slug}"]
    
    @display(description="Masalalar")
    def problems_count_display(self, obj):
        return obj.problems.count()
    
    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"


# ============================================
# TAGS ADMIN
# ============================================

@admin.register(Tags)
class TagsAdmin(BaseOwnerAdmin):
    list_display = ('name_display', 'problems_count_display', 'owner_display')
    search_fields = ('name',)
    list_per_page = 25
    ordering = ('name',)
    
    fieldsets = (
        ("🏷️ Teg", {
            'fields': ('name',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )
    
    @display(description="Teg", header=True)
    def name_display(self, obj):
        return [obj.name, f"ID: #{obj.id}"]
    
    @display(description="Masalalar")
    def problems_count_display(self, obj):
        return obj.problems.count()
    
    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"


# ============================================
# LANGUAGE ADMIN
# ============================================

@admin.register(Language)
class LanguageAdmin(ModelAdmin):
    list_display = ('name_display', 'version_display', 'problems_count_display' )
    search_fields = ('name', 'version')
    list_per_page = 25
    ordering = ('name',)
    
    fieldsets = (
        ("💻 Til", {
            'fields': (('name', 'version'),),
        }),
    )
    
    @display(description="Til", header=True)
    def name_display(self, obj):
        return [obj.name, f"Id: {obj.id}"]
    
    @display(description="Versiya")
    def version_display(self, obj):
        return obj.version
    
    @display(description="Masalalar")
    def problems_count_display(self, obj):
        return obj.problems.count()
    


# ============================================
# HINT ADMIN (YORDAMLAR)
# ============================================

@admin.register(Hint)
class HintAdmin(BaseOwnerAdmin):
    list_display = ('problem_display', 'text_preview', 'owner_display')
    search_fields = ('problem__title', 'text')
    list_filter = ('problem',)
    list_per_page = 30
    ordering = ('-id',)
    
    fieldsets = (
        ("🔑 Yordam", {
            'fields': ('problem', 'text'),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
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


# ============================================
# CHALLENGE ADMIN (TOPSHIRIQLAR)
# ============================================

@admin.register(Challenge)
class ChallengeAdmin(BaseOwnerAdmin):
    list_display = ('problem_display', 'text_preview', 'owner_display')
    search_fields = ('problem__title', 'text')
    list_filter = ('problem',)
    list_per_page = 30
    ordering = ('-id',)
    
    fieldsets = (
        ("🎯 Topshiriq", {
            'fields': ('problem', 'text'),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
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


# ============================================
# FUNCTION ADMIN (FUNKSIYA SHABLONLARI)
# ============================================

@admin.register(Function)
class FunctionAdmin(BaseOwnerAdmin):
    list_display = ('problem_display', 'language_display', 'function_preview', 'owner_display')
    search_fields = ('problem__title', 'language__name', 'function')
    list_filter = ('problem', 'language')
    list_per_page = 30
    ordering = ('-id',)
    
    fieldsets = (
        ("🧩 Funksiya Shabloni", {
            'fields': (('problem', 'language'), 'function'),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
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
            '<span style="background: #f1f5f9; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">💻 {}</span>',
            obj.language.name
        )
    
    @display(description="Shablon")
    def function_preview(self, obj):
        return obj.function[:50] + "..." if len(obj.function) > 50 else obj.function
    
    @display(description="Yaratuvchi")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner else "-"


# ============================================
# EXECUTION TEST CASE ADMIN (KOD TESTLARI)
# ============================================

@admin.register(ExecutionTestCase)
class ExecutionTestCaseAdmin(BaseOwnerAdmin):
    list_display = ('problem_display', 'language_display', 'top_code_preview', 'owner_display')
    search_fields = ('problem__title', 'language__name')
    list_filter = ('problem', 'language')
    list_per_page = 30
    ordering = ('-id',)
    
    fieldsets = (
        ("🚀 Kod Testi", {
            'fields': (('problem', 'language'), 'top_code', 'bottom_code'),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
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
            '<span style="background: #f1f5f9; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">💻 {}</span>',
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


# ============================================
# TEST CASE ADMIN (TEST CASELAR)
# ============================================


@admin.register(TestCase)
class TestCaseAdmin(BaseOwnerAdmin):  # UnfoldAdmin ishlatsangiz: class TestCaseAdmin(UnfoldAdmin)
    # 1. N+1 muammosini oldini olish uchun tezkor yuklash
    list_select_related = ('problem', 'owner')
    
    # 2. Ro'yxatda ko'rinadigan ustunlar
    list_display = (
        'order_display', 
        'problem_display', 
        'is_sample', 
        'input_preview', 
        'output_preview', 
        'owner_display'
    )
    
    list_display_links = ('order_display', 'problem_display')
    
    # Ro'yxatning o'zida turib tezkor almashtirish (Unfold toggle chiroyli chiqadi)
    list_editable = ('is_sample',)
    
    # 3. Unfold uslubidagi aqlli filtrlar
    list_filter = (
        'is_sample',
        ('problem', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = ('problem__title', 'problem__slug', 'input_txt', 'output_txt')
    list_per_page = 30
    ordering = ('problem', 'order', '-id')
    
    # Masalani tezkor qidirib topish uchun (ProblemAdmin ichida search_fields bo'lishi shart)
    autocomplete_fields = ('problem',)
    
    # 4. Unfold formatida formani guruhlash
    fieldsets = (
        ("🎯 Masala va Tartib", {
            'fields': (('problem', 'order', 'is_sample'),),
        }),
        ("🧪 Test Ma'lumotlari", {
            'fields': ('input_txt', 'output_txt', 'explanation'),
        }),
        ("👤 Ma'muriyat", {
            'fields': ('owner',),
            'classes': ('collapse',),
        }),
    )
    
    # --- UNFOLD DIZAYNIDAGI USTUNLAR ---
    
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
        # Unfold qorong'u (dark) va yorug' (light) rejimlari uchun Tailwind dizayni
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

    # 5. Yangi test qo'shilayotganda joriy adminni avtomatik biriktirish
    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

# ============================================
# LIKE ADMIN (REAKSIYALAR)
# ============================================

@admin.register(Like)
class LikeAdmin(BaseOwnerAdmin):
    list_display = ('problem_display', 'user_display', 'reaction_display')
    search_fields = ('problem__title', 'user__username', 'user__full_name')
    list_filter = ('like_or_dislike', 'problem')
    list_per_page = 30
    ordering = ('-id',)
    
    fieldsets = (
        ("👍 Reaksiya", {
            'fields': (('problem', 'user'), 'like_or_dislike'),
        }),
    )
    
    readonly_fields = ('problem', 'user', 'like_or_dislike')
    
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