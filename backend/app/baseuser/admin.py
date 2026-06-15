# baseuser/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from unfold.admin import ModelAdmin
from .models import BaseUser

@admin.register(BaseUser)
class BaseUserAdmin(ModelAdmin):
    change_list_template = "admin/user_changelist.html"
    
    list_display = (
        'telegram_id_link', 
        'username_link',     
        'phone',
        'full_name',
        'status_badge',      
        'last_login_formatted',
        'created_at_formatted'
    )
    
    search_fields = ('telegram_id', 'username', 'phone', 'full_name')
    list_filter = ('is_active', 'created_at')
    ordering = ('-created_at',)
    
    def telegram_id_link(self, obj):
        return format_html('<strong>{}</strong>', obj.telegram_id)
    telegram_id_link.short_description = "Telegram ID"
    
    def username_link(self, obj):
        if obj.username:
            return format_html(
                '<a href="https://t.me/{0}" target="_blank" style="text-decoration:none; display:flex; align-items:center; gap:5px;">'
                '<img src="https://img.freepik.com/premium-vector/telegram-line-icon-communication-chat-message-photo-messenger-video-emoji-publications-subscribers-views-likes-comments-editorial_855332-4711.jpg" style="width:25px; height:25px;">'
                '<span style="color: #0088cc; font-weight: 500;">@{0}</span>'
                '</a>',
                obj.username
            )
        return "-"
    username_link.short_description = "Username"
    
    def status_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span style="background: #4CAF50; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">✓ Faol</span>')
        return mark_safe('<span style="background: #f44336; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">✗ Nofaol</span>')
    status_badge.short_description = "Holati"
    
    def last_login_formatted(self, obj):
        return obj.last_login.strftime("%Y-%m-%d %H:%M") if obj.last_login else "Hali kirish yo'q"
    last_login_formatted.short_description = "Oxirgi kirish"
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d") if obj.created_at else "-"
    created_at_formatted.short_description = "Qo'shilgan sana"
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['total_users'] = BaseUser.objects.count()
        extra_context['active_users'] = BaseUser.objects.filter(is_active=True).count()
        extra_context['inactive_users'] = BaseUser.objects.filter(is_active=False).count()
        extra_context['today_users'] = BaseUser.objects.filter(created_at__date=now().date()).count()
        return super().changelist_view(request, extra_context=extra_context)