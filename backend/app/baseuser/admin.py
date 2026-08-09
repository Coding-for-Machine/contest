# baseuser/admin.py
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

from .models import BaseUser, Profile


# ============================================
# 1. DEFAULT DJANGO USER / GROUP NI O'CHIRISH
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
# 2. DJANGO USER ADMIN (Xodimlar/Staff)
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
        'groups_display',
        'is_active_badge',
        'is_staff_badge',
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
        ("👤 Shaxsiy ma'lumotlar", {
            'fields': (('username', 'email'), ('first_name', 'last_name')),
        }),
        ("🔐 Huquqlar", {
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
        ("👤 Shaxsiy ma'lumotlar", {
            'fields': (('username', 'email'), ('first_name', 'last_name')),
        }),
        ("🔐 Huquqlar", {
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

    @display(description="Foydalanuvchi", header=True)
    def username_display(self, obj):
        return [obj.username, f"ID: #{obj.id}"]

    @display(description="Email")
    def email_display(self, obj):
        if obj.email:
            return format_html(
                '<a href="mailto:{}" class="text-blue-500 hover:underline">{}</a>',
                obj.email, obj.email
            )
        return format_html('<span class="text-gray-400">—</span>')

    @display(description="To'liq ism")
    def full_name_display(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or format_html('<span class="text-gray-400 italic">To\'ldirilmagan</span>')

    @display(description="Guruhlar")
    def groups_display(self, obj):
        groups = obj.groups.all()
        if not groups:
            return format_html('<span class="text-gray-400">—</span>')
        badges = []
        for g in groups:
            badges.append(
                f'<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 mr-1">{g.name}</span>'
            )
        return mark_safe(''.join(badges))

    @display(description="Faol", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Xodim", boolean=True)
    def is_staff_badge(self, obj):
        return obj.is_staff

    @display(description="Qo'shilgan")
    def date_joined_display(self, obj):
        return obj.date_joined.strftime("%d-%m-%Y %H:%M")


# ============================================
# 3. GROUP ADMIN
# ============================================
@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin, ModelAdmin):
    list_display = ('name_display', 'users_count_display')
    search_fields = ('name',)
    list_per_page = 30
    ordering = ('name',)
    filter_horizontal = ('permissions',)

    @display(description="Guruh", header=True)
    def name_display(self, obj):
        return [obj.name, f"ID: #{obj.id}"]

    @display(description="A'zolar")
    def users_count_display(self, obj):
        count = obj.user_set.count()
        if count:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">👥 {}</span>',
                count
            )
        return format_html('<span class="text-gray-400">—</span>')


# ============================================
# 4. BASE USER ADMIN (Talabalar — Telegram)
# ============================================
@admin.register(BaseUser)
class BaseUserAdmin(ModelAdmin):
    """
    Telegram bot orqali ro'yxatdan o'tgan talabalar.
    Boshqa admin panellarda autocomplete_fields = ('user',) ishlashi
    uchun ushbu admin to'liq va xatosiz bo'lishi SHART.
    """

    list_display = (
        'telegram_id_display',
        'username_display',
        'full_name_display',
        'center_display',
        'is_active_badge',
        'last_login_display',
        'created_at_display',
    )
    list_filter = (
        'is_active',
        'center',
        'created_at',
    )
    search_fields = (
        'telegram_id',
        'username',
        'full_name',
        'phone',
        'center__name',
    )
    list_per_page = 30
    ordering = ('-created_at',)
    autocomplete_fields = ('center',)

    fieldsets = (
        ("👤 Asosiy ma'lumotlar", {
            'fields': (
                ('telegram_id', 'username'),
                ('full_name', 'phone'),
                'is_active',
            ),
        }),
        ("🏢 O'quv markazi", {
            'fields': ('center',),
        }),
        ("📅 Vaqt", {
            'fields': (('last_login', 'created_at', 'updated_at'),),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'last_login')

    @display(description="Telegram ID", header=True)
    def telegram_id_display(self, obj):
        return [str(obj.telegram_id), f"ID: #{obj.id}"]

    @display(description="Username")
    def username_display(self, obj):
        if obj.username:
            return format_html(
                '<a href="https://t.me/{}" target="_blank" class="text-blue-500 hover:underline">@{}</a>',
                obj.username, obj.username
            )
        return format_html('<span class="text-gray-400">—</span>')

    @display(description="To'liq ism")
    def full_name_display(self, obj):
        if obj.full_name:
            return format_html('<span class="font-medium">{}</span>', obj.full_name)
        return format_html('<span class="text-gray-400 italic">To\'ldirilmagan</span>')

    @display(description="Markaz")
    def center_display(self, obj):
        if obj.center:
            return format_html(
                '<a href="/admin/centers/center/{}/change/" class="text-blue-500 hover:underline">🏢 {}</a>',
                obj.center.id, obj.center.name[:30]
            )
        return format_html('<span class="text-gray-400">—</span>')

    @display(description="Faol", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Oxirgi kirish")
    def last_login_display(self, obj):
        if obj.last_login:
            return obj.last_login.strftime("%d-%m-%Y %H:%M")
        return format_html('<span class="text-gray-400">Hali kirish yo\'q</span>')

    @display(description="Qo'shilgan")
    def created_at_display(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M")


# ============================================
# 5. PROFILE ADMIN
# ============================================
@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = (
        'id_display',
        'owner_display',
        'type_badge',
        'center_display',
    )
    list_filter = (
        ('django_user', admin.EmptyFieldListFilter),
        ('student_user', admin.EmptyFieldListFilter),
        'center',
    )
    search_fields = (
        'django_user__username',
        'django_user__first_name',
        'django_user__last_name',
        'student_user__username',
        'student_user__full_name',
        'student_user__telegram_id',
        'center__name',
    )
    list_per_page = 30
    ordering = ('id',)
    autocomplete_fields = ('django_user', 'student_user', 'center')

    fieldsets = (
        ("👤 Foydalanuvchi", {
            'fields': (('django_user', 'student_user'),),
            'description': "Profil faqat bittasiga (Xodim YOKI Talaba) tegishli bo'lishi mumkin.",
        }),
        ("🏢 Markaz", {
            'fields': ('center',),
        }),
        ("🖼️ Qo'shimcha", {
            'fields': ('avatar', 'bio', 'website'),
            'classes': ('collapse',),
        }),
    )

    @display(description="Profil", header=True)
    def id_display(self, obj):
        return [f"Profil #{obj.id}", f"Center: {obj.center_id or '—'}"]

    @display(description="Egasi")
    def owner_display(self, obj):
        owner = obj.owner
        if not owner:
            return format_html('<span class="text-gray-400">—</span>')
        if obj.is_staff_profile:
            name = owner.get_full_name() or owner.username
            return format_html('<span class="font-semibold text-indigo-600">👔 {}</span>', name)
        name = owner.full_name or owner.username or f"User#{owner.telegram_id}"
        return format_html('<span class="font-semibold text-green-600">🎓 {}</span>', name)

    @display(description="Turi")
    def type_badge(self, obj):
        if obj.is_staff_profile:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">Xodim</span>'
            )
        if obj.is_student_profile:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Talaba</span>'
            )
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400">Bo\'sh</span>'
        )

    @display(description="Markaz")
    def center_display(self, obj):
        if obj.center:
            return format_html(
                '<a href="/admin/centers/center/{}/change/" class="text-blue-500 hover:underline">{}</a>',
                obj.center.id, obj.center.name[:30]
            )
        return format_html('<span class="text-gray-400">—</span>')