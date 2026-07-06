from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Submission

@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    # 1. BAZA OPTIMIZATSIYASI: Ustunlardagi bog'langan ma'lumotlarni bitta so'rovda yuklaydi
    list_select_related = ('user', 'problem', 'language')
    
    # 2. RO'YXAT SAHIFASI USTUNLARI
    list_display = (
        'id_display',
        'user_display',
        'problem_display',
        'language_badge',
        'verdict_badge',
        'progress_bar',
        'metrics_display',
        'submitted_at'
    )
    
    # 3. KUCHLI FILTRLAR (Unfold sidebar qismida chiroyli chiqadi)
    list_filter = (
        'verdict', 
        'status', 
        'language', 
        ('problem', admin.RelatedOnlyFieldListFilter)
    )
    
    # 4. TEZKOR QIDIRUV MAYDONLARI
    search_fields = ('user__username', 'problem__title', 'code')
    
    # Xavfsizlik uchun admin panelda yechimlarni qo'lda o'zgartirish taqiqlanadi
    readonly_fields = (
        'user', 'problem', 'language', 'code', 'status', 'verdict', 
        'passed_test_count', 'total_test_count', 'execution_time', 
        'execution_memory', 'test_results', 'submitted_at'
    )
    
    list_per_page = 25

    # 5. FORMANI GURUHLACH (Form View)
    fieldsets = (
        (_("🎯 Masala va Foydalanuvchi"), {
            'fields': (('user', 'problem', 'language'),),
        }),
        (_("💻 Yuborilgan Yechim"), {
            'fields': ('code',),
        }),
        (_("📊 Natija va Metrikalar"), {
            'fields': (('status', 'verdict'), ('passed_test_count', 'total_test_count'), ('execution_time', 'execution_memory')),
        }),
        (_("🧪 Batafsil Test Caselar (JSON)"), {
            'fields': ('test_results',),
            'classes': ('collapse',),
        }),
    )

    # ─── UNFOLD TAILWIND DESIGN COMPONENT BADGES ───

    @display(description=_("ID"), ordering='id')
    def id_display(self, obj):
        return format_html('<span class="font-bold text-gray-500 dark:text-gray-400">#{}</span>', obj.id)

    @display(description=_("Foydalanuvchi"), ordering='user__username')
    def user_display(self, obj):
        return format_html('<span class="font-medium text-gray-900 dark:text-gray-100">{}</span>', obj.user.username)

    @display(description=_("Masala"), ordering='problem__title')
    def problem_display(self, obj):
        return format_html(
            '<a href="/admin/problems/problem/{}/change/" class="text-primary-600 dark:text-primary-400 font-medium hover:underline">{}</a>',
            obj.problem.id, obj.problem.title
        )

    @display(description=_("Til"))
    def language_badge(self, obj):
        return format_html(
            '<span class="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 px-2 py-1 rounded text-xs font-mono border border-blue-200 dark:border-blue-800">{}</span>',
            obj.language.name
        )

    @display(description=_("Hukm (Verdict)"), ordering='verdict')
    def verdict_badge(self, obj):
        # Unfold Dark va Light rejimlari uchun Tailwind ranglar palitrasi
        colors = {
            "AC": "bg-success-50 text-success-700 border-success-200 dark:bg-success-900/30 dark:text-success-400 dark:border-success-800",
            "WA": "bg-danger-50 text-danger-700 border-danger-200 dark:bg-danger-900/30 dark:text-danger-400 dark:border-danger-800",
            "TLE": "bg-warning-50 text-warning-700 border-warning-200 dark:bg-warning-900/30 dark:text-warning-400 dark:border-warning-800",
            "MLE": "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800",
            "RE": "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800",
            "CE": "bg-gray-100 text-gray-700 border-gray-300 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700"
        }
        badge_style = colors.get(obj.verdict, "bg-gray-50 text-gray-700 border-gray-200")
        return format_html(
            '<span class="px-2 py-1 rounded text-xs font-bold border {}">{}</span>',
            badge_style, obj.get_verdict_display()
        )

    @display(description=_("Testlar"))
    def progress_bar(self, obj):
        color = "text-success-600 dark:text-success-400" if obj.status else "text-danger-600 dark:text-danger-400"
        return format_html(
            '<span class="font-mono font-semibold {}">{}/{}</span>',
            color, obj.passed_test_count, obj.total_test_count
        )

    @display(description=_("Resurslar"))
    def metrics_display(self, obj):
        t = f"{obj.execution_time} ms" if obj.execution_time else "-"
        m = f"{obj.execution_memory} KB" if obj.execution_memory else "-"
        return format_html('<span class="text-xs text-gray-500 dark:text-gray-400 font-mono">⏱️ {} <br> 💾 {}</span>', t, m)
