# status/admin.py
import json
import logging
from datetime import timedelta

from django.contrib import admin
from django.db.models import Sum, Avg, Count
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from unfold.admin import ModelAdmin

from .models import CourseStatus, ModuleStatus, ProblemStatus, UserStats, UserActivityDaily, LessonStatus, LectureStatus

logger = logging.getLogger(__name__)


LEVEL_COLORS = {
    "beginner": "#94a3b8",
    "bronze": "#cd7f32",
    "silver": "#c0c0c0",
    "gold": "#eab308",
    "pro": "#8b5cf6",
}
LEVEL_ICONS = {
    "beginner": "🟡",
    "bronze": "🥉",
    "silver": "🥈",
    "gold": "🥇",
    "pro": "💎",
}


# ============================================
# USER STATS ADMIN
# ============================================
@admin.register(UserStats)
class UserStatsAdmin(ModelAdmin):
    """Foydalanuvchi statistikasi.

    DIQQAT: `change_list_template` ATAY ishlatilmaydi — bu butun
    change_list.html/change_list_results.html'ni almashtirib,
    Unfold'ning standart jadval renderingini (colspan, checkbox
    ustuni, row actions va h.k.) xavf ostiga qo'yishi mumkin.
    Buning o'rniga Unfold'ning rasmiy `list_before_template` hook'i
    ishlatiladi — u faqat natijalar jadvali TEPASIGA qo'shimcha
    blok qo'shadi, jadvalning o'zi butunlay default holatda qoladi.
    """

    list_before_template = "admin/status/userstats_before_list.html"

    list_display = (
        "user_display",
        "xp_display",
        "level_badge",
        "progress_bar",
        "activity_count",
        "last_activity_display",
    )
    list_filter = ("level", "updated_at")
    search_fields = ("user__username", "user__full_name", "user__telegram_id")
    list_per_page = 25
    ordering = ("-xp",)
    autocomplete_fields = ("user",)

    fieldsets = (
        ("👤 Foydalanuvchi", {"fields": ("user",)}),
        ("📊 Statistika", {"fields": (("xp", "level"),)}),
        ("📅 Vaqt", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ("created_at", "updated_at")

    # ---------- list_display bezaklari ----------

    @admin.display(description="Foydalanuvchi")
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return format_html(
            '<div class="flex flex-col leading-tight">'
            '<span class="font-semibold">{}</span>'
            '<span class="text-xs text-gray-400">ID: {}</span></div>',
            name, obj.user.telegram_id,
        )

    @admin.display(description="XP", ordering="xp")
    def xp_display(self, obj):
        return format_html('<span class="font-bold" style="color:#8b5cf6;">⚡ {} XP</span>', obj.xp)

    @admin.display(description="Daraja", ordering="level")
    def level_badge(self, obj):
        color = LEVEL_COLORS.get(obj.level, "#6b7280")
        icon = LEVEL_ICONS.get(obj.level, "•")
        label = obj.get_level_display()
        return mark_safe(
            f'<span class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs '
            f'font-semibold" style="background:{color}1a;color:{color};border:1px solid {color}40;">'
            f"{icon} {label}</span>"
        )

    @admin.display(description="Progress")
    def progress_bar(self, obj):
        xp = obj.xp
        if xp < 2000:
            current, target, label = xp, 2000, "Bronza"
        elif xp < 5000:
            current, target, label = xp - 2000, 3000, "Kumush"
        elif xp < 8000:
            current, target, label = xp - 5000, 3000, "Oltin"
        elif xp < 15000:
            current, target, label = xp - 8000, 7000, "Professional"
        else:
            current, target, label = 1, 1, "MAX"

        percent = min(round((current / target) * 100, 1), 100) if target else 100
        bar_color = "#8b5cf6" if percent < 50 else "#f59e0b" if percent < 80 else "#22c55e"

        return format_html(
            '<div class="w-36">'
            '<div class="flex justify-between text-[10px] text-gray-400 mb-1"><span>{}</span><span>{}%</span></div>'
            '<div class="w-full h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">'
            '<div class="h-full rounded-full" style="width:{}%;background:{};"></div>'
            "</div></div>",
            label, percent, percent, bar_color,
        )

    @admin.display(description="Faol kunlar")
    def activity_count(self, obj):
        count = UserActivityDaily.objects.filter(user=obj.user).count()
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold" '
            'style="background:#f0fdf4;color:#16a34a;">📅 {} kun</span>',
            count,
        )

    @admin.display(description="Oxirgi faollik")
    def last_activity_display(self, obj):
        last = UserActivityDaily.objects.filter(user=obj.user).order_by("-date").first()
        return last.date.strftime("%d-%m-%Y") if last else "—"

    # ---------- list_before_template uchun kontekst ----------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        total_users = UserStats.objects.count()
        total_xp = UserStats.objects.aggregate(total=Sum("xp"))["total"] or 0
        avg_xp = UserStats.objects.aggregate(avg=Avg("xp"))["avg"] or 0

        # 1) Darajalar bo'yicha taqsimot
        level_cards = []
        level_labels, level_counts, level_bg = [], [], []
        for level, label in UserStats.Level.choices:
            count = UserStats.objects.filter(level=level).count()
            percent = round((count / total_users) * 100, 1) if total_users else 0
            color = LEVEL_COLORS.get(level, "#6b7280")
            level_cards.append({
                "count": count, "label": str(label), "percent": percent,
                "color": color, "icon": LEVEL_ICONS.get(level, "•"),
            })
            level_labels.append(str(label))
            level_counts.append(count)
            level_bg.append(color)

        # 2) So'nggi 7 kunlik umumiy XP
        today = now().date()
        weekly_labels, weekly_xp_data = [], []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            xp = UserActivityDaily.objects.filter(date=d).aggregate(total=Sum("xp_earned"))["total"] or 0
            weekly_labels.append(d.strftime("%d-%b"))
            weekly_xp_data.append(xp)

        # 3) Top 10 lider talabalar (table komponenti uchun headers/rows shaklida)
        top_qs = UserStats.objects.select_related("user").order_by("-xp")[:10]
        top_rows = []
        for i, u in enumerate(top_qs, start=1):
            name = u.user.full_name or u.user.username or f"User#{u.user.telegram_id}"
            top_rows.append([f"#{i}", name, u.get_level_display(), f"⚡ {u.xp}"])

        extra_context.update({
            "us_total_users": total_users,
            "us_total_xp": total_xp,
            "us_avg_xp": round(avg_xp, 1),
            "us_level_cards": level_cards,
            "us_top_table": {
                "headers": ["#", "Foydalanuvchi", "Daraja", "XP"],
                "rows": top_rows,
            },
            "us_weekly_chart_data": json.dumps({
                "labels": weekly_labels,
                "datasets": [{
                    "label": "Kunlik jami XP",
                    "data": weekly_xp_data,
                    "borderColor": "#4f46e5",
                    "backgroundColor": "rgba(79,70,229,0.12)",
                    "fill": True,
                    "tension": 0.35,
                }],
            }),
            "us_level_chart_data": json.dumps({
                "labels": level_labels,
                "datasets": [{"data": level_counts, "backgroundColor": level_bg, "borderWidth": 0}],
            }),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# USER ACTIVITY DAILY ADMIN
# ============================================
@admin.register(UserActivityDaily)
class UserActivityDailyAdmin(ModelAdmin):
    list_before_template = "admin/status/useractivitydaily_before_list.html"

    list_display = ("user_display", "date_display", "xp_display", "tasks_display", "duration_display")
    list_filter = ("date", "user")
    search_fields = ("user__username", "user__full_name", "user__telegram_id")
    list_per_page = 30
    ordering = ("-date",)
    autocomplete_fields = ("user",)
    fieldsets = (
        ("👤 Foydalanuvchi", {"fields": ("user",)}),
        ("📊 Faollik", {"fields": ("date", ("xp_earned", "tasks_count"), "total_duration")}),
    )
    readonly_fields = ("date",)

    @admin.display(description="Foydalanuvchi")
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return format_html(
            '<div class="flex flex-col leading-tight"><span class="font-semibold">{}</span>'
            '<span class="text-xs text-gray-400">ID: {}</span></div>', name, obj.user.telegram_id,
        )

    @admin.display(description="Sana")
    def date_display(self, obj):
        return obj.date.strftime("%d-%m-%Y")

    @admin.display(description="XP")
    def xp_display(self, obj):
        return format_html('<span style="color:#8b5cf6;font-weight:600;">⚡ {}</span>', obj.xp_earned)

    @admin.display(description="Vazifalar")
    def tasks_display(self, obj):
        return format_html(
            '<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs bg-gray-100 dark:bg-gray-800">📝 {}</span>',
            obj.tasks_count,
        )

    @admin.display(description="Vaqt")
    def duration_display(self, obj):
        hours, minutes = divmod(obj.total_duration, 60)
        return f"{hours}h {minutes}m" if hours else f"{minutes}m"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        today = now().date()
        yesterday = today - timedelta(days=1)

        today_agg = UserActivityDaily.objects.filter(date=today).aggregate(
            xp=Sum("xp_earned"), tasks=Sum("tasks_count"), duration=Sum("total_duration"), users=Count("user"),
        )
        yesterday_xp = UserActivityDaily.objects.filter(date=yesterday).aggregate(xp=Sum("xp_earned"))["xp"] or 0
        today_xp = today_agg["xp"] or 0
        delta = today_xp - yesterday_xp
        duration = today_agg["duration"] or 0
        duration_hours, duration_minutes = divmod(duration, 60)

        extra_context.update({
            "uad_today_xp": today_xp,
            "uad_today_tasks": today_agg["tasks"] or 0,
            "uad_today_duration_hours": duration_hours,
            "uad_today_duration_minutes": duration_minutes,
            "uad_today_active_users": today_agg["users"] or 0,
            "uad_delta_vs_yesterday": delta,
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# LESSON STATUS ADMIN
# ============================================
@admin.register(LessonStatus)
class LessonStatusAdmin(ModelAdmin):
    list_before_template = "admin/status/lessonstatus_before_list.html"

    list_display = ("user_display", "lesson_display", "finished_tasks_display", "status_badge", "completed_at_formatted")
    list_filter = ("is_completed", "lesson__modul__course", "completed_at")
    search_fields = ("user__username", "user__full_name", "lesson__title", "lesson__modul__title")
    list_per_page = 30
    ordering = ("-completed_at",)
    autocomplete_fields = ("user", "lesson")
    fieldsets = (
        ("👤 Talaba va Dars", {"fields": ("user", "lesson")}),
        ("📊 Holat", {"fields": ("finished_tasks_count", "is_completed", "completed_at")}),
    )
    readonly_fields = ("completed_at",)

    @admin.display(description="Talaba")
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return format_html(
            '<div class="flex flex-col leading-tight"><span class="font-semibold">{}</span>'
            '<span class="text-xs text-gray-400">ID: {}</span></div>', name, obj.user.telegram_id,
        )

    @admin.display(description="Darslik")
    def lesson_display(self, obj):
        return format_html(
            '<a href="/admin/courses/lesson/{}/change/" class="text-blue-500 hover:underline">📘 {}</a>',
            obj.lesson.id, obj.lesson.title[:40],
        )

    @admin.display(description="Tugatilgan vazifalar")
    def finished_tasks_display(self, obj):
        total = obj.lesson.total_tasks_count or 0
        finished = obj.finished_tasks_count
        percent = round((finished / total) * 100, 1) if total else 0
        return format_html(
            '<div class="flex items-center gap-2"><span class="font-semibold">{}/{}</span>'
            '<span class="text-xs text-gray-400">({}%)</span></div>', finished, total, percent,
        )

    @admin.display(description="Holat")
    def status_badge(self, obj):
        if obj.is_completed:
            return mark_safe(
                '<span class="inline-flex px-3 py-1 rounded-full text-xs font-semibold" '
                'style="background:#dcfce7;color:#15803d;">✅ Tugatilgan</span>'
            )
        return mark_safe(
            '<span class="inline-flex px-3 py-1 rounded-full text-xs font-semibold" '
            'style="background:#fee2e2;color:#b91c1c;">⏳ Davom etmoqda</span>'
        )

    @admin.display(description="Tugatilgan vaqt")
    def completed_at_formatted(self, obj):
        return obj.completed_at.strftime("%d-%m-%Y %H:%M") if obj.completed_at else "—"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        total = LessonStatus.objects.count()
        completed = LessonStatus.objects.filter(is_completed=True).count()
        percent = round((completed / total) * 100, 1) if total else 0

        top_lessons = (
            LessonStatus.objects.filter(is_completed=True)
            .values("lesson__title")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )
        top_rows = [[row["lesson__title"][:40], row["total"]] for row in top_lessons]

        extra_context.update({
            "ls_total": total,
            "ls_completed": completed,
            "ls_in_progress": total - completed,
            "ls_percent": percent,
            "ls_top_table": {"headers": ["Darslik", "Tugatgan talabalar"], "rows": top_rows},
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# LECTURE STATUS ADMIN
# ============================================
@admin.register(LectureStatus)
class LectureStatusAdmin(ModelAdmin):
    list_before_template = "admin/status/lecturestatus_before_list.html"

    list_display = ("user_display", "lecture_display", "status_badge", "completed_at_formatted")
    list_filter = ("is_completed", "lecture__lesson__modul__course", "completed_at")
    search_fields = ("user__username", "user__full_name", "lecture__title", "lecture__lesson__title")
    list_per_page = 30
    ordering = ("-completed_at",)
    autocomplete_fields = ("user", "lecture")
    fieldsets = (
        ("👤 Talaba va Ma'ruza", {"fields": ("user", "lecture")}),
        ("📊 Holat", {"fields": ("is_completed", "completed_at")}),
    )
    readonly_fields = ("completed_at",)

    @admin.display(description="Talaba")
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return format_html(
            '<div class="flex flex-col leading-tight"><span class="font-semibold">{}</span>'
            '<span class="text-xs text-gray-400">ID: {}</span></div>', name, obj.user.telegram_id,
        )

    @admin.display(description="Ma'ruza")
    def lecture_display(self, obj):
        return format_html(
            '<a href="/admin/courses/lecture/{}/change/" class="hover:underline" style="color:#8b5cf6;">📖 {}</a>',
            obj.lecture.id, obj.lecture.title[:40],
        )

    @admin.display(description="Holat")
    def status_badge(self, obj):
        if obj.is_completed:
            return mark_safe(
                '<span class="inline-flex px-3 py-1 rounded-full text-xs font-semibold" '
                'style="background:#dcfce7;color:#15803d;">✅ Tugatilgan</span>'
            )
        return mark_safe(
            '<span class="inline-flex px-3 py-1 rounded-full text-xs font-semibold" '
            'style="background:#fee2e2;color:#b91c1c;">❌ Tugatilmagan</span>'
        )

    @admin.display(description="Tugatilgan vaqt")
    def completed_at_formatted(self, obj):
        return obj.completed_at.strftime("%d-%m-%Y %H:%M") if obj.completed_at else "—"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        total = LectureStatus.objects.count()
        completed = LectureStatus.objects.filter(is_completed=True).count()
        percent = round((completed / total) * 100, 1) if total else 0

        today = now().date()
        today_completed = LectureStatus.objects.filter(completed_at__date=today, is_completed=True).count()

        extra_context.update({
            "lc_total": total,
            "lc_completed": completed,
            "lc_not_completed": total - completed,
            "lc_percent": percent,
            "lc_today_completed": today_completed,
        })
        return super().changelist_view(request, extra_context=extra_context)



@admin.register(ProblemStatus)
class ProblemStatusAdmin(ModelAdmin):
    list_before_template = "admin/status/problemstatus_before_list.html"

    list_display = (
        "user_display",
        "problem_display",
        "status_badge",
        "attempts_display",
        "started_at_display",
        "solved_at_display",
    )

    list_filter = (
        "solved",
        "problem__difficulty",
        "problem__category",
        "solved_at",
    )

    search_fields = (
        "user__username",
        "user__full_name",
        "user__telegram_id",
        "problem__title",
    )

    ordering = ("-solved_at",)
    list_per_page = 30

    autocomplete_fields = (
        "user",
        "problem",
        "best_submission",
    )

    fieldsets = (
        (
            "👤 Talaba",
            {
                "fields": (
                    "user",
                    "problem",
                )
            },
        ),
        (
            "📊 Progress",
            {
                "fields": (
                    ("solved", "attempts"),
                    "best_submission",
                )
            },
        ),
        (
            "🕒 Vaqt",
            {
                "fields": (
                    "started_at",
                    "solved_at",
                )
            },
        ),
    )

    readonly_fields = (
        "started_at",
        "solved_at",
    )

    # ---------------------------------------------------
    # LIST DISPLAY
    # ---------------------------------------------------

    @admin.display(description="Talaba")
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"

        return format_html(
            '<div class="flex flex-col">'
            '<span class="font-semibold">{}</span>'
            '<span class="text-xs text-gray-400">ID: {}</span>'
            "</div>",
            name,
            obj.user.telegram_id,
        )

    @admin.display(description="Masala")
    def problem_display(self, obj):
        return format_html(
            '<a href="/admin/problems/problem/{}/change/" '
            'class="text-primary-600 hover:underline">'
            "🧩 {}"
            "</a>",
            obj.problem.id,
            obj.problem.title[:45],
        )

    @admin.display(description="Holat", ordering="solved")
    def status_badge(self, obj):
        if obj.solved:
            return mark_safe(
                '<span class="inline-flex px-3 py-1 rounded-full '
                'text-xs font-semibold" '
                'style="background:#dcfce7;color:#15803d;">'
                "✅ Yechilgan"
                "</span>"
            )

        return mark_safe(
            '<span class="inline-flex px-3 py-1 rounded-full '
            'text-xs font-semibold" '
            'style="background:#fee2e2;color:#b91c1c;">'
            "⏳ Jarayonda"
            "</span>"
        )

    @admin.display(description="Urinishlar", ordering="attempts")
    def attempts_display(self, obj):
        color = "#22c55e" if obj.solved else "#f59e0b"

        return format_html(
            '<span class="inline-flex items-center px-2.5 py-1 '
            'rounded-full text-xs font-semibold" '
            'style="background:{}20;color:{};">'
            "🎯 {} ta"
            "</span>",
            color,
            color,
            obj.attempts,
        )

    @admin.display(description="Boshlangan")
    def started_at_display(self, obj):
        if not obj.started_at:
            return "—"

        return obj.started_at.strftime("%d-%m-%Y %H:%M")

    @admin.display(description="Yechilgan")
    def solved_at_display(self, obj):
        if not obj.solved_at:
            return "—"

        return obj.solved_at.strftime("%d-%m-%Y %H:%M")

    # ---------------------------------------------------
    # DASHBOARD
    # ---------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        total = ProblemStatus.objects.count()

        solved = ProblemStatus.objects.filter(
            solved=True
        ).count()

        unsolved = total - solved

        percent = round(
            solved * 100 / total,
            1,
        ) if total else 0

        today = now().date()

        solved_today = ProblemStatus.objects.filter(
            solved=True,
            solved_at__date=today,
        ).count()

        most_attempted = (
            ProblemStatus.objects
            .values("problem__title")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )

        rows = [
            [item["problem__title"][:45], item["total"]]
            for item in most_attempted
        ]

        extra_context.update({
            "ps_total": total,
            "ps_solved": solved,
            "ps_unsolved": unsolved,
            "ps_percent": percent,
            "ps_today": solved_today,
            "ps_top_table": {
                "headers": [
                    "Masala",
                    "Yechgan foydalanuvchilar",
                ],
                "rows": rows,
            },
        })

        return super().changelist_view(
            request,
            extra_context=extra_context,
        )

@admin.register(ModuleStatus)
class ModuleStatusAdmin(ModelAdmin):
    list_before_template = "admin/status/modulestatus_before_list.html"

    list_display = (
        "user_display",
        "module_display",
        "progress_display",
        "status_badge",
        "completed_at_display",
    )

    list_filter = (
        "is_completed",
        "modul__course",
        "completed_at",
    )

    search_fields = (
        "user__username",
        "user__full_name",
        "user__telegram_id",
        "modul__title",
        "modul__course__title",
    )

    ordering = ("-completed_at",)
    list_per_page = 30

    autocomplete_fields = (
        "user",
        "modul",
    )

    fieldsets = (
        (
            "👤 Talaba",
            {
                "fields": (
                    "user",
                    "modul",
                )
            },
        ),
        (
            "📚 Progress",
            {
                "fields": (
                    ("completed_lessons", "completed_tests"),
                    "is_completed",
                )
            },
        ),
        (
            "🕒 Vaqt",
            {
                "fields": (
                    "started_at",
                    "completed_at",
                )
            },
        ),
    )

    readonly_fields = (
        "started_at",
        "completed_at",
    )

    # -------------------------------------------------

    @admin.display(description="Talaba")
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"

        return format_html(
            '<div class="flex flex-col">'
            '<span class="font-semibold">{}</span>'
            '<span class="text-xs text-gray-400">ID: {}</span>'
            '</div>',
            name,
            obj.user.telegram_id,
        )

    @admin.display(description="Modul")
    def module_display(self, obj):
        return format_html(
            '<a href="/admin/courses/modul/{}/change/" '
            'class="text-primary-600 hover:underline">'
            '{}'
            '</a>',
            obj.modul.id,
            obj.modul.title[:45],
        )

    @admin.display(description="Progress")
    def progress_display(self, obj):
        total_lessons = obj.modul.lessons.count()
        total_tests = obj.modul.tests.count()

        total = total_lessons + total_tests
        finished = obj.completed_lessons + obj.completed_tests

        percent = round(finished * 100 / total, 1) if total else 0

        color = (
            "#ef4444"
            if percent < 40
            else "#f59e0b"
            if percent < 80
            else "#22c55e"
        )

        return format_html(
            '<div class="w-40">'
            '<div class="flex justify-between text-xs">'
            '<span>{}/{}</span>'
            '<span>{}%</span>'
            '</div>'
            '<div class="mt-1 h-2 rounded-full bg-gray-200 dark:bg-gray-700">'
            '<div class="h-2 rounded-full" '
            'style="width:{}%;background:{};"></div>'
            '</div>'
            '</div>',
            finished,
            total,
            percent,
            percent,
            color,
        )

    @admin.display(description="Holat")
    def status_badge(self, obj):

        if obj.is_completed:
            return mark_safe(
                '<span class="inline-flex items-center px-3 py-1 '
                'rounded-full text-xs font-semibold '
                'bg-green-100 text-green-700">'
                'Completed'
                '</span>'
            )

        return mark_safe(
            '<span class="inline-flex items-center px-3 py-1 '
            'rounded-full text-xs font-semibold '
            'bg-yellow-100 text-yellow-700">'
            'In Progress'
            '</span>'
        )

    @admin.display(description="Tugatilgan")
    def completed_at_display(self, obj):
        if obj.completed_at:
            return obj.completed_at.strftime("%d-%m-%Y %H:%M")
        return "—"

    # -------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        total = ModuleStatus.objects.count()

        completed = ModuleStatus.objects.filter(
            is_completed=True
        ).count()

        percent = round(
            completed * 100 / total,
            1,
        ) if total else 0

        today = now().date()

        today_completed = ModuleStatus.objects.filter(
            is_completed=True,
            completed_at__date=today,
        ).count()

        top_modules = (
            ModuleStatus.objects.filter(
                is_completed=True
            )
            .values("modul__title")
            .annotate(
                total=Count("id")
            )
            .order_by("-total")[:10]
        )

        rows = [
            [
                item["modul__title"][:45],
                item["total"],
            ]
            for item in top_modules
        ]

        extra_context.update({
            "ms_total": total,
            "ms_completed": completed,
            "ms_in_progress": total - completed,
            "ms_percent": percent,
            "ms_today": today_completed,
            "ms_top_table": {
                "headers": [
                    "Modul",
                    "Tugatgan talabalar",
                ],
                "rows": rows,
            },
        })

        return super().changelist_view(
            request,
            extra_context=extra_context,
        )

@admin.register(CourseStatus)
class CourseStatusAdmin(ModelAdmin):
    list_before_template = "admin/status/coursestatus_before_list.html"

    list_display = (
        "user_display",
        "course_display",
        "progress_display",
        "status_badge",
        "completed_at_display",
    )

    list_filter = (
        "is_completed",
        "course",
        "completed_at",
    )

    search_fields = (
        "user__username",
        "user__full_name",
        "user__telegram_id",
        "course__title",
    )

    ordering = ("-completed_at",)
    list_per_page = 30

    autocomplete_fields = (
        "user",
        "course",
    )

    fieldsets = (
        (
            "👤 Talaba",
            {
                "fields": (
                    "user",
                    "course",
                )
            },
        ),
        (
            "📊 Progress",
            {
                "fields": (
                    ("completed_modules", "completed_lessons"),
                    ("completed_tests", "completed_problems"),
                    "is_completed",
                )
            },
        ),
        (
            "🕒 Vaqt",
            {
                "fields": (
                    "started_at",
                    "completed_at",
                )
            },
        ),
    )

    readonly_fields = (
        "started_at",
        "completed_at",
    )

    # ---------------------------------------------------

    @admin.display(description="Talaba")
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"

        return format_html(
            '<div class="flex flex-col">'
            '<span class="font-semibold">{}</span>'
            '<span class="text-xs text-gray-400">ID: {}</span>'
            "</div>",
            name,
            obj.user.telegram_id,
        )

    @admin.display(description="Kurs")
    def course_display(self, obj):
        return format_html(
            '<a href="/admin/courses/course/{}/change/" '
            'class="text-primary-600 hover:underline">'
            "{}"
            "</a>",
            obj.course.id,
            obj.course.title[:50],
        )

    @admin.display(description="Progress")
    def progress_display(self, obj):

        total_modules = obj.course.modullar.count()

        finished = obj.completed_modules

        percent = round(
            finished * 100 / total_modules,
            1,
        ) if total_modules else 0

        color = (
            "#ef4444"
            if percent < 40
            else "#f59e0b"
            if percent < 80
            else "#22c55e"
        )

        return format_html(
            '<div class="w-44">'
            '<div class="flex justify-between text-xs">'
            '<span>{}/{}</span>'
            '<span>{}%</span>'
            '</div>'
            '<div class="mt-1 h-2 rounded-full bg-gray-200 dark:bg-gray-700">'
            '<div class="h-2 rounded-full" '
            'style="width:{}%;background:{};"></div>'
            '</div>'
            '</div>',
            finished,
            total_modules,
            percent,
            percent,
            color,
        )

    @admin.display(description="Holat")
    def status_badge(self, obj):

        if obj.is_completed:
            return mark_safe(
                '<span class="inline-flex items-center px-3 py-1 '
                'rounded-full text-xs font-semibold '
                'bg-green-100 text-green-700">'
                'Completed'
                '</span>'
            )

        return mark_safe(
            '<span class="inline-flex items-center px-3 py-1 '
            'rounded-full text-xs font-semibold '
            'bg-yellow-100 text-yellow-700">'
            'In Progress'
            '</span>'
        )

    @admin.display(description="Tugatilgan")
    def completed_at_display(self, obj):
        if obj.completed_at:
            return obj.completed_at.strftime("%d-%m-%Y %H:%M")
        return "—"

    # ---------------------------------------------------

    def changelist_view(self, request, extra_context=None):

        extra_context = extra_context or {}

        total = CourseStatus.objects.count()

        completed = CourseStatus.objects.filter(
            is_completed=True
        ).count()

        percent = round(
            completed * 100 / total,
            1,
        ) if total else 0

        today_completed = CourseStatus.objects.filter(
            completed_at__date=now().date(),
            is_completed=True,
        ).count()

        top_courses = (
            CourseStatus.objects
            .filter(is_completed=True)
            .values("course__title")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )

        rows = [
            [
                row["course__title"][:50],
                row["total"],
            ]
            for row in top_courses
        ]

        extra_context.update({
            "cs_total": total,
            "cs_completed": completed,
            "cs_in_progress": total - completed,
            "cs_percent": percent,
            "cs_today": today_completed,
            "cs_top_table": {
                "headers": [
                    "Kurs",
                    "Bitirgan talabalar",
                ],
                "rows": rows,
            },
        })

        return super().changelist_view(
            request,
            extra_context=extra_context,
        )