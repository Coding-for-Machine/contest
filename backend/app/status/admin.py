# status/admin.py
import logging
from datetime import datetime, timedelta
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils.timezone import now, localtime
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.contrib.forms.widgets import WysiwygWidget

from .models import UserStats, UserActivityDaily, LessonStatus, LectureStatus

logger = logging.getLogger(__name__)


# ============================================
# INLINES (UserStats ga bog'langan modellar uchun)
# ============================================
# ❌ BU INLINELARNI O'CHIRIB QO'YAMIZ
# Chunki ular UserStats ga ForeignKey orqali bog'lanmagan

# class LectureStatusInline(TabularInline):
#     model = LectureStatus
#     ...

# class LessonStatusInline(TabularInline):
#     model = LessonStatus
#     ...

# class UserActivityDailyInline(TabularInline):
#     model = UserActivityDaily
#     ...


# ============================================
# USER STATS ADMIN
# ============================================

@admin.register(UserStats)
class UserStatsAdmin(ModelAdmin):
    """Foydalanuvchi statistikasi - Chart va UI bilan"""
    
    change_list_template = "admin/status/userstats_changelist.html"
    
    list_display = (
        'user_display',
        'xp_display',
        'level_badge',
        'progress_bar',
        'activity_count',
        'last_activity_display',
    )
    
    list_filter = (
        'level',
        'updated_at',
    )
    
    search_fields = (
        'user__username',
        'user__full_name',
        'user__telegram_id',
    )
    
    list_per_page = 25
    ordering = ('-xp',)
    autocomplete_fields = ('user',)
    
    # ❌ Inlinelarni o'chirib qo'ydik
    # inlines = [UserActivityDailyInline, LessonStatusInline, LectureStatusInline]
    
    fieldsets = (
        ("👤 Foydalanuvchi", {
            'fields': ('user',),
        }),
        ("📊 Statistika", {
            'fields': (
                ('xp', 'level'),
            ),
        }),
        ("📅 Vaqt", {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    # ========== DISPLAY METHODS ==========
    
    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return [name, f"ID: {obj.user.telegram_id}"]
    
    @display(description="XP", ordering='xp')
    def xp_display(self, obj):
        return format_html(
            '<span style="font-size: 20px; font-weight: 700; color: #8b5cf6;">⚡ {}</span>',
            obj.xp
        )
    
    @display(description="Daraja")
    def level_badge(self, obj):
        level_colors = {
            'beginner': ('#94a3b8', '🟡 Yangi boshlovchi'),
            'bronze': ('#cd7f32', '🥉 Bronza'),
            'silver': ('#c0c0c0', '🥈 Kumush'),
            'gold': ('#ffd700', '🥇 Oltin'),
            'pro': ('#7c3aed', '💎 Professional'),
        }
        color, label = level_colors.get(obj.level, ('#6b7280', obj.level))
        return mark_safe(
            f'<span style="background: {color}20; color: {color}; '
            f'padding: 4px 14px; border-radius: 20px; font-weight: 600; '
            f'font-size: 13px; border: 1px solid {color}40;">{label}</span>'
        )
    level_badge.admin_order_field = 'level'
    
    @display(description="Progress")
    def progress_bar(self, obj):
        # XP progressini hisoblash
        xp = obj.xp
        if xp < 2000:
            current = xp
            next_level = 2000
            percent = (current / next_level) * 100
            label = "Bronza"
        elif xp < 5000:
            current = xp - 2000
            next_level = 3000
            percent = (current / next_level) * 100
            label = "Kumush"
        elif xp < 8000:
            current = xp - 5000
            next_level = 3000
            percent = (current / next_level) * 100
            label = "Oltin"
        elif xp < 15000:
            current = xp - 8000
            next_level = 7000
            percent = (current / next_level) * 100
            label = "Professional"
        else:
            percent = 100
            label = "MAX"
        
        bar_color = '#8b5cf6' if percent < 50 else '#f59e0b' if percent < 80 else '#22c55e'
        percent = min(percent, 100)
        
        return format_html(
            '<div style="width: 150px;">'
            '<div style="display: flex; justify-content: space-between; font-size: 10px; color: #94a3b8;">'
            '<span>{}</span>'
            '<span>{:.1f}%</span>'
            '</div>'
            '<div style="width: 100%; height: 8px; background: #f1f5f9; border-radius: 10px; overflow: hidden;">'
            '<div style="width: {:.1f}%; height: 100%; background: {}; border-radius: 10px; transition: width 0.5s;"></div>'
            '</div>'
            '</div>',
            label, percent, percent, bar_color
        )
    
    @display(description="Faoliyat")
    def activity_count(self, obj):
        count = obj.user.activity_days.count()
        return format_html(
            '<span style="background: #e0f2fe; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">📅 {}</span>',
            count
        )
    
    @display(description="Oxirgi faollik")
    def last_activity_display(self, obj):
        last = obj.user.activity_days.order_by('-date').first()
        if last:
            return last.date.strftime("%d-%m-%Y")
        return "—"
    
    # ========== CHANGELIST VIEW (CHART MA'LUMOTLARI) ==========
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # 1. Umumiy statistika
        total_users = UserStats.objects.count()
        total_xp = UserStats.objects.aggregate(total=Sum('xp'))['total'] or 0
        avg_xp = UserStats.objects.aggregate(avg=Avg('xp'))['avg'] or 0
        
        # 2. Darajalar bo'yicha taqsimot
        level_stats = {}
        for level, label in UserStats.Level.choices:
            count = UserStats.objects.filter(level=level).count()
            level_stats[level] = {
                'label': label,
                'count': count,
                'percent': round((count / total_users) * 100, 1) if total_users > 0 else 0
            }
        
        # 3. So'nggi 7 kunlik faollik
        today = now().date()
        weekly_activity = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_xp = UserActivityDaily.objects.filter(
                date=date
            ).aggregate(total=Sum('xp_earned'))['total'] or 0
            weekly_activity.append({
                'date': date.strftime("%Y-%m-%d"),
                'label': date.strftime("%a"),
                'xp': daily_xp
            })
        
        # 4. Top 10 foydalanuvchilar (chart uchun)
        top_users = UserStats.objects.select_related('user').order_by('-xp')[:10]
        top_users_data = [
            {
                'username': stats.user.username or f"User#{stats.user.telegram_id}",
                'xp': stats.xp,
                'level': stats.get_level_display()
            }
            for stats in top_users
        ]
        
        # 5. So'nggi 30 kunlik heatmap ma'lumotlari
        heatmap_data = []
        for i in range(30, -1, -1):
            date = today - timedelta(days=i)
            activity = UserActivityDaily.objects.filter(date=date).aggregate(
                total=Sum('xp_earned')
            )['total'] or 0
            heatmap_data.append({
                'date': date.strftime("%Y-%m-%d"),
                'xp': activity
            })
        
        extra_context.update({
            'total_users': total_users,
            'total_xp': total_xp,
            'avg_xp': round(avg_xp, 1),
            'level_stats': level_stats,
            'weekly_activity': weekly_activity,
            'top_users': top_users_data,
            'heatmap_data': heatmap_data,
        })
        
        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# USER ACTIVITY DAILY ADMIN
# ============================================

@admin.register(UserActivityDaily)
class UserActivityDailyAdmin(ModelAdmin):
    list_display = (
        'user_display',
        'date_display',
        'xp_display',
        'tasks_display',
        'duration_display',
    )
    
    list_filter = (
        'date',
        'user',
    )
    
    search_fields = (
        'user__username',
        'user__full_name',
        'user__telegram_id',
    )
    
    list_per_page = 30
    ordering = ('-date',)
    autocomplete_fields = ('user',)
    
    fieldsets = (
        ("👤 Foydalanuvchi", {
            'fields': ('user',),
        }),
        ("📊 Faollik", {
            'fields': (
                'date',
                ('xp_earned', 'tasks_count'),
                'total_duration',
            )
        }),
    )
    
    readonly_fields = ('date',)
    
    @display(description="Foydalanuvchi", header=True)
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return [name, f"ID: {obj.user.telegram_id}"]
    
    @display(description="Sana")
    def date_display(self, obj):
        return obj.date.strftime("%d-%m-%Y")
    
    @display(description="XP")
    def xp_display(self, obj):
        return format_html(
            '<span style="color: #8b5cf6; font-weight: 600;">⚡ {}</span>',
            obj.xp_earned
        )
    
    @display(description="Vazifalar")
    def tasks_display(self, obj):
        return format_html(
            '<span style="background: #f1f5f9; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">📝 {}</span>',
            obj.tasks_count
        )
    
    @display(description="Vaqt")
    def duration_display(self, obj):
        hours = obj.total_duration // 60
        minutes = obj.total_duration % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


# ============================================
# LESSON STATUS ADMIN
# ============================================

@admin.register(LessonStatus)
class LessonStatusAdmin(ModelAdmin):
    list_display = (
        'user_display',
        'lesson_display',
        'finished_tasks_display',
        'status_badge',
        'completed_at_formatted',
    )
    
    list_filter = (
        'is_completed',
        'lesson__modul__course',
        'completed_at',
    )
    
    search_fields = (
        'user__username',
        'user__full_name',
        'lesson__title',
        'lesson__modul__title',
    )
    
    list_per_page = 30
    ordering = ('-completed_at',)
    autocomplete_fields = ('user', 'lesson')
    
    fieldsets = (
        ("👤 Talaba va Dars", {
            'fields': ('user', 'lesson'),
        }),
        ("📊 Holat", {
            'fields': (
                'finished_tasks_count',
                'is_completed',
                'completed_at',
            )
        }),
    )
    
    readonly_fields = ('completed_at',)
    
    @display(description="Talaba", header=True)
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return [name, f"ID: {obj.user.telegram_id}"]
    
    @display(description="Darslik")
    def lesson_display(self, obj):
        return format_html(
            '<a href="/admin/courses/lesson/{}/change/" style="color: #3b82f6;">📘 {}</a>',
            obj.lesson.id, obj.lesson.title[:40]
        )
    
    @display(description="Tugatilgan vazifalar")
    def finished_tasks_display(self, obj):
        total = obj.lesson.total_tasks_count or 0
        finished = obj.finished_tasks_count
        percent = round((finished / total) * 100, 1) if total > 0 else 0
        
        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px;">'
            '<span style="font-weight: 600;">{}/{}</span>'
            '<span style="font-size: 11px; color: #94a3b8;">({:.1f}%)</span>'
            '</div>',
            finished, total, percent
        )
    
    @display(description="Holat")
    def status_badge(self, obj):
        if obj.is_completed:
            return mark_safe(
                '<span style="background: #dcfce7; color: #15803d; padding: 4px 14px; '
                'border-radius: 20px; font-size: 12px; font-weight: 600;">✅ Tugatilgan</span>'
            )
        return mark_safe(
            '<span style="background: #fee2e2; color: #b91c1c; padding: 4px 14px; '
            'border-radius: 20px; font-size: 12px; font-weight: 600;">⏳ Davom etmoqda</span>'
        )
    
    @display(description="Tugatilgan vaqt")
    def completed_at_formatted(self, obj):
        if obj.completed_at:
            return obj.completed_at.strftime("%d-%m-%Y %H:%M")
        return "—"


# ============================================
# LECTURE STATUS ADMIN
# ============================================

@admin.register(LectureStatus)
class LectureStatusAdmin(ModelAdmin):
    list_display = (
        'user_display',
        'lecture_display',
        'status_badge',
        'completed_at_formatted',
    )
    
    list_filter = (
        'is_completed',
        'lecture__lesson__modul__course',
        'completed_at',
    )
    
    search_fields = (
        'user__username',
        'user__full_name',
        'lecture__title',
        'lecture__lesson__title',
    )
    
    list_per_page = 30
    ordering = ('-completed_at',)
    autocomplete_fields = ('user', 'lecture')
    
    fieldsets = (
        ("👤 Talaba va Ma'ruza", {
            'fields': ('user', 'lecture'),
        }),
        ("📊 Holat", {
            'fields': (
                'is_completed',
                'completed_at',
            )
        }),
    )
    
    readonly_fields = ('completed_at',)
    
    @display(description="Talaba", header=True)
    def user_display(self, obj):
        name = obj.user.full_name or obj.user.username or f"User#{obj.user.telegram_id}"
        return [name, f"ID: {obj.user.telegram_id}"]
    
    @display(description="Ma'ruza")
    def lecture_display(self, obj):
        return format_html(
            '<a href="/admin/courses/lecture/{}/change/" style="color: #8b5cf6;">📖 {}</a>',
            obj.lecture.id, obj.lecture.title[:40]
        )
    
    @display(description="Holat")
    def status_badge(self, obj):
        if obj.is_completed:
            return mark_safe(
                '<span style="background: #dcfce7; color: #15803d; padding: 4px 14px; '
                'border-radius: 20px; font-size: 12px; font-weight: 600;">✅ Tugatilgan</span>'
            )
        return mark_safe(
            '<span style="background: #fee2e2; color: #b91c1c; padding: 4px 14px; '
            'border-radius: 20px; font-size: 12px; font-weight: 600;">❌ Tugatilmagan</span>'
        )
    
    @display(description="Tugatilgan vaqt")
    def completed_at_formatted(self, obj):
        if obj.completed_at:
            return obj.completed_at.strftime("%d-%m-%Y %H:%M")
        return "—"