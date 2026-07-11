# status/admin.py
import json
import logging
from datetime import timedelta

from django.contrib import admin
from django.db.models import Sum, Avg
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now
from unfold.admin import ModelAdmin

from .models import UserStats, UserActivityDaily, LessonStatus, LectureStatus

logger = logging.getLogger(__name__)


# Bitta yagona rang palitrasi — admin.py va template bir xil ranglardan foydalanadi
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
    """Foydalanuvchi statistikasi — Chartlar va Liderlar jadvali bilan"""

    change_list_template = "admin/status/userstats_changelist.html"

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
        return format_html(
            '<span class="font-bold" style="color:#8b5cf6;">⚡ {} XP</span>', obj.xp
        )

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

    # ---------- Dashboard konteksti ----------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        total_users = UserStats.objects.count()
        total_xp = UserStats.objects.aggregate(total=Sum("xp"))["total"] or 0
        avg_xp = UserStats.objects.aggregate(avg=Avg("xp"))["avg"] or 0

        # 1) Darajalar bo'yicha taqsimot — kartochkalar VA doughnut chart uchun
        level_stats = {}
        level_labels, level_counts, level_bg = [], [], []
        for level, label in UserStats.Level.choices:
            count = UserStats.objects.filter(level=level).count()
            percent = round((count / total_users) * 100, 1) if total_users else 0
            color = LEVEL_COLORS.get(level, "#6b7280")
            level_stats[level] = {
                "count": count,
                "label": str(label),
                "percent": percent,
                "color": color,
                "icon": LEVEL_ICONS.get(level, "•"),
            }
            level_labels.append(str(label))
            level_counts.append(count)
            level_bg.append(color)

        # 2) So'nggi 7 kunlik umumiy XP — bar chart uchun (kartochka + Chart.js)
        today = now().date()
        weekly_activity, weekly_labels, weekly_xp_data = [], [], []
        daily_totals = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            xp = UserActivityDaily.objects.filter(date=d).aggregate(total=Sum("xp_earned"))["total"] or 0
            daily_totals.append((d, xp))
            weekly_labels.append(d.strftime("%d-%b"))
            weekly_xp_data.append(xp)
        max_weekly = max(weekly_xp_data) or 1
        for d, xp in daily_totals:
            weekly_activity.append({
                "label": d.strftime("%d-%b"),
                "xp": xp,
                "percent": round((xp / max_weekly) * 100, 1),
            })

        # 3) So'nggi 30 kunlik heatmap
        heatmap_data = []
        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            xp = UserActivityDaily.objects.filter(date=d).aggregate(total=Sum("xp_earned"))["total"] or 0
            heatmap_data.append({"date": d.strftime("%d-%m-%Y"), "xp": xp})

        # 4) Top 10 lider talabalar
        top_qs = UserStats.objects.select_related("user").order_by("-xp")[:10]
        top_users = [{
            "username": u.user.full_name or u.user.username or f"User#{u.user.telegram_id}",
            "xp": u.xp,
            "level": u.get_level_display(),
            "level_color": LEVEL_COLORS.get(u.level, "#6b7280"),
        } for u in top_qs]

        extra_context.update({
            "total_users": total_users,
            "total_xp": total_xp,
            "avg_xp": round(avg_xp, 1),
            "level_stats": level_stats,
            "weekly_activity": weekly_activity,
            "heatmap_data": heatmap_data,
            "top_users": top_users,
            # Chart.js uchun JSON payloadlar (asosiy grafiklar shu orqali chiziladi)
            "weekly_chart_data": json.dumps({
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
            "level_chart_data": json.dumps({
                "labels": level_labels,
                "datasets": [{"data": level_counts, "backgroundColor": level_bg, "borderWidth": 0}],
            }),
            "top_users_chart_data": json.dumps({
                "labels": [u["username"] for u in top_users],
                "datasets": [{
                    "label": "Jami XP",
                    "data": [u["xp"] for u in top_users],
                    "backgroundColor": "#8b5cf6",
                    "borderRadius": 6,
                }],
            }),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# USER ACTIVITY DAILY ADMIN
# ============================================
@admin.register(UserActivityDaily)
class UserActivityDailyAdmin(ModelAdmin):
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


# ============================================
# LESSON STATUS ADMIN
# ============================================
@admin.register(LessonStatus)
class LessonStatusAdmin(ModelAdmin):
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


# ============================================
# LECTURE STATUS ADMIN
# ============================================
@admin.register(LectureStatus)
class LectureStatusAdmin(ModelAdmin):
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