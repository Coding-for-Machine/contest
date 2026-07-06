# baseuser/utils/admin.py
from django import forms
from unfold.admin import ModelAdmin, TabularInline


# ============================================================
# GURUH KONFIGURATSIYASI
# ============================================================

OWNER_ONLY_GROUPS  = ["O'qituvchi", "Masala Muallifi"]
READ_ONLY_GROUPS   = ["Moderator"]
FULL_MANAGE_GROUPS = ["Kontent Menejer"]


# ============================================================
# MIXIN — huquq logikasi
# ============================================================

class OwnerPermissionMixin:
    """Faqat huquq metodlarini o'z ichiga oladi"""

    def _in_group(self, request, *group_names) -> bool:
        return request.user.groups.filter(name__in=group_names).exists()

    def _is_owner_only(self, request) -> bool:
        return self._in_group(request, *OWNER_ONLY_GROUPS)

    def _is_read_only(self, request) -> bool:
        return self._in_group(request, *READ_ONLY_GROUPS)

    def _is_full_manage(self, request) -> bool:
        return self._in_group(request, *FULL_MANAGE_GROUPS)

    def _obj_is_mine(self, request, obj) -> bool:
        if obj is None:
            return True
        return hasattr(obj, 'owner') and obj.owner_id == request.user.pk

    # --- Queryset ---

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if self._is_owner_only(request):
            return qs.filter(owner=request.user)
        if self._is_read_only(request) or self._is_full_manage(request):
            return qs
        if request.user.is_staff:
            return qs.filter(owner=request.user)
        return qs.none()

    # --- Add ---

    def has_add_permission(self, request, obj=None) -> bool:
        if request.user.is_superuser:
            return True
        if self._is_read_only(request):
            return False
        if self._is_owner_only(request) or self._is_full_manage(request):
            return True
        return super().has_add_permission(request, obj)

    # --- Change ---

    def has_change_permission(self, request, obj=None) -> bool:
        if request.user.is_superuser:
            return True
        if self._is_read_only(request):
            return False
        if self._is_owner_only(request):
            return self._obj_is_mine(request, obj)
        if self._is_full_manage(request):
            return True
        return super().has_change_permission(request, obj)

    # --- Delete ---

    def has_delete_permission(self, request, obj=None) -> bool:
        if request.user.is_superuser:
            return True
        if self._is_read_only(request):
            return False
        if self._is_owner_only(request):
            if obj is None:
                return False
            return self._obj_is_mine(request, obj)
        if self._is_full_manage(request):
            return False
        return super().has_delete_permission(request, obj)


# ============================================================
# BASE OWNER ADMIN (UNFOLD VERSIYASI)
# ============================================================

class BaseOwnerAdmin(OwnerPermissionMixin, ModelAdmin):  # ✅ unfold.admin.ModelAdmin
    """Owner field bo'lgan ModelAdmin lar uchun"""

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if hasattr(form, 'base_fields') and 'owner' in form.base_fields:
            form.base_fields['owner'].widget = forms.HiddenInput()
            form.base_fields['owner'].required = False
        return form

    def save_model(self, request, obj, form, change):
        """Saqlashda owner ni avtomatik o'rnatish"""
        
        # Modelda haqiqatdan ham 'owner' yoki 'owner_id' maydoni borligini tekshiramiz
        has_owner_field = 'owner' in [f.name for f in obj._meta.get_fields()]

        if has_owner_field:
            if not change:
                # Yangi obyekt yaratilayotganda joriy foydalanuvchini biriktiramiz
                obj.owner = request.user
            else:
                # Tahrirlanayotganda superuser bo'lmaganlar egasini o'zgartira olmaydi
                if not request.user.is_superuser:
                    try:
                        old_obj = self.model.objects.get(pk=obj.pk)
                        obj.owner = old_obj.owner
                    except self.model.DoesNotExist:
                        obj.owner = request.user
                        
        super().save_model(request, obj, form, change)


    def save_formset(self, request, form, formset, change):
        """Inlinelar uchun owner ni avtomatik o'rnatish"""
        instances = formset.save(commit=False)
        for instance in instances:
            if hasattr(instance, 'owner') and not instance.owner_id:
                instance.owner = request.user
            instance.save()
        formset.save_m2m()


# ============================================================
# BASE OWNER INLINE
# ============================================================

class BaseOwnerInline(OwnerPermissionMixin, TabularInline):
    """Owner field bo'lgan TabularInline lar uchun"""
    extra = 1

    def get_formset(self, request, obj=None, **kwargs):
        self._request = request
        formset = super().get_formset(request, obj, **kwargs)
        if hasattr(formset, 'form'):
            if hasattr(formset.form, 'base_fields') and 'owner' in formset.form.base_fields:
                formset.form.base_fields['owner'].widget = forms.HiddenInput()
                formset.form.base_fields['owner'].required = False
        return formset

    def save_new(self, form, commit=True):
        obj = super().save_new(form, commit=False)
        if hasattr(obj, 'owner') and not obj.owner_id:
            obj.owner = self._request.user
        if commit:
            obj.save()
        return obj

    def save_existing(self, form, instance, commit=True):
        if hasattr(instance, 'owner_id') and instance.owner_id:
            form.instance.owner_id = instance.owner_id
        return super().save_existing(form, instance, commit)