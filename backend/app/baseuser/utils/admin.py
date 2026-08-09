"""
baseuser/utils/admin.py
PERMISSION-BASED ACCESS CONTROL (PBAC) + Center/Owner Scope

Arxitektura:
    Permission (has_perm)  →  Admin Kirish  →  Center Filter  →  Owner Filter

Tamoyillar:
    1. Guruhlar faqat rol va permission konteyneri.
    2. Admin hech qachon guruh nomini tekshirmaydi.
    3. Kirish huquqi faqat request.user.has_perm() orqali aniqlanadi.
    4. Center va Owner filtrlari alohida qatlam hisoblanadi.
    5. Har bir rad etish (403) sababi konsolga aniq va o'qilishi oson
       formatda log qilinadi (logger: "baseuser.permissions").
"""

import logging

from django import forms
from django.contrib import admin
from django.core.exceptions import FieldError, ObjectDoesNotExist
from unfold.admin import ModelAdmin, TabularInline

logger = logging.getLogger("baseuser.permissions")


# ============================================================
# CENTER PATHS — Modellardan markazni topish yo'llari
# ============================================================

CENTER_PATHS = (
    "center",
    "course.center",
    "problem.center",
    "contest.center",
    "test.center",
    "modul.course.center",
    "lesson.modul.course.center",
    "question.test.center",
    "question.lesson.modul.course.center",
    "registration.contest.center",
    "contest_problem.contest.center",
    "user.center",
    "owner.profile.center",
)


def _resolve_center(obj, path):
    """Masalan: 'course.center' → obj.course.center"""
    if obj is None:
        return None
    parts = path.split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        try:
            current = getattr(current, part)
        except (AttributeError, ObjectDoesNotExist):
            return None
    return current


# ============================================================
# PERMISSION + SCOPE MIXIN
# ============================================================

class PermissionScopeMixin:
    """
    PBAC mixin. Permissionlar Django has_perm orqali, scope esa
    foydalanuvchi ma'lumotlari (center, directed_centers) orqali.
    """

    # --- Permission yordamchilari ---

    def _get_perm(self, action, model=None):
        """Masalan: 'courses.view_course'"""
        target = model or self.model
        opts = target._meta
        return f"{opts.app_label}.{action}_{opts.model_name}"

    def _has_perm(self, request, action, model=None):
        """Superuser yoki haqiqiy permission egasi"""
        if request.user.is_superuser:
            return True
        return request.user.has_perm(self._get_perm(action, model))

    def _get_record_scope(self, request, model=None):
        """
        Foydalanuvchining ushbu modeldagi huquq darajasi:
            'full'     → delete bor = markazdagi hamma narsa
            'owner'    → change/add bor, delete yo'q = faqat o'zini
            'readonly' → faqat view bor
            'none'     → hech narsa yo'q
        """
        if request.user.is_superuser:
            return 'full'

        has_delete = self._has_perm(request, 'delete', model)
        has_change = self._has_perm(request, 'change', model)
        has_add = self._has_perm(request, 'add', model)
        has_view = self._has_perm(request, 'view', model)

        if has_delete:
            return 'full'
        if has_change or has_add:
            return 'owner'
        if has_view:
            return 'readonly'
        return 'none'

    # --- Center scope yordamchilari ---

    def _get_center_scope(self, request):
        """
        Returns: (center, is_cross_center)
        center = None bo'lsa, filter qo'llanmaydi.
        is_cross_center = True → Direktor, barcha markazlar.
        """
        if request.user.is_superuser:
            return (None, True)

        # 1. Direktor tekshiruvi: 1 dan ko'p markaz boshqaradi
        if hasattr(request.user, 'directed_centers'):
            count = request.user.directed_centers.count()
            if count > 1:
                return (None, True)   # Direktor - barcha markazlar
            if count == 1:
                # Markaz Boshlig'i - faqat o'sha markaz
                return (request.user.directed_centers.first(), False)

        # 2. Oddiy xodim - profile.center orqali
        try:
            profile = request.user.profile
        except ObjectDoesNotExist:
            return (None, False)

        center = getattr(profile, "center", None)
        return (center, False) if center else (None, False)

    def _get_obj_center(self, obj):
        """CENTER_PATHS orqali obyektning markazini topadi."""
        if obj is None:
            return None
        for path in CENTER_PATHS:
            center = _resolve_center(obj, path)
            if center is not None:
                return center
        return None

    def _get_center_filter_path(self):
        """Model maydonlari orqali center filter yo'lini aniqlaydi."""
        field_names = {f.name for f in self.model._meta.get_fields()}

        if "center" in field_names:
            return "center"

        paths = [
            "course__center",
            "problem__center",
            "test__center",
            "contest__center",
            "modul__course__center",
            "lesson__modul__course__center",
            "question__test__center",
            "question__lesson__modul__course__center",
            "user__center",
            "owner__profile__center",
            "registration__contest__center",
            "contest_problem__contest__center",
        ]

        for path in paths:
            first = path.split("__")[0]
            if first in field_names:
                return path

        return None

    def _filter_by_center(self, qs, center):
        """QuerySet'ni markaz bo'yicha filterlaydi."""
        path = self._get_center_filter_path()
        if path:
            return qs.filter(**{path: center})
        # Modelda center yo'li topilmasa = center maydoni yo'q,
        # shuning uchun filter qo'llanmaydi (qs o'zgarishsiz qaytariladi)
        return qs

    def _check_scope(self, request, obj=None):
        """Obyekt darajasida center mosligini tekshiradi."""
        if request.user.is_superuser:
            return True

        center, is_cross = self._get_center_scope(request)
        if is_cross:
            return True
        if center is None:
            return False
        if obj is not None:
            obj_center = self._get_obj_center(obj)
            if obj_center is not None and obj_center != center:
                return False
        return True

    # ============================================================
    # LOG YORDAMCHISI
    # ============================================================

    def _deny(self, request, action, reason, obj=None):
        """
        403 sababini konsolga aniq, bir qatorli formatda yozadi.
        `reason`: "PERM" (huquq yo'q) yoki "SCOPE" (markaz mos kelmadi/aniqlanmadi)
        """
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        user = request.user

        if reason == "PERM":
            logger.warning(
                "403 %s rad etildi | model=%s.%s | user=%s (id=%s) | "
                "kerakli ruxsat=%s | user guruhlari=%s",
                action, app_label, model_name,
                getattr(user, "username", user), user.id,
                self._get_perm(action.lower()),
                list(user.groups.values_list("name", flat=True)),
            )
        else:  # SCOPE
            center, is_cross = self._get_center_scope(request)
            obj_center = self._get_obj_center(obj) if obj is not None else None
            logger.warning(
                "403 %s rad etildi (SCOPE) | model=%s.%s | user=%s (id=%s) | "
                "user_center=%s | is_cross=%s | obj_id=%s | obj_center=%s | "
                "sabab: profile.center yo'q yoki obj markazi user markaziga mos kelmadi",
                action, app_label, model_name,
                getattr(user, "username", user), user.id,
                center, is_cross,
                getattr(obj, "id", None), obj_center,
            )

    # ============================================================
    # DJANGO ADMIN PERMISSION METHODS
    # ============================================================

    def has_module_permission(self, request):
        """Admin index'da ko'rinish uchun modelning istalgan permissioni yetarli."""
        if request.user.is_superuser:
            return True
        for action in ('view', 'add', 'change', 'delete'):
            if request.user.has_perm(self._get_perm(action)):
                return True
        return False

    def has_view_permission(self, request, obj=None):
        # view YOKI change permissioni bo'lsa ko'radi (Django standarti)
        if not self._has_perm(request, 'view') and not self._has_perm(request, 'change'):
            self._deny(request, "VIEW", "PERM")
            return False
        if not self._check_scope(request, obj):
            self._deny(request, "VIEW", "SCOPE", obj)
            return False
        return True

    def has_add_permission(self, request):
        if not self._has_perm(request, 'add'):
            self._deny(request, "ADD", "PERM")
            return False
        if not self._check_scope(request, None):
            self._deny(request, "ADD", "SCOPE")
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if not self._has_perm(request, 'change'):
            self._deny(request, "CHANGE", "PERM")
            return False
        if not self._check_scope(request, obj):
            self._deny(request, "CHANGE", "SCOPE", obj)
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if not self._has_perm(request, 'delete'):
            self._deny(request, "DELETE", "PERM")
            return False
        if not self._check_scope(request, obj):
            self._deny(request, "DELETE", "SCOPE", obj)
            return False
        return True

    # ============================================================
    # QUERYSET
    # ============================================================

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        scope = self._get_record_scope(request)
        if scope == 'none':
            return qs.none()

        center, is_cross = self._get_center_scope(request)
        if is_cross:
            # Direktor: faqat owner filter (agar kerak bo'lsa)
            if scope == 'owner':
                if 'owner' in {f.name for f in self.model._meta.get_fields()}:
                    return qs.filter(owner=request.user)
            return qs

        if center is None:
            return qs.none()

        # Markaz filteri
        qs = self._filter_by_center(qs, center)

        # Owner filteri (faqat o'z ma'lumotlari)
        if scope == 'owner':
            if 'owner' in {f.name for f in self.model._meta.get_fields()}:
                return qs.filter(owner=request.user)

        return qs


# ============================================================
# BASE OWNER ADMIN
# ============================================================

class BaseOwnerAdmin(PermissionScopeMixin, ModelAdmin):
    """
    Center va Owner maydoni bo'lgan modellar uchun.
    Permission → Center → Owner tartibida ishlaydi.
    """

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not hasattr(form, 'base_fields'):
            return form

        if 'owner' in form.base_fields:
            if request.user.is_superuser:
                # Superuser uchun owner ko'rinadigan va tahrirlanadigan bo'ladi
                form.base_fields['owner'].required = False
            else:
                form.base_fields['owner'].widget = forms.HiddenInput()
                form.base_fields['owner'].required = False

        if 'center' in form.base_fields:
            # Agar foydalanuvchining aniq markazi bo'lsa (cross-center emas),
            # center maydoni yashirin va avtomatik to'ldiriladi.
            center, is_cross = self._get_center_scope(request)
            if center and not is_cross:
                form.base_fields['center'].widget = forms.HiddenInput()
                form.base_fields['center'].required = False

        return form

    def save_model(self, request, obj, form, change):
        field_names = {f.name for f in obj._meta.get_fields()}
        has_owner = "owner" in field_names
        has_center = "center" in field_names

        # Owner avtomatik to'ldirish
        if has_owner:
            if not change:
                if request.user.is_superuser:
                    # Superuser formada tanlagan owner saqlanadi;
                    # tanlamagan bo'lsa (bo'sh qoldirsa) o'ziga yoziladi
                    if not obj.owner_id:
                        obj.owner = request.user
                else:
                    obj.owner = request.user
            elif not request.user.is_superuser:
                # O'zgartirishda eski owner saqlanadi (agar superuser bo'lmasa)
                try:
                    old = self.model.objects.get(pk=obj.pk)
                    obj.owner = old.owner
                except self.model.DoesNotExist:
                    obj.owner = request.user

        # Center avtomatik to'ldirish
        if has_center:
            user_center, is_cross = self._get_center_scope(request)
            if not change:
                if user_center and not is_cross:
                    obj.center = user_center
                # Aks holda (cross-center yoki markazi yo'q) forma orqali tanlanadi
            elif not request.user.is_superuser and not is_cross:
                # Oddiy xodim markazni o'zgartira olmaydi
                try:
                    old = self.model.objects.get(pk=obj.pk)
                    obj.center = old.center
                except self.model.DoesNotExist:
                    pass

        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for obj in formset.deleted_objects:
            obj.delete()

        for instance in instances:
            if hasattr(instance, 'owner') and not instance.owner_id:
                instance.owner = request.user
            if hasattr(instance, 'center') and not instance.center_id:
                center, is_cross = self._get_center_scope(request)
                if center and not is_cross:
                    instance.center = center
            instance.save()

        formset.save_m2m()


# ============================================================
# BASE OWNER INLINE
# ============================================================

class BaseOwnerInline(PermissionScopeMixin, TabularInline):
    """Inline modellar uchun PBAC + Center/Owner"""
    extra = 1

    def _get_inline_perm(self, action):
        """Inline o'zining model permissionini tekshiradi."""
        opts = self.model._meta
        return f"{opts.app_label}.{action}_{opts.model_name}"

    def _has_inline_perm(self, request, action):
        if request.user.is_superuser:
            return True
        return request.user.has_perm(self._get_inline_perm(action))

    def _get_inline_scope(self, request):
        """Inline model uchun scope."""
        has_delete = self._has_inline_perm(request, 'delete')
        has_change = self._has_inline_perm(request, 'change')
        has_add = self._has_inline_perm(request, 'add')
        has_view = self._has_inline_perm(request, 'view')

        if has_delete:
            return 'full'
        if has_change or has_add:
            return 'owner'
        if has_view:
            return 'readonly'
        return 'none'

    def get_formset(self, request, obj=None, **kwargs):
        self._request = request
        formset = super().get_formset(request, obj, **kwargs)
        if hasattr(formset, 'form') and hasattr(formset.form, 'base_fields'):
            if 'owner' in formset.form.base_fields:
                formset.form.base_fields['owner'].widget = forms.HiddenInput()
                formset.form.base_fields['owner'].required = False
            if 'center' in formset.form.base_fields:
                formset.form.base_fields['center'].widget = forms.HiddenInput()
                formset.form.base_fields['center'].required = False
        return formset

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        scope = self._get_inline_scope(request)
        if scope == 'none':
            return qs.none()

        center, is_cross = self._get_center_scope(request)
        if is_cross:
            if scope == 'owner':
                if 'owner' in {f.name for f in self.model._meta.get_fields()}:
                    return qs.filter(owner=request.user)
            return qs

        if center is None:
            return qs.none()

        # Inline uchun parent orqali center filter
        if self.model and hasattr(self.model, 'center'):
            qs = qs.filter(center=center)
        elif self.parent_model and hasattr(self.parent_model, 'center'):
            qs = qs.filter(**{f"{self.parent_model._meta.model_name}__center": center})

        if scope == 'owner':
            if 'owner' in {f.name for f in self.model._meta.get_fields()}:
                qs = qs.filter(owner=request.user)

        return qs

    # Inline permissionlari inline modelning o'z permissioniga asoslanadi
    def has_add_permission(self, request, obj=None):
        # obj = parent instance (masalan: Problem)
        if request.user.is_superuser:
            return True
        if not self._has_inline_perm(request, 'add'):
            logger.warning(
                "403 INLINE ADD rad etildi | inline_model=%s | user=%s (id=%s) | "
                "kerakli ruxsat=%s",
                self.model._meta.model_name,
                getattr(request.user, "username", request.user), request.user.id,
                self._get_inline_perm('add'),
            )
            return False
        if not self._check_scope(request, obj):
            logger.warning(
                "403 INLINE ADD rad etildi (SCOPE) | inline_model=%s | parent_id=%s | "
                "user=%s (id=%s)",
                self.model._meta.model_name, getattr(obj, "id", None),
                getattr(request.user, "username", request.user), request.user.id,
            )
            return False
        return True

    def has_change_permission(self, request, obj=None):
        # obj = inline instance (masalan: Hint)
        if request.user.is_superuser:
            return True
        if not self._has_inline_perm(request, 'change'):
            logger.warning(
                "403 INLINE CHANGE rad etildi | inline_model=%s | user=%s (id=%s) | "
                "kerakli ruxsat=%s",
                self.model._meta.model_name,
                getattr(request.user, "username", request.user), request.user.id,
                self._get_inline_perm('change'),
            )
            return False
        if not self._check_scope(request, obj):
            logger.warning(
                "403 INLINE CHANGE rad etildi (SCOPE) | inline_model=%s | obj_id=%s | "
                "user=%s (id=%s)",
                self.model._meta.model_name, getattr(obj, "id", None),
                getattr(request.user, "username", request.user), request.user.id,
            )
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not self._has_inline_perm(request, 'delete'):
            logger.warning(
                "403 INLINE DELETE rad etildi | inline_model=%s | user=%s (id=%s) | "
                "kerakli ruxsat=%s",
                self.model._meta.model_name,
                getattr(request.user, "username", request.user), request.user.id,
                self._get_inline_perm('delete'),
            )
            return False
        if not self._check_scope(request, obj):
            logger.warning(
                "403 INLINE DELETE rad etildi (SCOPE) | inline_model=%s | obj_id=%s | "
                "user=%s (id=%s)",
                self.model._meta.model_name, getattr(obj, "id", None),
                getattr(request.user, "username", request.user), request.user.id,
            )
            return False
        return True

    def save_new(self, form, commit=True):
        obj = super().save_new(form, commit=False)
        if hasattr(obj, 'owner') and not obj.owner_id:
            obj.owner = self._request.user
        if hasattr(obj, 'center') and not obj.center_id:
            center, is_cross = self._get_center_scope(self._request)
            if center and not is_cross:
                obj.center = center
        if commit:
            obj.save()
        return obj

    def save_existing(self, form, instance, commit=True):
        if hasattr(instance, 'owner_id') and instance.owner_id:
            form.instance.owner_id = instance.owner_id
        if hasattr(instance, 'center_id') and instance.center_id:
            form.instance.center_id = instance.center_id
        return super().save_existing(form, instance, commit)


# ============================================================
# SIMPLE OWNER ADMIN (center maydoni YO'Q modellar uchun)
# ============================================================

class SimpleOwnerAdmin(PermissionScopeMixin, ModelAdmin):
    """
    Faqat 'owner' maydoni bor, 'center' maydoni YO'Q modellar.
    Masalan: Category, Tags
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        scope = self._get_record_scope(request)
        if scope == 'none':
            return qs.none()
        if scope == 'owner' and 'owner' in {f.name for f in self.model._meta.get_fields()}:
            return qs.filter(owner=request.user)
        return qs

    def has_add_permission(self, request):
        allowed = self._has_perm(request, 'add')
        if not allowed:
            self._deny(request, "ADD", "PERM")
        return allowed

    def has_change_permission(self, request, obj=None):
        if not self._has_perm(request, 'change'):
            self._deny(request, "CHANGE", "PERM")
            return False
        if request.user.is_superuser:
            return True
        # Owner-only: faqat o'zini tahrirlaydi
        if self._get_record_scope(request) == 'owner' and obj is not None:
            allowed = hasattr(obj, 'owner') and obj.owner == request.user
            if not allowed:
                logger.warning(
                    "403 CHANGE rad etildi (OWNER) | model=%s.%s | obj_id=%s | "
                    "obj_owner=%s | user=%s (id=%s)",
                    self.model._meta.app_label, self.model._meta.model_name,
                    getattr(obj, "id", None), getattr(obj, "owner_id", None),
                    getattr(request.user, "username", request.user), request.user.id,
                )
            return allowed
        return True

    def has_delete_permission(self, request, obj=None):
        if not self._has_perm(request, 'delete'):
            self._deny(request, "DELETE", "PERM")
            return False
        if request.user.is_superuser:
            return True
        # Owner-only: o'chira olmaydi (chunki delete perm yo'q owner-only'da)
        return True

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if hasattr(form, 'base_fields') and 'owner' in form.base_fields:
            if request.user.is_superuser:
                form.base_fields['owner'].required = False
            else:
                form.base_fields['owner'].widget = forms.HiddenInput()
                form.base_fields['owner'].required = False
        return form

    def save_model(self, request, obj, form, change):
        if not change:
            if request.user.is_superuser:
                if not obj.owner_id:
                    obj.owner = request.user
            else:
                obj.owner = request.user
        else:
            if not request.user.is_superuser:
                try:
                    old = self.model.objects.get(pk=obj.pk)
                    obj.owner = old.owner
                except self.model.DoesNotExist:
                    obj.owner = request.user
        super().save_model(request, obj, form, change)


# ============================================================
# STUDENT DATA ADMIN
# ============================================================

class BaseStudentDataAdmin(PermissionScopeMixin, ModelAdmin):
    """BaseUser (talaba) ma'lumotlari uchun."""

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def _get_center_filter_path(self):
        if hasattr(self.model, 'user'):
            return 'user__center'
        if hasattr(self.model, 'registration'):
            return 'registration__contest__center'
        return super()._get_center_filter_path()