import json
from django.contrib import admin
from django.db import models
from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncMonth
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
# Unfold ModelAdmin to'g'ridan-to'g'ri import qilinadi
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Submission  # Modelingiz yo'lini tekshiring


@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):  # 👈 TO'G'RILANDI: Toza Unfold ModelAdmin'dan foydalanamiz!
    # ─── 🎨 UNFOLD EKSKLYUZIV SOZLAMALARI ───
    list_before_template = "admin/submissions/submission/list_top.html"
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    list_per_page = 25
    ordering = ('-submitted_at',)
    
    # Baza optimizatsiyasi: N+1 so'rovlarni bitta SQL JOIN'ga jamlaydi
    list_select_related = ('user', 'problem', 'language')
    
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
    
    list_filter = (
        'verdict', 
        'status', 
        'language', 
        ('problem', admin.RelatedOnlyFieldListFilter)
    )
    
    search_fields = ('user__username', 'problem__title', 'code')
    
    # Xavfsizlik: Yechimlarni admin panelda qo'lda o'zgartirish mutlaqo taqiqlanadi
    readonly_fields = (
        'user', 'problem', 'language', 'code', 'status', 'verdict', 
        'passed_test_count', 'total_test_count', 'execution_time', 
        'execution_memory', 'test_results', 'submitted_at'
    )
    
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

    # ─── DISPLAY USTUN METODLARI (Xatoliklar va double formatting 100% tozalangan) ───

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

    # ─── 📊 CHANGELIST VIEW STATISTIKASI (AGGREGATE & TRUNC) ───
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)
        filtered_qs = cl.get_queryset(request)
        
        # Barcha ko'rsatkichlar bitta tezkor SQL so'rovga aggregate qilinadi
        stats = filtered_qs.aggregate(
            total_submissions=Count('id'),
            ac_count=Count('id', filter=Q(verdict='AC')),
            wa_count=Count('id', filter=Q(verdict='WA')),
            tle_count=Count('id', filter=Q(verdict='TLE')),
            other_count=Count('id', filter=~Q(verdict__in=['AC', 'WA', 'TLE'])),
            avg_time=Avg('execution_time')
        )
        
        # Oylik urinishlar dinamikasi (Chart.js chiziqli grafigi uchun)
        monthly_data = (
            filtered_qs.annotate(month=TruncMonth('submitted_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        
        chart_labels = []
        chart_values = []
        for item in monthly_data:
            if item['month']:
                chart_labels.append(item['month'].strftime('%Y-%m'))
                chart_values.append(int(item['count'] or 0))

        # Raqamlarni xavfsiz formatlaymiz (Format xatoligiga qarshi qat'iy float yoki string)
        avg_time_val = stats['avg_time'] or 0.0
        avg_time_str = f"{avg_time_val:.1f}"

        extra_context.update({
            'total_submissions': stats['total_submissions'] or 0,
            'ac_count': stats['ac_count'] or 0,
            'wa_count': stats['wa_count'] or 0,
            'tle_count': stats['tle_count'] or 0,
            'other_count': stats['other_count'] or 0,
            'avg_time': avg_time_str,  # f-string formatlash muammosiz string ko'rinishida o'tadi
            'chart_labels_json': json.dumps(chart_labels),
            'chart_values_json': json.dumps(chart_values),
        })
        return super().changelist_view(request, extra_context=extra_context)
