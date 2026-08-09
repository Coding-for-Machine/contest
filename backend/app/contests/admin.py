# contests/admin.py
import json

from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RelatedDropdownFilter,
    RangeDateFilter,
)

from .models import (
    Contest,
    ContestProblem,
    ContestPrize,
    ContestRegistration,
    ContestAnswer,
    CheatFlag,
)
from baseuser.utils.admin import BaseOwnerAdmin, BaseOwnerInline


# ============================================================
# RANG VA BELGI KONSTANTALARI
# ============================================================

CONTEST_STATUS_COLORS = {
    "upcoming": "#3b82f6",   # ko'k
    "ongoing": "#22c55e",    # yashil
    "ended": "#6b7280",      # kulrang
}

CONTEST_STATUS_ICONS = {
    "upcoming": "⏳",
    "ongoing": "▶️",
    "ended": "✅",
}

REGISTRATION_STATUS_COLORS = {
    "in_progress": "#f59e0b",
    "completed": "#22c55e",
    "expired": "#6b7280",
    "disqualified": "#ef4444",
}

REGISTRATION_STATUS_LABELS = {
    "in_progress": _("⏳ Jarayonda"),
    "completed": _("✅ Yakunlangan"),
    "expired": _("⏰ Muddati o'tgan"),
    "disqualified": _("🚫 Diskvalifikatsiya"),
}

CHEAT_REASON_ICONS = {
    "tab_switch": "🔄",
    "multiple_ip": "🌐",
    "copy_paste": "📋",
    "time_anomaly": "⏱️",
    "similar_code": "👥",
    "manual": "✋",
}


# ============================================================
# CONTEST STATUS — DB DA MAVJUD EMAS (Python @property)
# ============================================================
# `Contest.status` model darajasida haqiqiy ustun emas, balki
# `start_time`/`end_time` asosida hisoblanadigan @property. Shu sababli
# ORM darajasida na Q(status=...) bilan filtrlash, na list_filter'da oddiy
# maydon sifatida ishlatish mumkin — ikkalasi ham "Cannot resolve keyword"
# xatosini beradi. Buning o'rniga vaqt maydonlariga asoslangan Q obyektlari
# va maxsus SimpleListFilter ishlatiladi.

def _contest_status_q(status):
    now = timezone.now()
    if status == Contest.Status.UPCOMING:
        return Q(start_time__gt=now)
    if status == Contest.Status.ONGOING:
        return Q(start_time__lte=now, end_time__gte=now)
    # ENDED
    return Q(end_time__lt=now)


class ContestStatusListFilter(admin.SimpleListFilter):
    """`status` @property'ga mos, lekin real vaqt maydonlari orqali filtrlaydigan admin filtri."""

    title = _("Holat")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return Contest.Status.choices

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(_contest_status_q(self.value()))


# ============================================================
# ORTAK YORDAMCHI: MARKAZ DOIRASI (SCOPE) YORLIG'I
# ============================================================

class CenterScopedStatsMixin:
    """
    Statistika bloklari uchun umumiy yordamchi.
    - Superuser / Direktor → barcha markazlar bo'yicha statistika
    - Markaz Boshlig'i / Menejerlar / Moderator → faqat o'z markazi
    Bu klass `MultiCenterOwnerMixin` ustiga qo'yiladi (BaseOwnerAdmin orqali),
    shuning uchun `_get_user_center` va `_is_director` allaqachon mavjud.
    """

    def _stats_scope_label(self, request):
        if request.user.is_superuser:
            return str(_("🌍 Barcha markazlar (superuser)"))
        center = self._get_user_center(request)
        if center is None:
            return str(_("⚠️ Markaz biriktirilmagan"))
        return format_html("🏢 {}", center.name)

    def _stats_queryset(self, request, base_qs):
        """
        Statistika har doim foydalanuvchi ko'ra oladigan (center/owner bilan
        cheklangan) queryset ustida hisoblanadi — hech qachon global manager
        ustida emas. Shu bilan Markaz Boshlig'i faqat o'z markazining
        raqamlarini, Direktor/superuser esa hammasini ko'radi.
        """
        return self.get_queryset(request).filter(pk__in=base_qs.values("pk")) \
            if base_qs is not None else self.get_queryset(request)


# ============================================================
# INLINE ADMINLAR
# ============================================================

class ContestPrizeInline(BaseOwnerInline):
    """Musobaqa mukofotlari — ichki ko'rinish"""
    model = ContestPrize
    extra = 1
    fields = ("title", "rank_target", "description")
    show_change_link = True
    compressed_fields = True


class ContestRegistrationInline(BaseOwnerInline):
    """Ro'yxatdan o'tishlar — faqat o'qish rejimi"""
    model = ContestRegistration
    extra = 0
    fields = ("user", "status", "total_xp_earned", "rank", "started_at")
    readonly_fields = ("user", "status", "total_xp_earned", "rank", "started_at")
    show_change_link = True
    can_delete = False
    tab = True

    def has_add_permission(self, request, obj=None):
        return False


class ContestProblemInline(BaseOwnerInline):
    """Musobaqa bandlari (masala yoki test savoli)"""
    model = ContestProblem
    extra = 1
    fields = (
        "letter",
        "order_index",
        "problem",
        "question",
        "max_score",
        "is_scoring_dynamic",
    )
    autocomplete_fields = ("problem", "question")
    tab = True


# ============================================================
# CONTEST ADMIN
# ============================================================

@admin.register(Contest)
class ContestAdmin(CenterScopedStatsMixin, BaseOwnerAdmin):
    """🏆 Musobaqa boshqaruv paneli"""
    list_before_template = "admin/contest/contest_stats_before_list.html"
    list_filter_submit = True
    date_hierarchy = "start_time"
    ordering = ["-start_time"]

    # `owner` doim avtomatik biriktiriladi va yashirin.
    # `center` esa markazga bog'langan xodimlar uchun avtomatik/yashirin,
    # superuser (yoki markazi yo'q xodim) uchun esa ko'rinadigan va majburiy
    # bo'lib qoladi — buni BaseOwnerAdmin.get_form() dinamik hal qiladi,
    # shuning uchun bu yerda statik `exclude` ISHLATILMAYDI.

    list_display = (
        "title",
        "center_display",
        "contest_type_display",
        "visibility_display",
        "status_display",
        "start_time",
        "end_time",
        "participant_count_display",
        "format_display",
        "is_active_display",
    )
    list_filter = (
        ContestStatusListFilter,
        ("visibility", ChoicesDropdownFilter),
        ("contest_type", ChoicesDropdownFilter),
        ("format", ChoicesDropdownFilter),
        ("center", RelatedDropdownFilter),
        "is_active",
        ("start_time", RangeDateFilter),
        ("end_time", RangeDateFilter),
    )
    search_fields = (
        "title",
        "slug",
        "description",
        "access_key",
        "center__name",
        "owner__username",
    )
    autocomplete_fields = ("owner", "intro_video")
    inlines = (ContestPrizeInline, ContestProblemInline, ContestRegistrationInline)

    readonly_fields = (
        "status",
        "slug",
        "created_at",
        "updated_at",
        "is_running_display",
        "is_registration_open_display",
        "participant_count_display",
    )

    fieldsets = (
        (_("Asosiy"), {
            "fields": (
                "title",
                "slug",
                "description",
            ),
        }),
        (_("Vaqt parametrlari"), {
            "fields": (
                "start_time",
                "end_time",
                "registration_deadline",
                "duration_minutes",
            ),
        }),
        (_("Musobaqa sozlamalari"), {
            "fields": (
                "contest_type",
                "format",
                "penalty_minutes_per_wrong",
                "allow_practice",
            ),
        }),
        (_("Ko'rinish va kirish"), {
            "fields": (
                "visibility",
                "access_key",
                "is_active",
            ),
        }),
        (_("Media"), {
            "fields": (
                "intro_video",
            ),
        }),
        (_("Holat va meta"), {
            "fields": (
                "status",
                "is_running_display",
                "is_registration_open_display",
                "participant_count_display",
                "owner",
                "center",
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )

    compressed_fields = True
    list_per_page = 25
    show_full_result_count = True

    # ---------- Queryset optimallashtirish ----------

    def get_queryset(self, request):
        qs = super().get_queryset(request)  # MultiCenterOwnerMixin: markaz/owner bo'yicha cheklangan
        return qs.select_related("center", "owner").annotate(
            _participant_count=Count("registrations", distinct=True),
        )

    # ---------- Display metodlar ----------

    @display(description=_("Markaz"), label=True)
    def center_display(self, obj):
        if not obj.center_id:
            return format_html('<span class="text-gray-400">—</span>')
        return format_html("🏢 {}", obj.center.name)

    @display(description=_("Turi"), label=True)
    def contest_type_display(self, obj):
        labels = {
            "icpc": "ICPC",
            "dynamic": _("Dinamik"),
            "simple": _("Oddiy"),
        }
        return labels.get(obj.contest_type, obj.contest_type)

    @display(description=_("Ko'rinish"), label=True)
    def visibility_display(self, obj):
        if obj.visibility == Contest.Visibility.PUBLIC:
            return format_html(
                '<span class="text-green-600">🔓 {}</span>',
                _("Ochiq"),
            )
        return format_html(
            '<span class="text-red-600">🔒 {}</span>',
            _("Yopiq"),
        )

    @display(description=_("Holat"), label=True)
    def status_display(self, obj):
        color = CONTEST_STATUS_COLORS.get(obj.status, "#6b7280")
        icon = CONTEST_STATUS_ICONS.get(obj.status, "•")
        label = dict(Contest.Status.choices).get(obj.status, obj.status)
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>',
            color,
            icon,
            label,
        )

    @display(description=_("Ishtirokchilar"))
    def participant_count_display(self, obj):
        count = getattr(obj, "_participant_count", 0)
        return format_html(
            '{} <span class="text-gray-400">({})</span>',
            count,
            _("ro'yxatdan o'tgan"),
        )

    @display(description=_("Format"), label=True)
    def format_display(self, obj):
        labels = {
            "coding": _("💻 Dasturlash"),
            "quiz": _("📝 Test"),
            "mixed": _("🔀 Aralash"),
        }
        return labels.get(obj.format, obj.format)

    @display(description=_("Faollik"), boolean=True)
    def is_active_display(self, obj):
        return obj.is_active

    @display(description=_("Davom etmoqda"), boolean=True)
    def is_running_display(self, obj):
        return obj.is_running

    @display(description=_("Ro'yxatdan o'tish ochiq"), boolean=True)
    def is_registration_open_display(self, obj):
        return obj.is_registration_open

    # ---------- Actionlar (faqat o'zgartirish huquqi borlar uchun) ----------

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not self.has_change_permission(request):
            return {}
        return actions

    @action(description=_("Faollashtirish"))
    def activate_contests(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _(f"{updated} ta musobaqa faollashtirildi."))

    @action(description=_("Noaktivlashtirish"))
    def deactivate_contests(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _(f"{updated} ta musobaqa noaktivlashtirildi."))

    @action(description=_("Nusxalash"))
    def copy_contests(self, request, queryset):
        if not self.has_add_permission(request):
            self.message_user(request, _("Nusxalash uchun ruxsatingiz yo'q."), level="error")
            return
        count = 0
        for contest in queryset:
            contest.pk = None
            contest.title = f"{contest.title} (Nusxa)"
            contest.slug = None
            contest.is_active = False
            if not request.user.is_superuser:
                contest.owner = request.user
                user_center = self._get_user_center(request)
                if user_center:
                    contest.center = user_center
            contest.save()
            # Eslatma: M2M va inline ma'lumotlar avtomatik nusxalanmaydi
            count += 1
        self.message_user(request, _(f"{count} ta musobaqa nusxalandi."))

    actions = ("activate_contests", "deactivate_contests", "copy_contests")

    # ---------- O'chirish / List view ----------

    def delete_view(self, request, object_id, extra_context=None):
        context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj:
            context["registrations_count"] = obj.registrations.count()
            context["prizes_count"] = obj.prizes.count()
            context["delete_message"] = _(
                "Ushbu musobaqani o'chirishga ishonchingiz komilmi? "
                "Barcha %(reg)d ta ro'yxatdan o'tish va %(prize)d ta mukofot o'chiriladi!"
            ) % {
                "reg": context["registrations_count"],
                "prize": context["prizes_count"],
            }
        return super().delete_view(request, object_id, extra_context=context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # MUHIM: statistika HAR DOIM joriy foydalanuvchi ko'ra oladigan
        # (markaz/owner bo'yicha cheklangan) queryset ustida hisoblanadi.
        # Shunday qilib Markaz Boshlig'i faqat o'z markazi raqamlarini,
        # Direktor/superuser esa barcha markazlar bo'yicha umumiy
        # statistikani ko'radi.
        scoped_qs = self.get_queryset(request)

        stats = scoped_qs.aggregate(
            total=Count("id"),
            public_count=Count("id", filter=Q(visibility=Contest.Visibility.PUBLIC)),
            private_count=Count("id", filter=Q(visibility=Contest.Visibility.PRIVATE)),
            active_count=Count("id", filter=Q(is_active=True)),
            upcoming=Count("id", filter=_contest_status_q(Contest.Status.UPCOMING)),
            ongoing=Count("id", filter=_contest_status_q(Contest.Status.ONGOING)),
            ended=Count("id", filter=_contest_status_q(Contest.Status.ENDED)),
        )
        extra_context.update({
            "scope_label": self._stats_scope_label(request),
            "total_contests": stats["total"],
            "public_contests": stats["public_count"],
            "private_contests": stats["private_count"],
            "active_contests": stats["active_count"],
            "upcoming_count": stats["upcoming"],
            "ongoing_count": stats["ongoing"],
            "ended_count": stats["ended"],
            "contest_status_chart_data": json.dumps({
                "labels": [
                    str(_("Kutilmoqda")),
                    str(_("Davom etmoqda")),
                    str(_("Yakunlangan")),
                ],
                "datasets": [{
                    "data": [stats["upcoming"], stats["ongoing"], stats["ended"]],
                    "backgroundColor": [
                        CONTEST_STATUS_COLORS["upcoming"],
                        CONTEST_STATUS_COLORS["ongoing"],
                        CONTEST_STATUS_COLORS["ended"],
                    ],
                    "borderWidth": 0,
                }],
            }),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# CONTEST PROBLEM ADMIN
# ============================================================

@admin.register(ContestProblem)
class ContestProblemAdmin(BaseOwnerAdmin):
    """🔗 Contest — Masala/Savol bog'lash paneli"""
    list_select_related = ("contest", "contest__center", "problem", "question")
    ordering = ["contest", "order_index"]
    list_display = (
        "contest",
        "letter",
        "target_title",
        "order_index",
        "max_score",
        "is_scoring_dynamic",
        "is_quiz",
    )
    list_filter = (
        ("contest", RelatedDropdownFilter),
        "is_scoring_dynamic",
    )
    list_filter_submit = True
    search_fields = (
        "contest__title",
        "problem__title",
        "question__text",
        "letter",
    )
    autocomplete_fields = ("contest", "problem", "question")
    compressed_fields = True
    list_per_page = 50

    fieldsets = (
        (_("Asosiy"), {
            "fields": (
                "contest",
                "letter",
                "order_index",
            ),
        }),
        (_("Masala yoki Savol (XOR)"), {
            "fields": (
                "problem",
                "question",
            ),
            "description": _("Ikkisidan faqat bittasini tanlang. XOR qoidasi shart."),
        }),
        (_("Ball sozlamalari"), {
            "fields": (
                "max_score",
                "is_scoring_dynamic",
            ),
        }),
    )

    def _get_center_filter_path(self):
        return "contest__center"

    @display(description=_("Sarlavha"))
    def target_title(self, obj):
        if obj.problem:
            return obj.problem.title
        if obj.question:
            return str(obj.question.text)[:50]
        return "—"

    @display(description=_("Turi"), boolean=True)
    def is_quiz(self, obj):
        return obj.is_quiz


# ============================================================
# CONTEST PRIZE ADMIN
# ============================================================

@admin.register(ContestPrize)
class ContestPrizeAdmin(BaseOwnerAdmin):
    list_select_related = ("contest", "contest__center", "owner")
    ordering = ["rank_target"]
    list_display = (
        "contest",
        "title",
        "rank_target_display",
        "created_at",
    )
    list_filter = (
        ("contest", RelatedDropdownFilter),
        "rank_target",
    )
    list_filter_submit = True
    search_fields = (
        "title",
        "description",
        "contest__title",
    )
    autocomplete_fields = ("contest",)
    readonly_fields = ("created_at",)
    compressed_fields = True
    list_per_page = 25

    fieldsets = (
        (_("Mukofot"), {
            "fields": (
                "contest",
                "title",
                "rank_target",
                "description",
            ),
        }),
        (_("Meta"), {
            "fields": ("owner", "created_at"),
            "classes": ("collapse",),
        }),
    )

    def _get_center_filter_path(self):
        return "contest__center"

    @display(description=_("O'rin"), label=True)
    def rank_target_display(self, obj):
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        medal = medals.get(obj.rank_target, "🎖️")
        return format_html(
            '<span style="font-weight:700;font-size:14px;">{} #{} — {}</span>',
            medal,
            obj.rank_target,
            _("o'rin"),
        )


# ============================================================
# CONTEST REGISTRATION ADMIN
# ============================================================

@admin.register(ContestRegistration)
class ContestRegistrationAdmin(CenterScopedStatsMixin, BaseOwnerAdmin):
    """👥 Ro'yxatdan o'tishlar boshqaruv paneli"""
    list_before_template = "admin/contest/registration_stats_before_list.html"
    list_select_related = ("user", "contest", "contest__center")
    ordering = ["rank", "-score", "penalty_minutes"]
    list_display = (
        "user_info",
        "contest",
        "center_display",
        "status_display",
        "score",
        "total_xp_earned",
        "rank_display",
        "accuracy_display",
        "time_spent_display",
        "started_at",
    )
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("contest", RelatedDropdownFilter),
        ("contest__center", RelatedDropdownFilter),
        ("started_at", RangeDateFilter),
        ("completed_at", RangeDateFilter),
    )
    list_filter_submit = True
    search_fields = (
        "user__username",
        "user__telegram_id",
        "contest__title",
        "id",
    )
    autocomplete_fields = ("user", "contest")
    compressed_fields = True
    list_per_page = 25

    readonly_fields = (
        "id",
        "user",
        "contest",
        "started_at",
        "completed_at",
        "accuracy_display",
        "total_questions_display",
        "medal_display",
        "time_spent_display",
        "total_questions_answered",
        "correct_count",
        "wrong_count",
        "unanswered_count",
        "score",
        "penalty_minutes",
        "total_xp_earned",
        "rank",
        "ip_address",
    )

    fieldsets = (
        (_("Ishtirokchi va musobaqa"), {
            "fields": (
                "id",
                "user",
                "contest",
                "status",
                "ip_address",
            ),
        }),
        (_("Natijalar"), {
            "fields": (
                "correct_count",
                "wrong_count",
                "unanswered_count",
                "total_questions_display",
                "accuracy_display",
                "time_spent_display",
                "score",
                "penalty_minutes",
                "total_xp_earned",
                "rank",
                "medal_display",
            ),
        }),
        (_("Vaqt parametrlari"), {
            "fields": (
                "started_at",
                "completed_at",
            ),
        }),
        (_("Meta"), {
            "fields": ("owner", "xp_awarded"),
            "classes": ("collapse",),
        }),
    )

    def _get_center_filter_path(self):
        return "contest__center"

    # ---------- Display metodlar ----------

    @display(description=_("Ishtirokchi"), ordering="user__username")
    def user_info(self, obj):
        username = getattr(obj.user, "username", None)
        tid = getattr(obj.user, "telegram_id", None)
        name = username or tid or _("Noma'lum")
        return format_html("👤 {}", name)

    @display(description=_("Markaz"), label=True)
    def center_display(self, obj):
        center = getattr(obj.contest, "center", None)
        if not center:
            return format_html('<span class="text-gray-400">—</span>')
        return format_html("🏢 {}", center.name)

    @display(description=_("Holat"), label=True)
    def status_display(self, obj):
        color = REGISTRATION_STATUS_COLORS.get(obj.status, "#6b7280")
        label = REGISTRATION_STATUS_LABELS.get(obj.status, obj.status)
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            color,
            label,
        )

    @display(description=_("O'rin"), ordering="rank")
    def rank_display(self, obj):
        if obj.rank:
            return format_html(
                '<span class="font-bold text-lg">#{}</span>',
                obj.rank,
            )
        return "-"

    @display(description=_("Aniqlik"))
    def accuracy_display(self, obj):
        return f"{obj.accuracy_percent}%"

    @display(description=_("Javob berilgan"))
    def total_questions_display(self, obj):
        return obj.total_questions_answered

    @display(description=_("Medal"))
    def medal_display(self, obj):
        return obj.medal or format_html(
            '<span class="text-gray-400">—</span>'
        )

    @display(description=_("Sarflangan vaqt"))
    def time_spent_display(self, obj):
        total = obj.time_spent_seconds or 0
        m, s = divmod(total, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    # ---------- Qo'lda status o'zgartirish (faqat manager) ----------

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not self.has_change_permission(request):
            return {}
        return actions

    @action(description=_("Yakunlash"))
    def complete_registrations(self, request, queryset):
        updated = queryset.update(
            status=ContestRegistration.Status.COMPLETED,
            completed_at=timezone.now(),
        )
        self.message_user(request, _(f"{updated} ta ro'yxatdan o'tish yakunlandi."))

    @action(description=_("Diskvalifikatsiya qilish"))
    def disqualify_registrations(self, request, queryset):
        updated = queryset.update(
            status=ContestRegistration.Status.DISQUALIFIED,
            completed_at=timezone.now(),
        )
        self.message_user(request, _(f"{updated} ta ro'yxatdan o'tish diskvalifikatsiya qilindi."))

    actions = ("complete_registrations", "disqualify_registrations")

    # ---------- Ruxsatlar: ro'yxatdan o'tishlarni qo'lda yaratib/yo'qotib bo'lmaydi ----------

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Har doim joriy foydalanuvchi ko'ra oladigan (markaz bo'yicha
        # cheklangan) queryset ustida hisoblanadi.
        scoped_qs = self.get_queryset(request)

        stats = scoped_qs.aggregate(
            total=Count("id"),
            in_progress=Count("id", filter=Q(status=ContestRegistration.Status.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=ContestRegistration.Status.COMPLETED)),
            expired=Count("id", filter=Q(status=ContestRegistration.Status.EXPIRED)),
            disqualified=Count("id", filter=Q(status=ContestRegistration.Status.DISQUALIFIED)),
        )
        extra_context.update({
            "scope_label": self._stats_scope_label(request),
            "reg_total": stats["total"],
            "reg_in_progress": stats["in_progress"],
            "reg_completed": stats["completed"],
            "reg_expired": stats["expired"],
            "reg_disqualified": stats["disqualified"],
            "registration_status_chart_data": json.dumps({
                "labels": [
                    str(REGISTRATION_STATUS_LABELS["in_progress"]),
                    str(REGISTRATION_STATUS_LABELS["completed"]),
                    str(REGISTRATION_STATUS_LABELS["expired"]),
                    str(REGISTRATION_STATUS_LABELS["disqualified"]),
                ],
                "datasets": [{
                    "data": [
                        stats["in_progress"],
                        stats["completed"],
                        stats["expired"],
                        stats["disqualified"],
                    ],
                    "backgroundColor": [
                        REGISTRATION_STATUS_COLORS["in_progress"],
                        REGISTRATION_STATUS_COLORS["completed"],
                        REGISTRATION_STATUS_COLORS["expired"],
                        REGISTRATION_STATUS_COLORS["disqualified"],
                    ],
                    "borderWidth": 0,
                }],
            }),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# CONTEST ANSWER ADMIN (Quiz javoblari) — FAQAT KO'RISH
# ============================================================

@admin.register(ContestAnswer)
class ContestAnswerAdmin(BaseOwnerAdmin):
    """📮 Contest ichidagi test javoblari (read-only)"""
    list_select_related = (
        "registration__user",
        "registration__contest",
        "registration__contest__center",
        "contest_problem",
        "choice",
    )
    ordering = ["-answered_at"]
    list_display = (
        "registration_info",
        "contest_problem",
        "choice",
        "is_true_display",
        "answered_at",
    )
    list_filter = (
        ("contest_problem__contest", RelatedDropdownFilter),
        ("contest_problem__contest__center", RelatedDropdownFilter),
        ("choice__is_correct", admin.BooleanFieldListFilter),
    )
    list_filter_submit = True
    search_fields = (
        "registration__user__username",
        "registration__user__telegram_id",
        "contest_problem__letter",
        "contest_problem__contest__title",
    )
    autocomplete_fields = ("registration", "contest_problem", "choice")
    readonly_fields = ("registration", "contest_problem", "choice", "is_true_display", "answered_at", "time_offset_seconds")
    compressed_fields = True
    list_per_page = 50

    fieldsets = (
        (_("Asosiy"), {
            "fields": (
                "registration",
                "contest_problem",
                "choice",
            ),
        }),
        (_("Natija"), {
            "fields": (
                "is_true_display",
                "time_offset_seconds",
                "answered_at",
            ),
        }),
    )

    def _get_center_filter_path(self):
        return "contest_problem__contest__center"

    @display(description=_("Ro'yxatdan o'tish"))
    def registration_info(self, obj):
        user = getattr(obj.registration.user, "username", None) \
            or getattr(obj.registration.user, "telegram_id", "Noma'lum")
        return f"{user} — {obj.registration.contest.title}"

    @display(description=_("To'g'ri"), boolean=True)
    def is_true_display(self, obj):
        return obj.is_true

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ============================================================
# CHEAT FLAG ADMIN (Shubhali harakatlar)
# ============================================================

@admin.register(CheatFlag)
class CheatFlagAdmin(BaseOwnerAdmin):
    list_select_related = ("registration__user", "registration__contest", "registration__contest__center", "reviewed_by")
    ordering = ["-detected_at"]
    list_display = (
        "registration_info",
        "reason_display",
        "detected_at",
        "reviewed_display",
    )
    list_filter = (
        ("reason", ChoicesDropdownFilter),
        "reviewed",
        ("registration__contest__center", RelatedDropdownFilter),
        ("detected_at", RangeDateFilter),
    )
    list_filter_submit = True
    search_fields = (
        "registration__user__username",
        "registration__user__telegram_id",
        "registration__contest__title",
        "detail",
    )
    autocomplete_fields = ("registration", "reviewed_by")
    readonly_fields = ("detected_at", "registration", "reason", "detail")
    compressed_fields = True
    list_per_page = 50

    fieldsets = (
        (_("Asosiy"), {
            "fields": (
                "registration",
                "reason",
                "detail",
            ),
        }),
        (_("Ko'rib chiqish"), {
            "fields": (
                "reviewed",
                "reviewed_by",
            ),
        }),
        (_("Vaqt"), {
            "fields": ("detected_at",),
            "classes": ("collapse",),
        }),
    )

    def _get_center_filter_path(self):
        return "registration__contest__center"

    @display(description=_("Ro'yxatdan o'tish"))
    def registration_info(self, obj):
        user = getattr(obj.registration.user, "username", None) \
            or getattr(obj.registration.user, "telegram_id", "Noma'lum")
        return f"{user} — {obj.registration.contest.title}"

    @display(description=_("Sabab"), label=True)
    def reason_display(self, obj):
        icon = CHEAT_REASON_ICONS.get(obj.reason, "⚠️")
        return format_html(
            '<span style="font-weight:600;">{} {}</span>',
            icon,
            obj.get_reason_display(),
        )

    @display(description=_("Ko'rib chiqilgan"), boolean=True)
    def reviewed_display(self, obj):
        return obj.reviewed

    @action(description=_("Ko'rib chiqilgan deb belgilash"))
    def mark_reviewed(self, request, queryset):
        updated = queryset.update(reviewed=True, reviewed_by=request.user)
        self.message_user(request, _(f"{updated} ta shubhali harakat ko'rib chiqildi deb belgilandi."))

    actions = ("mark_reviewed",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser