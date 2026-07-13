import json

from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RelatedDropdownFilter,
    RangeDateFilter,
)

from .models import Contest, ContestPrize, ContestRegistration
from baseuser.utils.admin import BaseOwnerAdmin, BaseOwnerInline


CONTEST_CHART_COLORS = {
    "upcoming": "#3b82f6",
    "ongoing": "#22c55e",
    "ended": "#6b7280",
}


@admin.register(Contest)
class ContestAdmin(BaseOwnerAdmin):
    """🏆 Musobaqa admin paneli - Unfold + BaseOwnerAdmin"""

    list_before_template = "admin/contest/contest_stats_before_list.html"
    list_filter_submit = True  # Filter tagida "Submit" tugmasi (har bosishda reload bo'lmaydi)

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

    # Dropdown filterlar: choices-li maydonlar uchun ChoicesDropdownFilter,
    # sana oralig'i uchun RangeDateFilter (Select2 asosida, chiroyli UI)
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("type", ChoicesDropdownFilter),
        "is_active",
        ("start_time", RangeDateFilter),
        ("end_time", RangeDateFilter),
    )

    search_fields = ('title', 'slug', 'description', 'access_key')
    autocomplete_fields = ('owner', 'intro_video')

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
            'fields': ('title', 'slug', 'description', 'cover_image'),
        }),
        (_('Vaqt parametrlari'), {
            'fields': ('start_time', 'end_time', 'registration_deadline'),
        }),
        (_('Ishtirokchilar va cheklovlar'), {
            'fields': ('max_participants', 'questions_count', 'pass_score_percent')
        }),
        (_('Maxfiylik va holat'), {
            'fields': ('access_key', 'type', 'status', 'is_active'),
            'classes': ('collapse',)
        }),
        (_('Qo\'shimcha maʼlumotlar'), {
            'fields': (
                'intro_video', 'created_at', 'updated_at',
                'participants_info', 'completion_rate_display', 'duration_display'
            ),
            'classes': ('collapse',)
        }),
    )

    compressed_fields = True
    list_per_page = 25
    show_full_result_count = True

    # ---------- ORM optimallashtirish ----------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # participants_count property .registrations.count() ni har chaqirganda
        # qayta hisoblaydi (cache qilinmagan) — buni bitta annotate bilan almashtiramiz.
        # Model property'ga tegilmadi, faqat admin display shu annotatsiyani ishlatadi.
        return qs.annotate(_participants_count=Count('registrations', distinct=True))

    # ---------- Display metodlar ----------
    def type_display(self, obj):
        if obj.type == 'open':
            return format_html('<span style="color: #28a745;">🔓 Ochiq</span>')
        return format_html('<span style="color: #dc3545;">🔒 Yopiq</span>')
    type_display.short_description = _('Tur')
    type_display.admin_order_field = 'type'

    def status_display(self, obj):
        colors = {'upcoming': '#007bff', 'ongoing': '#28a745', 'ended': '#6c757d'}
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
        # Annotatsiya bo'lmagan holatlarda (masalan save_model dan keyingi
        # oddiy get_object chaqiruvida) property'ga fallback qilamiz.
        count = getattr(obj, '_participants_count', None)
        if count is None:
            count = obj.participants_count
        max_count = obj.max_participants or '∞'
        return f"{count} / {max_count}"
    participants_info.short_description = _('Ishtirokchilar')

    def is_full_display(self, obj):
        count = getattr(obj, '_participants_count', None)
        if count is None:
            count = obj.participants_count
        is_full = bool(obj.max_participants) and count >= obj.max_participants
        if is_full:
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

    # ---------- Actionlar ----------
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

    # ---------- Changelist dashboard konteksti ----------
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        stats = Contest.objects.aggregate(
            total=Count('id'),
            open_count=Count('id', filter=Q(type='open')),
            private_count=Count('id', filter=Q(type='private')),
            active_count=Count('id', filter=Q(is_active=True)),
            upcoming=Count('id', filter=Q(status='upcoming')),
            ongoing=Count('id', filter=Q(status='ongoing')),
            ended=Count('id', filter=Q(status='ended')),
        )

        extra_context.update({
            'total_contests': stats['total'],
            'open_contests': stats['open_count'],
            'private_contests': stats['private_count'],
            'active_contests': stats['active_count'],
            'upcoming_count': stats['upcoming'],
            'ongoing_count': stats['ongoing'],
            'ended_count': stats['ended'],
            'contest_status_chart_data': json.dumps({
                'labels': ["Kutilmoqda", "Davom etmoqda", "Yakunlangan"],
                'datasets': [{
                    'data': [stats['upcoming'], stats['ongoing'], stats['ended']],
                    'backgroundColor': [
                        CONTEST_CHART_COLORS['upcoming'],
                        CONTEST_CHART_COLORS['ongoing'],
                        CONTEST_CHART_COLORS['ended'],
                    ],
                    'borderWidth': 0,
                }],
            }),
        })

        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ContestPrize)
class ContestPrizeAdmin(BaseOwnerAdmin):
    """🎁 Mukofotlar admin paneli"""

    list_select_related = ('contest', 'owner')  # N+1 oldini olish

    list_display = ('contest', 'title', 'rank_target', 'monetary_value', 'created_at')

    list_filter = (
        ("contest", RelatedDropdownFilter),  # Select2 dropdown, kichik jadval uchun xavfsiz
        "rank_target",
    )
    list_filter_submit = True

    search_fields = ('title', 'description', 'contest__title')
    autocomplete_fields = ('contest',)

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


@admin.register(ContestRegistration)
class ContestRegistrationAdmin(BaseOwnerAdmin):
    """👥 Ro'yxatdan o'tishlar admin paneli"""

    list_before_template = "admin/contest/registration_stats_before_list.html"
    list_select_related = ('user', 'contest')  # N+1 oldini olish

    list_display = (
        'user_info',
        'contest',
        'status_display',
        'total_xp_earned',
        'rank_display',
        'accuracy_display',
        'started_at'
    )

    # DIQQAT: `user` filterga qo'shilmadi — hujjatga ko'ra Unfold dropdownlari
    # autocomplete qilib ishlamaydi, shuning uchun katta (foydalanuvchilar)
    # jadvallarni dropdown filterga qo'yish tavsiya etilmaydi. Qidiruv uchun
    # `search_fields` va FK autocomplete_fields yetarli.
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("contest", RelatedDropdownFilter),
        ("started_at", RangeDateFilter),
        ("completed_at", RangeDateFilter),
    )
    list_filter_submit = True

    search_fields = (
        'user__username',
        'user__telegram_id',
        'contest__title',
        'id'
    )
    autocomplete_fields = ('user', 'contest')

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
            'fields': ('id', 'user', 'contest', 'status', 'ip_address')
        }),
        (_('Natijalar'), {
            'fields': (
                'correct_count', 'wrong_count', 'unanswered_count',
                'total_questions_display', 'accuracy_display',
                'time_spent_seconds', 'total_xp_earned', 'rank', 'medal_display'
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
            'in_progress': '#ffc107', 'completed': '#28a745',
            'expired': '#6c757d', 'disqualified': '#dc3545'
        }
        labels = {
            'in_progress': '⏳ Jarayonda', 'completed': '✅ Yakunlangan',
            'expired': '⏰ Muddati o\'tgan', 'disqualified': '🚫 Diskvalifikatsiya'
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

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        stats = ContestRegistration.objects.aggregate(
            total=Count('id'),
            in_progress=Count('id', filter=Q(status='in_progress')),
            completed=Count('id', filter=Q(status='completed')),
            expired=Count('id', filter=Q(status='expired')),
            disqualified=Count('id', filter=Q(status='disqualified')),
        )

        extra_context.update({
            'reg_total': stats['total'],
            'reg_in_progress': stats['in_progress'],
            'reg_completed': stats['completed'],
            'reg_expired': stats['expired'],
            'reg_disqualified': stats['disqualified'],
        })

        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# INLINE ADMINLAR
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

    def get_queryset(self, request):
        # Inline jadvalida user ko'rsatilgani uchun select_related shart
        return super().get_queryset(request).select_related('user')

    def has_add_permission(self, request, obj=None):
        return False  # Ro'yxatdan o'tishni faqat bot orqali qo'shish mumkin