from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "type",
        "title",
        "is_read",
        "created_at",
    )
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("title", "message", "user__username", "user__email")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)

    fieldsets = (
        (_("Asosiy ma'lumot"), {
            "fields": ("user", "type", "title", "message"),
        }),
        (_("Qo'shimcha"), {
            "fields": ("link", "meta", "is_read"),
        }),
        (_("Vaqt"), {
            "fields": ("created_at",),
        }),
    )

    actions = ["mark_as_read", "mark_as_unread"]

    @admin.action(description=_("Tanlanganlarni o'qilgan deb belgilash"))
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description=_("Tanlanganlarni o'qilmagan deb belgilash"))
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)