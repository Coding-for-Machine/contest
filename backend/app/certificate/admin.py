from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .models import Certificate, CertificateTemplate
from .tasks import bulk_regenerate_certificates, regenerate_certificate


# ============================================================
# CERTIFICATE TEMPLATE ADMIN
# ============================================================

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(ModelAdmin):
    list_display = ("name", "template_type_badge", "organization_name", "verify_domain", "mentor_name")
    list_filter = ("template_type",)
    search_fields = ("name", "organization_name", "mentor_name")
    ordering = ("template_type",)

    fieldsets = (
        (
            _("Asosiy ma'lumotlar"),
            {
                "fields": ("name", "template_type", "organization_name", "verify_domain"),
                "classes": ("tab",),
            },
        ),
        (
            _("Mentor"),
            {
                "fields": ("mentor_name", "mentor_status", "mentor_signature"),
                "classes": ("tab",),
            },
        ),
        (
            _("Rasmlar va matn"),
            {
                "fields": ("logo_image", "illustration_image", "congratulation_text"),
                "classes": ("tab",),
            },
        ),
    )

    @display(description=_("Turi"), label=True)
    def template_type_badge(self, obj):
        colors = {
            "course": "success",
            "test": "warning",
            "contest": "info",
            "default": "default",
        }
        return obj.get_template_type_display(), colors.get(obj.template_type, "default")


# ============================================================
# CERTIFICATE ADMIN
# ============================================================

@admin.register(Certificate)
class CertificateAdmin(ModelAdmin):
    list_display = (
        "certificate_code",
        "user_link",
        "source_title_display",
        "source_type_badge",
        "pdf_download",
        "qr_preview",
        "issued_at",
    )
    list_filter = (
        "issued_at",
    )
    search_fields = (
        "certificate_code",
        "user__username",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = (
        "certificate_code",
        "issued_at",
        "qr_preview_large",
        "pdf_download",
        "verify_url_display",
    )
    ordering = ("-issued_at",)
    date_hierarchy = "issued_at"

    fieldsets = (
        (
            _("Foydalanuvchi"),
            {
                "fields": ("user",),
                "classes": ("tab",),
            },
        ),
        (
            _("Manba"),
            {
                "fields": ("course", "test", "test_session", "contest", "contest_registration"),
                "classes": ("tab",),
            },
        ),
        (
            _("Sertifikat"),
            {
                "fields": (
                    "certificate_code",
                    "verify_url_display",
                    "qr_preview_large",
                    "pdf_download",
                    "issued_at",
                ),
                "classes": ("tab",),
            },
        ),
    )

    actions = ["action_regenerate_selected"]

    # ----------------------------------------------------------
    # LIST DISPLAY METHODS
    # ----------------------------------------------------------

    @display(description=_("Foydalanuvchi"))
    def user_link(self, obj):
        name = obj.user.full_name or obj.user.username or str(obj.user)
        return format_html('<span style="font-weight:600">{}</span>', name)

    @display(description=_("Manba"))
    def source_title_display(self, obj):
        return obj.source_title

    @display(description=_("Turi"), label=True)
    def source_type_badge(self, obj):
        colors = {
            "course": "success",
            "test": "warning",
            "contest": "info",
        }
        labels = {
            "course": "Kurs",
            "test": "Test",
            "contest": "Musobaqa",
        }
        t = obj.source_type
        return labels.get(t, "Default"), colors.get(t, "default")

    @display(description=_("PDF"))
    def pdf_download(self, obj):
        if obj.pdf_file:
            return format_html(
                '<a href="{}" target="_blank" '
                'style="color:#2563eb;font-weight:600;text-decoration:none;">'
                '📄 Yuklab olish</a>',
                obj.pdf_file.url,
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description=_("QR"))
    def qr_preview(self, obj):
        if obj.qr_code_image:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;border-radius:4px;" />',
                obj.qr_code_image.url,
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    # ----------------------------------------------------------
    # READONLY DETAIL METHODS
    # ----------------------------------------------------------

    @display(description=_("QR Kod"))
    def qr_preview_large(self, obj):
        if obj.qr_code_image:
            return format_html(
                '<img src="{}" style="width:120px;height:120px;border:1px solid #e2e8f0;'
                'border-radius:8px;padding:4px;" />',
                obj.qr_code_image.url,
            )
        return _("Hali generatsiya qilinmagan")

    @display(description=_("Tekshiruv URL"))
    def verify_url_display(self, obj):
        url = obj.verify_url
        return format_html(
            '<a href="{}" target="_blank" style="color:#2563eb;">{}</a>',
            url, url,
        )

    # ----------------------------------------------------------
    # ADMIN ACTIONS
    # ----------------------------------------------------------

    @action(description=_("🔄 Tanlangan sertifikatlarni qayta generatsiya qilish"))
    def action_regenerate_selected(self, request, queryset):
        ids = [str(pk) for pk in queryset.values_list("pk", flat=True)]
        bulk_regenerate_certificates.delay(ids)
        self.message_user(
            request,
            _(f"{len(ids)} ta sertifikat qayta generatsiya navbatiga qo'yildi."),
            messages.SUCCESS,
        )

    # ----------------------------------------------------------
    # OBJECT-LEVEL ACTIONS (Unfold)
    # ----------------------------------------------------------

    @action(description=_("🔄 Qayta generatsiya"), url_path="regenerate")
    def object_regenerate(self, request, object_id):
        regenerate_certificate.delay(object_id)
        self.message_user(
            request,
            _("Sertifikat qayta generatsiya navbatiga qo'yildi."),
            messages.SUCCESS,
        )