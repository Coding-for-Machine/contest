import json

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe # Mark_safe ni import qiling
from unfold.components import BaseComponent, register_component

from django.utils.timezone import now, timedelta
from .models import BaseUser
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group

from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass

@admin.register(BaseUser)
class BaseUserAdmin(ModelAdmin):
    change_list_template = "admin/baseuser_changelist.html"
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
        # O'zgaruvchi yo'q bo'lsa, format_html o'rniga mark_safe ishlatiladi
        if obj.is_active:
            return mark_safe(
                '<span style="background: #4CAF50; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">'
                '✓ Faol'
                '</span>'
            )
        return mark_safe(
            '<span style="background: #f44336; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">'
            '✗ Nofaol'
            '</span>'
        )
    status_badge.short_description = "Holati"
    
    def last_login_formatted(self, obj):
        if obj.last_login:
            return obj.last_login.strftime("%Y-%m-%d %H:%M")
        return "Hali kirish yo'q"
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d") if obj.created_at else "-"

    class Media:
        css = {'all': ('admin/css/custom.css',)}



from django.utils.timezone import now, timedelta

@register_component
class UsersPerDayChart(BaseComponent):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        days = [now() - timedelta(days=i) for i in range(6, -1, -1)]
        labels = [d.strftime("%a") for d in days]

        data = [
            BaseUser.objects.filter(created_at__date=d.date()).count()
            for d in days
        ]

        context.update({
            "height": 300,
            "data": json.dumps({
                "labels": labels,
                "datasets": [{
                    "label": "New Users",
                    "data": data,
                    "backgroundColor": "var(--color-primary-600)",
                }]
            })
        })

        return context

@register_component
class UserStatusChart(BaseComponent):
    def get_context_data(self, **kwargs):
        from .models import BaseUser

        context = super().get_context_data(**kwargs)

        active = BaseUser.objects.filter(is_active=True).count()
        inactive = BaseUser.objects.filter(is_active=False).count()

        context.update({
            "height": 300,
            "data": json.dumps({
                "labels": ["Active", "Inactive"],
                "datasets": [{
                    "label": "Users",
                    "data": [active, inactive],
                    "backgroundColor": [
                        "#4CAF50",
                        "#f44336"
                    ],
                }]
            })
        })

        return context
    
@register_component
class GrowthChart(BaseComponent):
    def get_context_data(self, **kwargs):
        from .models import BaseUser
        from django.utils.timezone import now, timedelta

        context = super().get_context_data(**kwargs)

        days = [now() - timedelta(days=i) for i in range(6, -1, -1)]
        labels = [d.strftime("%a") for d in days]

        total = 0
        cumulative = []

        for d in days:
            count = BaseUser.objects.filter(created_at__date=d.date()).count()
            total += count
            cumulative.append(total)

        context.update({
            "height": 300,
            "data": json.dumps({
                "labels": labels,
                "datasets": [{
                    "label": "Total Users Growth",
                    "data": cumulative,
                    "borderColor": "var(--color-primary-400)",
                    "type": "line",
                    "displayYAxis": True
                }]
            })
        })

        return context