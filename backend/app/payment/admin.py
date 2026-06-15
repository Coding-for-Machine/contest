# payment/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Order, Invoice

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'get_item', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__telegram_id', 'id']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user']  # content_type ni o'chiring
    # autocomplete_fields = ['user']  # FAQAT user qoldi
    
    def get_item(self, obj):
        return str(obj.item) if obj.item else "-"
    get_item.short_description = "Mahsulot"

@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ['id', 'user', 'order', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'order__id']
    list_editable = ['status']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user', 'order']  # Bu ikki maydon ishlaydi