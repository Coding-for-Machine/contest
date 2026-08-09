from django.contrib import admin
from django.db.models import Sum, Count, Q
from django.utils.html import format_html
from django.urls import reverse
from django.templatetags.static import static

from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.contrib.filters.admin import RangeDateTimeFilter

from payment.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    """
    Invoice modeli uchun Django Unfold admin panel.
    Professional, to'liq funksional va chiroyli ko'rinishda.
    """

    # ============================================================
    # UNFOLD SOZLAMALARI
    # ============================================================
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True
    list_horizontal_scrollbar_top = True

    # ============================================================
    # LIST VIEW
    # ============================================================
    list_display = [
        "id",
        "user_link",
        "item_link",
        "amount_formatted",
        "provider_badge",
        "status_badge",
        "transaction_id_short",
        "created_at",
    ]

    list_filter = [
        "status",
        "provider",
        ("created_at", RangeDateTimeFilter),
        "course",
        "test",
        "contest",
    ]

    list_filter_submit = True
    list_select_related = ["user", "course", "test", "contest"]
    list_per_page = 50
    date_hierarchy = "created_at"

    search_fields = [
        "user__username",
        "user__telegram_id",
        "user__first_name",
        "transaction_id",
        "course__title",
        "test__title",
        "contest__title",
    ]
    ordering = ["-created_at"]

    # ============================================================
    # DETAIL VIEW (Fieldsets)
    # ============================================================
    fieldsets = (
        (
            "📋 Asosiy ma'lumotlar",
            {
                "classes": ["tab"],
                "fields": [
                    "user",
                    "amount",
                    ("status", "provider"),
                    "transaction_id",
                ],
            },
        ),
        (
            "🎯 To'lov ob'ekti (faqat bittasini tanlang)",
            {
                "classes": ["tab"],
                "description": "Invoice faqat bitta ob'ektga ulanishi kerak: Kurs, Test yoki Musobaqa.",
                "fields": [
                    ("course", "test", "contest"),
                ],
            },
        ),
        (
            "🕐 Vaqt ma'lumotlari",
            {
                "classes": ["tab"],
                "fields": [
                    ("created_at", "updated_at"),
                ],
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "item_type_display"]
    autocomplete_fields = ["user", "course", "test", "contest"]

    radio_fields = {
        "status": admin.VERTICAL,
        "provider": admin.HORIZONTAL,
    }

    # ============================================================
    # ACTIONS
    # ============================================================
    actions = ["mark_as_paid", "mark_as_cancelled", "mark_as_refunded", "export_to_csv"]

    @action(description="✅ To'langan deb belgilash")
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status=Invoice.Status.PAID)
        self.message_user(
            request,
            f"{updated} ta invoice to'langan deb belgilandi.",
            level="success",
        )

    @action(description="❌ Bekor qilingan deb belgilash")
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status=Invoice.Status.CANCELLED)
        self.message_user(
            request,
            f"{updated} ta invoice bekor qilingan deb belgilandi.",
            level="warning",
        )

    @action(description="↩️ Qaytarilgan deb belgilash")
    def mark_as_refunded(self, request, queryset):
        updated = queryset.update(status=Invoice.Status.REFUNDED)
        self.message_user(
            request,
            f"{updated} ta invoice qaytarilgan deb belgilandi.",
            level="info",
        )

    @action(description="📥 CSV ga eksport qilish")
    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="invoices.csv"'
        writer = csv.writer(response)
        writer.writerow(["ID", "User", "Amount", "Provider", "Status", "Created"])
        for inv in queryset:
            writer.writerow([
                inv.id,
                inv.user,
                inv.amount,
                inv.provider,
                inv.status,
                inv.created_at,
            ])
        return response

    # ============================================================
    # CUSTOM COLUMNS (@display bilan)
    # ============================================================
    @display(description="Foydalanuvchi", ordering="user__username")
    def user_link(self, obj):
        if not obj.user:
            return "—"
        url = reverse("admin:baseuser_baseuser_change", args=[obj.user.id])
        return format_html(
            '<a href="{}" class="text-primary-600 hover:underline font-medium">{}</a>',
            url,
            obj.user.username or obj.user.telegram_id or f"User #{obj.user.id}",
        )

    @display(description="Ob'ekt")
    def item_link(self, obj):
        item = obj.item
        if not item:
            return format_html('<span class="text-gray-400">—</span>')

        if obj.course:
            url = reverse("admin:courses_course_change", args=[obj.course.id])
            icon = "📚"
        elif obj.test:
            url = reverse("admin:quizs_test_change", args=[obj.test.id])
            icon = "📝"
        elif obj.contest:
            url = reverse("admin:contests_contest_change", args=[obj.contest.id])
            icon = "🏆"
        else:
            return "—"

        return format_html(
            '<a href="{}" class="text-primary-600 hover:underline">{} {}</a>',
            url,
            icon,
            str(item)[:40],
        )

    @display(description="Summa", ordering="amount")
    def amount_formatted(self, obj):
        return format_html(
            '<span class="font-mono font-bold text-gray-900">{:,.0f} UZS</span>',
            obj.amount,
        )

    @display(description="Provider")
    def provider_badge(self, obj):
        colors = {
            Invoice.Provider.PAYME: "bg-green-100 text-green-800 border-green-200",
            Invoice.Provider.CLICK: "bg-blue-100 text-blue-800 border-blue-200",
            Invoice.Provider.UZUM: "bg-purple-100 text-purple-800 border-purple-200",
            Invoice.Provider.PAYNET: "bg-orange-100 text-orange-800 border-orange-200",
        }
        css = colors.get(obj.provider, "bg-gray-100 text-gray-800")
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border {}">{}</span>',
            css,
            obj.get_provider_display(),
        )

    @display(description="Holati")
    def status_badge(self, obj):
        colors = {
            Invoice.Status.PENDING: "bg-yellow-100 text-yellow-800 border-yellow-200",
            Invoice.Status.PAID: "bg-green-100 text-green-800 border-green-200",
            Invoice.Status.CANCELLED: "bg-red-100 text-red-800 border-red-200",
            Invoice.Status.REFUNDED: "bg-gray-100 text-gray-800 border-gray-200",
        }
        css = colors.get(obj.status, "bg-gray-100 text-gray-800")
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border {}">{}</span>',
            css,
            obj.get_status_display(),
        )

    @display(description="Transaction ID")
    def transaction_id_short(self, obj):
        if not obj.transaction_id:
            return format_html('<span class="text-gray-400 italic">—</span>')
        tid = obj.transaction_id
        if len(tid) > 20:
            tid = tid[:17] + "..."
        return format_html(
            '<code class="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-gray-700">{}</code>',
            tid,
        )

    @display(description="Ob'ekt turi")
    def item_type_display(self, obj):
        types = {
            "course": ("📚 Kurs", "text-blue-600"),
            "test": ("📝 Test", "text-purple-600"),
            "contest": ("🏆 Musobaqa", "text-orange-600"),
        }
        label, color = types.get(obj.item_type, ("Noma'lum", "text-gray-500"))
        return format_html('<span class="font-medium {}">{}</span>', color, label)

    # ============================================================
    # QUERYSET OPTIMIZATSIYA
    # ============================================================
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "user", "course", "test", "contest"
        )

    # ============================================================
    # XAVFSIZLIK
    # ============================================================
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == Invoice.Status.PAID:
            return self.readonly_fields + ["amount", "user", "provider", "transaction_id"]
        return self.readonly_fields