# apps/baseuser/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone

from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.decorators import display
from unfold.paginator import InfinitePaginator

from .models import BaseUser, Profile


# ============================================
# 1. DEFAULT USER VA GROUP ADMIN'LARINI O'CHIRISH
# ============================================
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


# ============================================
# 2. DJANGO USER ADMIN
# ============================================
@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        'username_display',
        'email_display',
        'full_name_display',
        'rol_display',
        'is_active_badge',
        'is_staff_badge',
        'is_superuser_badge',
        'date_joined_display',
    )

    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        'groups',
        'date_joined',
    )

    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_per_page = 30
    ordering = ('-date_joined',)

    fieldsets = (
        ("👤 Shaxsiy Ma'lumotlar", {
            'fields': (('username', 'email'), ('first_name', 'last_name')),
        }),
        ("🔐 Kirish va Ruxsatlar", {
            'fields': (
                'password',
                ('is_active', 'is_staff', 'is_superuser'),
                'groups',
                'user_permissions',
            ),
        }),
        ("📅 Vaqt", {
            'fields': (('last_login', 'date_joined'),),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        ("👤 Shaxsiy Ma'lumotlar", {
            'fields': (('username', 'email'), ('first_name', 'last_name')),
        }),
        ("🔐 Kirish va Ruxsatlar", {
            'fields': (
                'password1',
                'password2',
                ('is_active', 'is_staff', 'is_superuser'),
                'groups',
                'user_permissions',
            ),
        }),
    )

    readonly_fields = ('last_login', 'date_joined')

    def has_module_perms(self, request):
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff

    @display(description="Foydalanuvchi", header=True)
    def username_display(self, obj):
        return [obj.username, f"ID: #{obj.id}"]

    @display(description="Email")
    def email_display(self, obj):
        if obj.email:
            return format_html(
                '<a href="mailto:{}" style="color:#3b82f6;text-decoration:none;">{}</a>',
                obj.email, obj.email,
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description="To'liq ism")
    def full_name_display(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        if name:
            return name
        return format_html('<span style="color:#94a3b8;font-style:italic;">To\'ldirilmagan</span>')

    @display(description="Rol")
    def rol_display(self, obj):
        groups = obj.groups.all()
        if not groups:
            return format_html('<span style="color:#94a3b8;">—</span>')
        colors = {
            "O'qituvchi":      "#3b82f6",
            "Masala Muallifi": "#f97316",
            "Kontent Menejer": "#8b5cf6",
            "Moderator":       "#14b8a6",
        }
        badges = ""
        for g in groups:
            color = colors.get(g.name, "#64748b")
            badges += (
                f'<span style="background:{color};color:white;padding:2px 10px;'
                f'border-radius:20px;font-size:11px;margin-right:4px;">{g.name}</span>'
            )
        return mark_safe(badges)

    @display(description="Faol")
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span style="background:#22c55e;color:white;padding:2px 10px;'
                'border-radius:20px;font-size:12px;">✅ Faol</span>'
            )
        return mark_safe(
            '<span style="background:#ef4444;color:white;padding:2px 10px;'
            'border-radius:20px;font-size:12px;">⛔ Nofaol</span>'
        )

    @display(description="Xodim")
    def is_staff_badge(self, obj):
        if obj.is_staff:
            return mark_safe(
                '<span style="background:#3b82f6;color:white;padding:2px 10px;'
                'border-radius:20px;font-size:12px;">👤 Xodim</span>'
            )
        return mark_safe('<span style="color:#94a3b8;">—</span>')

    @display(description="Admin")
    def is_superuser_badge(self, obj):
        if obj.is_superuser:
            return mark_safe(
                '<span style="background:#8b5cf6;color:white;padding:2px 10px;'
                'border-radius:20px;font-size:12px;">⭐ Admin</span>'
            )
        return mark_safe('<span style="color:#94a3b8;">—</span>')

    @display(description="Qo'shilgan")
    def date_joined_display(self, obj):
        return obj.date_joined.strftime("%d-%m-%Y %H:%M")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({
            'total_users':    User.objects.count(),
            'active_users':   User.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active=False).count(),
            'staff_users':    User.objects.filter(is_staff=True).count(),
            'superusers':     User.objects.filter(is_superuser=True).count(),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# 3. GROUP ADMIN
# ============================================
@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin, ModelAdmin):
    list_display = (
        'name_display',
        'users_count_display',
        'permissions_count_display',
    )

    search_fields = ('name',)
    list_per_page = 30
    ordering = ('name',)

    fieldsets = (
        ("👥 Guruh Ma'lumotlari", {
            'fields': ('name',),
        }),
        ("🔐 Ruxsatlar", {
            'fields': ('permissions',),
        }),
    )

    filter_horizontal = ('permissions',)

    def has_module_perms(self, request):
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff

    @display(description="Guruh nomi", header=True)
    def name_display(self, obj):
        return [obj.name, f"ID: #{obj.id}"]

    @display(description="A'zolar soni")
    def users_count_display(self, obj):
        count = obj.user_set.count()
        if count:
            return format_html(
                '<span style="background:#3b82f6;color:white;padding:2px 10px;'
                'border-radius:20px;font-size:12px;">👥 {}</span>', count,
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description="Ruxsatlar soni")
    def permissions_count_display(self, obj):
        count = obj.permissions.count()
        if count:
            return format_html(
                '<span style="background:#8b5cf6;color:white;padding:2px 10px;'
                'border-radius:20px;font-size:12px;">🔑 {}</span>', count,
            )
        return format_html('<span style="color:#94a3b8;">—</span>')


# ============================================
# 4. BASE USER ADMIN
# ============================================
@admin.register(BaseUser)
class BaseUserModelAdmin(ModelAdmin):
    paginator = InfinitePaginator
    show_full_result_count = False

    list_display = (
        'telegram_id_display',
        'username_display',
        'full_name_display',
        'phone_display',
        'is_active_badge',
        'last_login_display',
        'created_at_display',
    )

    list_filter = (
        'is_active',
        'created_at',
    )

    search_fields = (
        'telegram_id',
        'username',
        'full_name',
        'phone',
    )

    list_per_page = 30
    ordering = ('-created_at',)

    fieldsets = (
        ("👤 Asosiy Ma'lumotlar", {
            'fields': (
                ('telegram_id', 'username'),
                ('full_name', 'phone'),
                'is_active',
            ),
        }),
        ("📅 Vaqt", {
            'fields': (
                ('last_login', 'created_at', 'updated_at'),
            ),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    @display(description="Telegram ID", header=True)
    def telegram_id_display(self, obj):
        return [
            format_html(
                '<span style="font-weight:600;font-size:14px;">{}</span>',
                obj.telegram_id,
            ),
            f"ID: #{obj.id}",
        ]

    @display(description="Username")
    def username_display(self, obj):
        if obj.username:
            return format_html(
                '<a href="https://t.me/{}" target="_blank" '
                'style="color:#3b82f6;text-decoration:none;">'
                '<span class="material-icons" style="font-size:14px;vertical-align:middle;">send</span> @{}'
                '</a>',
                obj.username, obj.username,
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description="To'liq ism")
    def full_name_display(self, obj):
        if obj.full_name:
            return format_html('<span style="font-weight:500;">{}</span>', obj.full_name)
        return format_html('<span style="color:#94a3b8;font-style:italic;">To\'ldirilmagan</span>')

    @display(description="Telefon")
    def phone_display(self, obj):
        if obj.phone:
            return format_html(
                '<a href="tel:{}" style="color:#3b82f6;text-decoration:none;">'
                '<span class="material-icons" style="font-size:14px;vertical-align:middle;">phone</span> {}'
                '</a>',
                obj.phone, obj.phone,
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description="Holat")
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span style="background:#22c55e;color:white;padding:2px 12px;'
                'border-radius:20px;font-size:12px;display:inline-block;">✅ Faol</span>'
            )
        return mark_safe(
            '<span style="background:#ef4444;color:white;padding:2px 12px;'
            'border-radius:20px;font-size:12px;display:inline-block;">⛔ Nofaol</span>'
        )

    is_active_badge.admin_order_field = 'is_active'

    @display(description="Oxirgi kirish")
    def last_login_display(self, obj):
        if obj.last_login:
            diff = timezone.now() - obj.last_login
            if diff.days > 0:
                return f"{diff.days} kun oldin"
            elif diff.seconds > 3600:
                return f"{diff.seconds // 3600} soat oldin"
            elif diff.seconds > 60:
                return f"{diff.seconds // 60} daqiqa oldin"
            else:
                return "Hozirgina"
        return format_html('<span style="color:#94a3b8;">Hali kirish yo\'q</span>')

    @display(description="Qo'shilgan")
    def created_at_display(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        today    = timezone.now().date()
        week_ago = timezone.now() - timezone.timedelta(days=7)
        extra_context.update({
            'total_users':    BaseUser.objects.count(),
            'active_users':   BaseUser.objects.filter(is_active=True).count(),
            'inactive_users': BaseUser.objects.filter(is_active=False).count(),
            'today_users':    BaseUser.objects.filter(created_at__date=today).count(),
            'week_users':     BaseUser.objects.filter(created_at__gte=week_ago).count(),
        })
        return super().changelist_view(request, extra_context=extra_context)


# ============================================
# 5. PROFILE ADMIN
# ============================================
@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    paginator = InfinitePaginator
    show_full_result_count = False

    list_display = (
        'id_display',
        'user_display',
        'avatar_display',
        'bio_display',
        'website_display',
        'user_type_badge',
    )

    list_filter = (
        ('django_user', admin.EmptyFieldListFilter),
        ('student_user', admin.EmptyFieldListFilter),
    )

    search_fields = (
        'django_user__username',
        'django_user__email',
        'django_user__first_name',
        'django_user__last_name',
        'student_user__username',
        'student_user__full_name',
        'student_user__phone',
    )

    list_per_page = 30
    ordering = ('id',)

    fieldsets = (
        ("👤 Foydalanuvchi", {
            'fields': (
                ('django_user', 'student_user'),
            ),
        }),
        ("🖼️ Profil Ma'lumotlari", {
            'fields': (
                'avatar',
                'bio',
                'website',
            ),
        }),
    )

    readonly_fields = ()

    @display(description="ID", header=True)
    def id_display(self, obj):
        return [
            format_html('<span style="font-weight:600;">Profil #{}</span>', obj.id),
            None,
        ]

    @display(description="Foydalanuvchi")
    def user_display(self, obj):
        if obj.django_user:
            name = obj.django_user.get_full_name() or obj.django_user.username
            return format_html(
                '<span style="font-weight:500;">👤 {}</span>'
                '<br><span style="color:#94a3b8;font-size:11px;">{}</span>',
                name,
                obj.django_user.email or '—',
            )
        if obj.student_user:
            name = (
                obj.student_user.full_name
                or obj.student_user.username
                or f"#{obj.student_user.telegram_id}"
            )
            return format_html(
                '<span style="font-weight:500;">🎓 {}</span>'
                '<br><span style="color:#94a3b8;font-size:11px;">TG: {}</span>',
                name,
                obj.student_user.telegram_id,
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description="Avatar")
    def avatar_display(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;border-radius:50%;'
                'object-fit:cover;border:2px solid #e2e8f0;" />',
                obj.avatar.url,
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:36px;height:36px;border-radius:50%;background:#e2e8f0;'
            'color:#94a3b8;font-size:16px;">👤</span>'
        )

    @display(description="Bio")
    def bio_display(self, obj):
        if obj.bio:
            short = obj.bio[:60] + ('…' if len(obj.bio) > 60 else '')
            return format_html('<span style="color:#475569;font-size:12px;">{}</span>', short)
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description="Veb-sayt")
    def website_display(self, obj):
        if obj.website:
            return format_html(
                '<a href="{}" target="_blank" '
                'style="color:#3b82f6;text-decoration:none;font-size:12px;">'
                '🔗 {}</a>',
                obj.website,
                obj.website[:35] + ('…' if len(obj.website) > 35 else ''),
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    @display(description="Tur")
    def user_type_badge(self, obj):
        if obj.django_user and obj.student_user:
            return mark_safe(
                '<span style="background:#f59e0b;color:white;padding:2px 10px;'
                'border-radius:20px;font-size:11px;">⚠️ Ikkalasi</span>'
            )
        if obj.django_user:
            color = "#8b5cf6" if obj.django_user.is_superuser else "#3b82f6"
            label = "⭐ Admin" if obj.django_user.is_superuser else "👤 Xodim"
            return mark_safe(
                f'<span style="background:{color};color:white;padding:2px 10px;'
                f'border-radius:20px;font-size:11px;">{label}</span>'
            )
        if obj.student_user:
            return mark_safe(
                '<span style="background:#22c55e;color:white;padding:2px 10px;'
                'border-radius:20px;font-size:11px;">🎓 Talaba</span>'
            )
        return mark_safe('<span style="color:#94a3b8;">—</span>')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({
            'total_profiles': Profile.objects.count(),
            'with_avatar':    Profile.objects.exclude(avatar='').exclude(avatar=None).count(),
            'django_users':   Profile.objects.exclude(django_user=None).count(),
            'student_users':  Profile.objects.exclude(student_user=None).count(),
            'both_linked':    Profile.objects.exclude(django_user=None).exclude(student_user=None).count(),
        })
        return super().changelist_view(request, extra_context=extra_context)