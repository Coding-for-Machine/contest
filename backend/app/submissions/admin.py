import json
from datetime import timedelta

from django.contrib import admin
from django.core.paginator import Paginator  # Oddiy raqamli pagination uchun
from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.paginator import InfinitePaginator  # "Yana yuklash" tugmasi uchun

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    # ─── UNFOLD SOZLAMALARI ───
    list_before_template = "admin/submissions/submission/list_top.html"
    list_filter_submit = True
    show_facets = admin.ShowFacets.NEVER
    ordering = ("-submitted_at",)
    date_hierarchy = "submitted_at"
    actions_selection_counter = True

    # ---------- PAGINATION SOZLAMALARI ----------
    # A) "Yana yuklash" (Load more) tugmasi — Unfold uslubi:
    paginator = InfinitePaginator
    # list_per_page = 25
    show_full_result_count = False   # COUNT(*) tezlashtirish uchun
    # list_max_show_all = 200

    # B) Oddiy raqamli pagination (sahifa 1, 2, 3...) kerak bo'lsa:
    #    yuqoridagi 4 qatorni o'chirib, quyidagini yoqing:
    # paginator = Paginator
    # show_full_result_count = True

    # N+1 oldini olish
    list_select_related = ("user", "problem", "language")

    list_display = (
        "id_display",
        "user_display",
        "problem_display",
        "language_badge",
        "verdict_badge",
        "progress_bar",
        "metrics_display",
        "submitted_at",
    )
    list_display_links = ("id_display", "problem_display")

    list_filter = (
        "verdict",
        "status",
        "language",
        ("problem", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = ("user__username", "problem__title", "code")

    readonly_fields = (
        "user", "problem", "language", "code_display", "status", "verdict",
        "passed_test_count", "total_test_count", "execution_time",
        "execution_memory", "test_results_display", "submitted_at",
    )
    exclude = ("code", "test_results")

    fieldsets = (
        (_("🎯 Masala va Foydalanuvchi"), {
            "fields": (("user", "problem", "language"),),
        }),
        (_("💻 Yuborilgan Yechim"), {
            "fields": ("code_display",),
        }),
        (_("📊 Natija va Metrikalar"), {
            "fields": (
                ("status", "verdict"),
                ("passed_test_count", "total_test_count"),
                ("execution_time", "execution_memory"),
            ),
        }),
        (_("🧪 Batafsil Test Caselar (JSON)"), {
            "fields": ("test_results_display",),
            "classes": ("collapse",),
        }),
    )

    CODE_BLOCK_STYLE = (
        "background:#0d1117; color:#e6edf3; padding:16px; border-radius:8px; "
        "font-family:'SF Mono',Consolas,monospace; font-size:13px; "
        "white-space:pre-wrap; overflow-x:auto; line-height:1.6; border:1px solid #30363d;"
    )

    # ─── DETAL KO'RINISH ───

    @admin.display(description=_("Yechim kodi"))
    def code_display(self, obj):
        if not obj.code:
            return format_html('<span class="text-gray-400">Kod mavjud emas</span>')
        return format_html(
            '<pre style="{}"><code>{}</code></pre>',
            self.CODE_BLOCK_STYLE, obj.code
        )

    @admin.display(description=_("Test natijalari"))
    def test_results_display(self, obj):
        if not obj.test_results:
            return format_html('<span class="text-gray-400">Natijalar mavjud emas</span>')
        try:
            data = json.loads(obj.test_results) if isinstance(obj.test_results, str) else obj.test_results
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            pretty = str(obj.test_results)
        return format_html(
            '<pre style="{}"><code>{}</code></pre>',
            self.CODE_BLOCK_STYLE, pretty
        )

    # ─── RO'YXAT USTUNLARI ───

    @display(description=_("ID"), ordering="id")
    def id_display(self, obj):
        return format_html(
            '<span class="font-bold text-gray-500 dark:text-gray-400">#{}</span>',
            obj.id,
        )

    @display(description=_("Foydalanuvchi"), ordering="user__username")
    def user_display(self, obj):
        username = getattr(obj.user, "username", "Noma'lum")
        return format_html(
            '<span class="font-medium text-gray-900 dark:text-gray-100">{}</span>',
            username,
        )

    @display(description=_("Masala"), ordering="problem__title")
    def problem_display(self, obj):
        title = getattr(obj.problem, "title", "Noma'lum")
        pid = getattr(obj.problem, "id", 0)
        return format_html(
            '<a href="/admin/problems/problem/{}/change/" '
            'class="text-primary-600 dark:text-primary-400 font-medium hover:underline">{}</a>',
            pid, title,
        )

    @display(description=_("Til"))
    def language_badge(self, obj):
        name = getattr(obj.language, "name", "?")
        return format_html(
            '<span class="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 '
            'px-2 py-1 rounded text-xs font-mono border border-blue-200 dark:border-blue-800">{}</span>',
            name,
        )

    @display(description=_("Hukm"), ordering="verdict")
    def verdict_badge(self, obj):
        colors = {
            "AC":  "bg-success-50 text-success-700 border-success-200 dark:bg-success-900/30 dark:text-success-400 dark:border-success-800",
            "WA":  "bg-danger-50 text-danger-700 border-danger-200 dark:bg-danger-900/30 dark:text-danger-400 dark:border-danger-800",
            "TLE": "bg-warning-50 text-warning-700 border-warning-200 dark:bg-warning-900/30 dark:text-warning-400 dark:border-warning-800",
            "MLE": "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800",
            "RE":  "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800",
            "CE":  "bg-gray-100 text-gray-700 border-gray-300 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700",
        }
        badge_style = colors.get(obj.verdict, "bg-gray-50 text-gray-700 border-gray-200")
        verdict_str = obj.get_verdict_display() if hasattr(obj, "get_verdict_display") else (obj.verdict or "-")
        return format_html(
            '<span class="px-2 py-1 rounded text-xs font-bold border {}">{}</span>',
            badge_style, verdict_str,
        )

    @display(description=_("Testlar"))
    def progress_bar(self, obj):
        passed = obj.passed_test_count or 0
        total = obj.total_test_count or 0
        color = "text-success-600 dark:text-success-400" if passed == total and total > 0 else "text-danger-600 dark:text-danger-400"
        return format_html(
            '<span class="font-mono font-semibold {}">{}/{}</span>',
            color, passed, total,
        )

    @display(description=_("Resurslar"))
    def metrics_display(self, obj):
        t = f"{obj.execution_time:.2f} ms" if obj.execution_time is not None else "-"
        m = f"{obj.execution_memory} KB" if obj.execution_memory else "-"
        return format_html(
            '<span class="text-xs text-gray-500 dark:text-gray-400 font-mono">⏱️ {}<br>💾 {}</span>',
            t, m,
        )

    # ─── CHANGELIST STATISTIKA (PAGINATIONGA TASIR QILMAYDI) ───
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        cl = self.get_changelist_instance(request)

        # Bu to'liq filtrlangan queryset — pagination bu yerda emas,
        # shuning uchun statistika barcha filtrlangan natijalar bo'yicha to'g'ri chiqadi
        filtered_qs = cl.get_queryset(request)

        # So'nggi 12 oy bilan cheklaymiz (tezlashtirish)
        twelve_months_ago = timezone.now() - timedelta(days=365)

        stats = filtered_qs.aggregate(
            total_submissions=Count("id"),
            ac_count=Count("id", filter=Q(verdict="AC")),
            wa_count=Count("id", filter=Q(verdict="WA")),
            tle_count=Count("id", filter=Q(verdict="TLE")),
            other_count=Count("id", filter=~Q(verdict__in=["AC", "WA", "TLE"])),
            avg_time=Avg("execution_time"),
        )

        monthly_data = (
            filtered_qs.filter(submitted_at__gte=twelve_months_ago)
            .annotate(month=TruncMonth("submitted_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        chart_labels = []
        chart_values = []
        for item in monthly_data:
            if item["month"]:
                chart_labels.append(item["month"].strftime("%Y-%m"))
                chart_values.append(int(item["count"] or 0))

        avg_time_val = stats["avg_time"] or 0.0

        extra_context.update({
            "total_submissions": stats["total_submissions"] or 0,
            "ac_count": stats["ac_count"] or 0,
            "wa_count": stats["wa_count"] or 0,
            "tle_count": stats["tle_count"] or 0,
            "other_count": stats["other_count"] or 0,
            "avg_time": f"{avg_time_val:.1f}",
            "chart_labels_json": json.dumps(chart_labels),
            "chart_values_json": json.dumps(chart_values),
        })
        return super().changelist_view(request, extra_context=extra_context)