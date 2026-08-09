# centers/admin.py
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.contrib.filters.admin import RangeDateFilter

from .models import Center


# ============================================================
# XODIM (NON-SUPERUSER) UCHUN TAHRIRLANMAYDIGAN MAYDONLAR
# ============================================================
# Direktor/markaz-bog'langan xodim o'z markazining kontakt ma'lumotlarini
# yangilay olsin, lekin markazni faollashtirish/o'chirish yoki direktorni
# almashtirish kabi og'ir ta'sirli amallarni FAQAT superuser bajara olsin.
SUPERUSER_ONLY_FIELDS = ("director", "is_active", "slug")


@admin.register(Center)
class CenterAdmin(ModelAdmin):
    """
    O'quv markazlari boshqaruv paneli.

    Huquq ierarxiyasi:
      1. Superuser — barcha markazlarni to'liq boshqaradi.
      2. Direktor / markazga biriktirilgan xodim — faqat o'z markazini
         ko'radi va cheklangan maydonlarni (nom, manzil, telefon) tahrirlay
         oladi; direktor va faollik holatini o'zgartira olmaydi.
      3. Boshqa foydalanuvchilar — hech narsa ko'rmaydi.
    """

    list_before_template = "admin/centers/center_stats_before_list.html"
    list_filter_submit = True
    compressed_fields = True
    show_full_result_count = True

    list_display = (
        "name_display",
        "director_display",
        "is_active_badge",
        "staff_count_display",
        "students_count_display",
        "created_at_formatted",
    )
    list_filter = (
        "is_active",
        ("created_at", RangeDateFilter),
    )
    search_fields = (
        "name",
        "slug",
        "address",
        "phone",
        "director__username",
        "director__first_name",
        "director__last_name",
    )
    list_per_page = 25
    ordering = ("-created_at",)
    autocomplete_fields = ("director",)

    fieldsets = (
        (_("🏢 Asosiy ma'lumotlar"), {
            "fields": (("name", "slug"), "address", "phone", "is_active"),
        }),
        (_("👤 Direktor"), {
            "fields": ("director",),
            "description": _(
                "Markaz direktori — bu foydalanuvchi markaz bo'yicha "
                "to'liq huquqga ega bo'ladi."
            ),
        }),
        (_("📅 Vaqt"), {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    readonly_fields = ("created_at",)

    # ============================================================
    # QUERYSET (N+1 oldini olish + Markaz filtrlash)
    # ============================================================

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .select_related("director")
            .annotate(
                _staff_count=Count("staff_profiles", distinct=True),
                _students_count=Count("students", distinct=True),
            )
        )

        if request.user.is_superuser:
            return qs

        # Direktor yoki markazga biriktirilgan xodim faqat o'z markazini ko'radi
        user_center = self._get_user_center(request)
        if user_center:
            return qs.filter(pk=user_center.pk)

        return qs.none()

    # ============================================================
    # TAHRIRLASH: og'ir ta'sirli maydonlar faqat superuser uchun
    # ============================================================

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            for field in SUPERUSER_ONLY_FIELDS:
                if field not in readonly:
                    readonly.append(field)
        return readonly

    # ============================================================
    # HUQUQLAR
    # ============================================================

    def has_add_permission(self, request):
        """Yangi markaz faqat superuser tomonidan yaratilishi mumkin."""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        user_center = self._get_user_center(request)
        if obj is None:
            # Changelist/admin-index darajasida: faqat markazga
            # biriktirilgan (yoki biror markazga direktor bo'lgan)
            # xodimlarga ko'rsatiladi — aks holda bo'sh ro'yxat ko'rinib,
            # noto'g'ri taassurot qoldiradi.
            return user_center is not None or self._is_any_director(request)
        # Direktor o'z markazini tahrirlay oladi
        if obj.director_id == request.user.pk:
            return True
        if user_center and user_center.pk == obj.pk:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        """Markazni o'chirish faqat superuser uchun."""
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        user_center = self._get_user_center(request)
        if obj is None:
            return user_center is not None or self._is_any_director(request)
        if user_center and user_center.pk == obj.pk:
            return True
        if obj.director_id == request.user.pk:
            return True
        return False

    # ============================================================
    # YORDAMCHI METODLAR
    # ============================================================

    def _get_user_center(self, request):
        """Xodimning `profile` orqali biriktirilgan markazini qaytaradi."""
        if not request.user.is_authenticated:
            return None
        try:
            profile = request.user.profile
        except ObjectDoesNotExist:
            return None
        if not profile:
            return None
        return profile.center

    def _is_any_director(self, request) -> bool:
        """Foydalanuvchi biror markazga direktor sifatida biriktirilganmi?"""
        if not request.user.is_authenticated:
            return False
        return Center.objects.filter(director=request.user).exists()

    # ============================================================
    # CHANGELIST DASHBOARD (Statistika)
    # ============================================================

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # MUHIM: statistika HAR DOIM joriy foydalanuvchi ko'ra oladigan
        # (superuser bo'lmasa — faqat o'z markazi) queryset ustida
        # hisoblanadi, global `Center.objects` ustida emas.
        scoped_qs = self.get_queryset(request)

        stats = scoped_qs.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            inactive=Count("id", filter=Q(is_active=False)),
            total_staff=Count("staff_profiles", distinct=True),
            total_students=Count("students", distinct=True),
        )

        total = stats["total"] or 0
        active = stats["active"] or 0
        active_percent = round((active / total) * 100, 1) if total else 0

        extra_context.update({
            "is_superuser": request.user.is_superuser,
            "total_centers": total,
            "active_centers": active,
            "inactive_centers": stats["inactive"] or 0,
            "active_percent": active_percent,
            "total_staff": stats["total_staff"] or 0,
            "total_students": stats["total_students"] or 0,
        })
        return super().changelist_view(request, extra_context=extra_context)

    # ============================================================
    # DISPLAY METHODS (Unfold bezaklari)
    # ============================================================

    @display(description=_("Markaz nomi"), header=True)
    def name_display(self, obj):
        return [obj.name, f"Slug: {obj.slug}"]

    @display(description=_("Direktor"))
    def director_display(self, obj):
        if obj.director:
            name = obj.director.get_full_name() or obj.director.username
            return format_html(
                '<span class="font-semibold text-gray-700 dark:text-gray-300">{}</span>',
                name,
            )
        return format_html('<span class="text-gray-400 italic">{}</span>', _("Tayinlanmagan"))

    @display(description=_("Holat"), ordering="is_active")
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold '
                'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">✅ {}</span>',
                _("Faol"),
            )
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold '
            'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">⛔ {}</span>',
            _("Nofaol"),
        )

    @display(description=_("Xodimlar"), ordering="_staff_count")
    def staff_count_display(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold '
            'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">👔 {}</span>',
            obj._staff_count,
        )

    @display(description=_("Talabalar"), ordering="_students_count")
    def students_count_display(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold '
            'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">🎓 {}</span>',
            obj._students_count,
        )

    @display(description=_("Yaratilgan"))
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")


# ============================================================
# IZOH: CenterScopedMixin
# ============================================================
# CenterScopedMixin — abstract model bo'lib, Course, Test, Contest,
# Problem va boshqa modellarda meros qilib olinadi. Unga alohida
# admin registratsiyasi talab qilinmaydi, chunki u o'z jadvaliga
# ega emas (abstract=True).
# ============================================================