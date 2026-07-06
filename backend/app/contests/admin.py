# contests/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from .models import Contest, ContestPrize, ContestRegistration
from baseuser.utils.admin import BaseOwnerAdmin, BaseOwnerInline


@admin.register(Contest)
class ContestAdmin(BaseOwnerAdmin):
    """🏆 Musobaqa admin paneli - Unfold + BaseOwnerAdmin"""
    
    # List sahifasi
    list_display = (
        'title', 
        'type_display', 
        'status_display', 
        'start_time', 
        'end_time',
        'participants_info',
        'is_full_display',
        'is_active_display'
    )
    
    list_filter = (
        'status', 
        'type', 
        'is_active',
        'start_time',
        'end_time',
    )
    
    search_fields = ('title', 'slug', 'description', 'access_key')
    
    readonly_fields = (
        'type', 
        'status', 
        'slug',
        'created_at', 
        'updated_at',
        'participants_info',
        'completion_rate_display',
        'duration_display'
    )
    
    fieldsets = (
        (_('Asosiy maʼlumotlar'), {
            'fields': (
                'title', 
                'slug', 
                'description', 
                'cover_image',
            )
        }),
        (_('Vaqt parametrlari'), {
            'fields': (
                'start_time', 
                'end_time', 
                'registration_deadline'
            ),
        }),
        (_('Ishtirokchilar va cheklovlar'), {
            'fields': (
                'max_participants', 
                'questions_count', 
                'pass_score_percent'
            )
        }),
        (_('Maxfiylik va holat'), {
            'fields': (
                'access_key', 
                'type', 
                'status', 
                'is_active'
            ),
            'classes': ('collapse',)
        }),
        (_('Qo\'shimcha maʼlumotlar'), {
            'fields': (
                'intro_video',
                'created_at', 
                'updated_at',
                'participants_info',
                'completion_rate_display',
                'duration_display'
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Unfold uchun kompakt ko'rinish
    compressed_fields = True
    list_per_page = 25
    show_full_result_count = True
    
    # Qo'shimcha metodlar
    def type_display(self, obj):
        if obj.type == 'open':
            return format_html('<span style="color: #28a745;">🔓 Ochiq</span>')
        return format_html('<span style="color: #dc3545;">🔒 Yopiq</span>')
    type_display.short_description = _('Tur')
    type_display.admin_order_field = 'type'
    
    def status_display(self, obj):
        colors = {
            'upcoming': '#007bff',
            'ongoing': '#28a745',
            'ended': '#6c757d'
        }
        labels = {
            'upcoming': '⏳ Kutilmoqda',
            'ongoing': '▶️ Davom etmoqda',
            'ended': '✅ Yakunlangan'
        }
        color = colors.get(obj.status, '#6c757d')
        label = labels.get(obj.status, obj.status)
        return format_html(f'<span style="color: {color}; font-weight: bold;">{label}</span>')
    status_display.short_description = _('Holat')
    status_display.admin_order_field = 'status'
    
    def participants_info(self, obj):
        count = obj.participants_count
        max_count = obj.max_participants or '∞'
        return f"{count} / {max_count}"
    participants_info.short_description = _('Ishtirokchilar')
    
    def is_full_display(self, obj):
        if obj.is_full:
            return format_html('🔴 <b>To\'lgan</b>')
        return format_html('🟢 <b>Bo\'sh</b>')
    is_full_display.short_description = _('Holat')
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('✅ <b>Faol</b>')
        return format_html('⛔ <b>Noaktiv</b>')
    is_active_display.short_description = _('Faollik')
    
    def completion_rate_display(self, obj):
        return f"{obj.completion_rate_percent}%"
    completion_rate_display.short_description = _('Yakunlanish foizi')
    
    def duration_display(self, obj):
        minutes = obj.duration_minutes
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours} soat {mins} daqiqa"
        return f"{mins} daqiqa"
    duration_display.short_description = _('Davomiylik')
    
    # Unfold action'lar
    @action(description=_("Tanlovlarni faollashtirish"))
    def activate_contests(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _(f'{updated} ta musobaqa faollashtirildi.'))
    
    @action(description=_("Tanlovlarni noaktivlashtirish"))
    def deactivate_contests(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _(f'{updated} ta musobaqa noaktivlashtirildi.'))
    
    @action(description=_("Tanlovlarni nusxalash"))
    def copy_contests(self, request, queryset):
        for contest in queryset:
            contest.pk = None
            contest.title = f"{contest.title} (Nusxa)"
            contest.slug = None
            contest.save()
        self.message_user(request, _(f'{queryset.count()} ta musobaqa nusxalandi.'))
    
    actions = ['activate_contests', 'deactivate_contests', 'copy_contests']
    
    # Delete sahifasi uchun
    def delete_view(self, request, object_id, extra_context=None):
        context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj:
            context['registrations_count'] = obj.registrations.count()
            context['prizes_count'] = obj.prizes.count()
            context['delete_message'] = _(
                f'Ushbu musobaqani o\'chirishga ishonchingiz komilmi? '
                f'Barcha {context["registrations_count"]} ta ro\'yxatdan o\'tish va '
                f'{context["prizes_count"]} ta mukofot o\'chiriladi!'
            )
        return super().delete_view(request, object_id, extra_context=context)
    
    # Owner maydoni BaseOwnerAdmin orqali avtomat boshqariladi


@admin.register(ContestPrize)
class ContestPrizeAdmin(BaseOwnerAdmin):
    """🎁 Mukofotlar admin paneli"""
    
    list_display = ('contest', 'title', 'rank_target', 'monetary_value', 'created_at')
    list_filter = ('contest', 'rank_target')
    search_fields = ('title', 'description', 'contest__title')
    
    fieldsets = (
        (_('Mukofot ma\'lumotlari'), {
            'fields': ('contest', 'title', 'rank_target', 'monetary_value', 'image', 'description')
        }),
        (_('Admin ma\'lumotlari'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)
    compressed_fields = True
    
    # BaseOwnerAdmin avtomat owner bilan ishlaydi


@admin.register(ContestRegistration)
class ContestRegistrationAdmin(BaseOwnerAdmin):
    """👥 Ro'yxatdan o'tishlar admin paneli"""
    
    list_display = (
        'user_info', 
        'contest', 
        'status_display',
        'total_xp_earned',
        'rank_display',
        'accuracy_display',
        'started_at'
    )
    
    list_filter = (
        'status',
        'contest',
        'started_at',
        'completed_at',
    )
    
    search_fields = (
        'user__username', 
        'user__telegram_id',
        'contest__title',
        'id'
    )
    
    readonly_fields = (
        'id',
        'started_at',
        'completed_at',
        'total_xp_earned',
        'rank',
        'accuracy_display',
        'total_questions_display',
        'medal_display'
    )
    
    fieldsets = (
        (_('Ishtirokchi va musobaqa'), {
            'fields': (
                'id',
                'user',
                'contest',
                'status',
                'ip_address'
            )
        }),
        (_('Natijalar'), {
            'fields': (
                'correct_count',
                'wrong_count',
                'unanswered_count',
                'total_questions_display',
                'accuracy_display',
                'time_spent_seconds',
                'total_xp_earned',
                'rank',
                'medal_display'
            )
        }),
        (_('Vaqt parametrlari'), {
            'fields': ('started_at', 'completed_at')
        }),
    )
    
    compressed_fields = True
    list_per_page = 25
    
    def user_info(self, obj):
        username = getattr(obj.user, 'username', None) or getattr(obj.user, 'telegram_id', 'Noma\'lum')
        return format_html(f'👤 {username}')
    user_info.short_description = _('Ishtirokchi')
    user_info.admin_order_field = 'user__username'
    
    def status_display(self, obj):
        colors = {
            'in_progress': '#ffc107',
            'completed': '#28a745',
            'expired': '#6c757d',
            'disqualified': '#dc3545'
        }
        labels = {
            'in_progress': '⏳ Jarayonda',
            'completed': '✅ Yakunlangan',
            'expired': '⏰ Muddati o\'tgan',
            'disqualified': '🚫 Diskvalifikatsiya'
        }
        color = colors.get(obj.status, '#6c757d')
        label = labels.get(obj.status, obj.status)
        return format_html(f'<span style="color: {color}; font-weight: bold;">{label}</span>')
    status_display.short_description = _('Holat')
    status_display.admin_order_field = 'status'
    
    def rank_display(self, obj):
        if obj.rank:
            return format_html(f'#{obj.rank}')
        return '-'
    rank_display.short_description = _('O\'rin')
    
    def accuracy_display(self, obj):
        return f"{obj.accuracy_percent}%"
    accuracy_display.short_description = _('Aniqlik')
    
    def total_questions_display(self, obj):
        return obj.total_questions_answered
    total_questions_display.short_description = _('Javob berilgan')
    
    def medal_display(self, obj):
        return obj.medal or '❌'
    medal_display.short_description = _('Medal')
    
    @action(description=_("Ro'yxatdan o'tishlarni yakunlash"))
    def complete_registrations(self, request, queryset):
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, _(f'{updated} ta ro\'yxatdan o\'tish yakunlandi.'))
    
    @action(description=_("Ro'yxatdan o'tishlarni diskvalifikatsiya qilish"))
    def disqualify_registrations(self, request, queryset):
        updated = queryset.update(status='disqualified', completed_at=timezone.now())
        self.message_user(request, _(f'{updated} ta ro\'yxatdan o\'tish diskvalifikatsiya qilindi.'))
    
    actions = ['complete_registrations', 'disqualify_registrations']


# ============================================================
# INLINE ADMINLAR (Agar kerak bo'lsa)
# ============================================================

class ContestPrizeInline(BaseOwnerInline):
    """Mukofotlar inline ko'rinishida"""
    model = ContestPrize
    extra = 1
    fields = ('title', 'rank_target', 'monetary_value', 'image')
    show_change_link = True


class ContestRegistrationInline(BaseOwnerInline):
    """Ro'yxatdan o'tishlar inline ko'rinishida"""
    model = ContestRegistration
    extra = 0
    fields = ('user', 'status', 'total_xp_earned', 'rank')
    readonly_fields = ('total_xp_earned', 'rank')
    show_change_link = True
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False  # Ro'yxatdan o'tishni faqat bot orqali qo'shish mumkin