# apps/users/forms.py
from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class BaseUserLoginForm(forms.Form):
    """
    Standart Django User modeli va Unfold uchun 
    1-bosqich xavfsiz login formasi (Username yoki Email).
    """
    username = forms.CharField(
        label="Foydalanuvchi nomi yoki Email",
        widget=forms.TextInput(attrs={
            "autofocus": True, 
            "class": "w-full",
            "placeholder": "Username yoki email kiriting"
        })
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password", 
            "class": "w-full",
            "placeholder": "••••••"
        })
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            # EmailOrUsername backend orqali standart User-ni tekshiramiz
            self.user_cache = authenticate(
                self.request, 
                username=username, 
                password=password
            )
            
            if self.user_cache is None:
                raise ValidationError(
                    _("Foydalanuvchi nomi, email yoki parol noto'g'ri!"),
                    code="invalid_login",
                )
            
            # ── 🛑 FAQAT STAFF VA SUPERUSER UCHUN FILTR ──
            elif not (self.user_cache.is_staff or self.user_cache.is_superuser):
                raise ValidationError(
                    _("Ushbu hisob xodim (Staff) yoki Administrator hisoblanmaydi!"),
                    code="not_staff",
                )
                
            elif not self.user_cache.is_active:
                raise ValidationError(
                    _("Ushbu hisob faolsizlantirilgan!"),
                    code="inactive",
                )

        return self.cleaned_data

    def get_user(self):
        return self.user_cache


from unfold.sites import UnfoldAdminSite

class CustomUnfoldAdminSite(UnfoldAdminSite):
    login_form = BaseUserLoginForm

custom_admin_site = CustomUnfoldAdminSite(name="custom_admin")
