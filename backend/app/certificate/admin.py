from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from .models import Certificate, CertificateTemplate
from .tasks import (
    bulk_generate_certificates,
    regenerate_certificate,
    bulk_regenerate_certificates,
    generate_certificate_files,
)


# ============================================================
# CERTIFICATE TEMPLATE ADMIN
# ============================================================

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(ModelAdmin):
    list_display = (
        "name",
        "template_type_badge",
        "organization_name",
        "verify_domain",
        "mentor_name",
        "is_active",
        "created_at",
    )
    list_filter = ("template_type", "is_active", "created_at")
    search_fields = ("name", "organization_name", "mentor_name")
    ordering = ("template_type", "name")
    list_editable = ("is_active",)
    list_per_page = 25

    fieldsets = (
        (
            _("Asosiy ma'lumotlar"),
            {
                "fields": ("name", "template_type", "is_active"),
                "classes": ("tab",),
            },
        ),
        (
            _("Tashkilot ma'lumotlari"),
            {
                "fields": ("organization_name", "verify_domain"),
                "classes": ("tab",),
            },
        ),
        (
            _("Mentor ma'lumotlari"),
            {
                "fields": ("mentor_name", "mentor_status"),
                "classes": ("tab",),
            },
        ),
        (
            _("Matn va dizayn"),
            {
                "fields": ("congratulation_text",),
                "classes": ("tab",),
            },
        ),
        (
            _("Rasmlar"),
            {
                "fields": ("logo", "signature", "background"),
                "classes": ("tab",),
                "description": "Rasmlar: Logo, Imzo va Fon rasmi",
            },
        ),
        (
            _("Vaqt"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at")

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
        "status_badge",
        "pdf_download",
        "qr_preview",
        "issued_at",
    )

    list_filter = (
        "status",
        "issued_at",
        "course",
        "test",
        "contest",
    )

    search_fields = (
        "certificate_code",
        "user__username",
        "user__first_name",
        "user__last_name",
        "course__title",
        "test__title",
        "contest__title",
    )

    readonly_fields = (
        "certificate_code",
        "issued_at",
        "qr_preview_large",
        "pdf_download",
        "verify_url_display",
        "template_snapshot_display",
        "source_type_display",
    )

    ordering = ("-issued_at",)
    date_hierarchy = "issued_at"
    list_per_page = 30

    fieldsets = (
        (
            _("👤 Foydalanuvchi"),
            {
                "fields": ("user",),
                "classes": ("tab",),
            },
        ),
        (
            _("📚 Manba"),
            {
                "fields": ("course", "test", "contest"),
                "classes": ("tab",),
                "description": "Sertifikat faqat bitta manbaga tegishli bo'lishi kerak",
            },
        ),
        (
            _("📋 Sertifikat ma'lumotlari"),
            {
                "fields": (
                    "certificate_code",
                    "template",
                    "source_type_display",
                    "template_snapshot_display",
                ),
                "classes": ("tab",),
            },
        ),
        (
            _("🔄 Generatsiya holati"),
            {
                "fields": ("status", "error_message", "retry_count"),
                "classes": ("tab",),
            },
        ),
        (
            _("📎 Generatsiya natijasi"),
            {
                "fields": ("qr_preview_large", "pdf_download", "verify_url_display"),
                "classes": ("tab",),
            },
        ),
        (
            _("📅 Vaqt"),
            {
                "fields": ("issued_at", "completed_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = (
        "action_regenerate_selected",
        "action_generate_selected",
    )

    # ============================
    # ACTIONS
    # ============================

    @action(
        description=_("🔄 Tanlangan sertifikatlarni qayta generatsiya qilish")
    )
    def action_regenerate_selected(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        bulk_regenerate_certificates.delay(ids)

        self.message_user(
            request,
            f"{len(ids)} ta sertifikat qayta generatsiya navbatiga qo'yildi.",
            messages.SUCCESS,
        )

    @action(
        description=_("⚡ Tanlangan sertifikatlarni generatsiya qilish")
    )
    def action_generate_selected(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        bulk_generate_certificates.delay(ids)

        self.message_user(
            request,
            f"{len(ids)} ta sertifikat generatsiya navbatiga qo'yildi.",
            messages.SUCCESS,
        )

    # ============================
    # DISPLAY
    # ============================

    @display(description=_("Foydalanuvchi"), header=True)
    def user_link(self, obj):
        return [
            obj.user_full_name,
            f"ID: {obj.user.id}",
        ]

    @display(description=_("Manba"))
    def source_title_display(self, obj):
        title = obj.source_title[:50]

        if obj.source_type == "course" and obj.course:
            url = reverse("admin:courses_course_change", args=[obj.course.id])
            return format_html('<a href="{}">📘 {}</a>', url, title)

        if obj.source_type == "test" and obj.test:
            url = reverse("admin:quizs_test_change", args=[obj.test.id])
            return format_html('<a href="{}">📝 {}</a>', url, title)

        if obj.source_type == "contest" and obj.contest:
            url = reverse("admin:contests_contest_change", args=[obj.contest.id])
            return format_html('<a href="{}">🏆 {}</a>', url, title)

        return title

    @display(description=_("Turi"), label=True)
    def source_type_badge(self, obj):
        labels = {
            "course": "📘 Kurs",
            "test": "📝 Test",
            "contest": "🏆 Musobaqa",
            "default": "📄 Default",
        }
        colors = {
            "course": "success",
            "test": "warning",
            "contest": "info",
            "default": "default",
        }
        return (
            labels.get(obj.source_type),
            colors.get(obj.source_type),
        )

    @display(description=_("Source Type"))
    def source_type_display(self, obj):
        labels = {
            "course": "📘 Kurs",
            "test": "📝 Test",
            "contest": "🏆 Musobaqa",
            "default": "📄 Default",
        }
        return labels.get(obj.source_type, obj.source_type)

    @display(description=_("Holat"), label=True)
    def status_badge(self, obj):
        labels = {
            "pending": "⏳ Kutilmoqda",
            "processing": "🔄 Jarayonda",
            "completed": "✅ Tayyor",
            "failed": "❌ Xato",
        }
        colors = {
            "pending": "warning",
            "processing": "info",
            "completed": "success",
            "failed": "danger",
        }
        return (
            labels.get(obj.status),
            colors.get(obj.status),
        )

    @display(description=_("PDF"))
    def pdf_download(self, obj):
        if obj.pdf_file:
            return format_html(
                '<a href="{}" target="_blank">📄 Yuklab olish</a>',
                obj.pdf_file.url,
            )
        return "—"

    @display(description=_("QR"))
    def qr_preview(self, obj):
        if obj.qr_code_image:
            return format_html(
                '<img src="{}" width="40" height="40"/>',
                obj.qr_code_image.url,
            )
        return "—"

    @display(description=_("QR Kod"))
    def qr_preview_large(self, obj):
        if obj.qr_code_image:
            return format_html(
                '<img src="{}" width="150"/>',
                obj.qr_code_image.url,
            )
        return "QR mavjud emas"

    @display(description=_("Tekshiruv URL"))
    def verify_url_display(self, obj):
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            obj.verify_url,
            obj.verify_url,
        )

    @display(description=_("Template snapshot"))
    def template_snapshot_display(self, obj):
        if not obj.template_snapshot:
            return "—"

        html = "<ul>"
        for key, value in obj.template_snapshot.items():
            html += f"<li><b>{key}</b>: {value}</li>"
        html += "</ul>"

        return format_html(html)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)