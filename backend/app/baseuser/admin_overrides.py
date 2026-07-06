"""
admin_overrides.py

Ushbu faylni loyihangizdagi istalgan app ichiga qo'ying
va uni apps.py yoki __init__.py orqali import qiling.

Yoki to'g'ridan-to'g'ri admin.py ning boshiga import qiling:
    from .admin_overrides import *
"""
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.decorators import action
from django.contrib.admin.utils import model_ngettext
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _


@action(
    permissions=["delete"],
    description="Tanlangan %(verbose_name_plural)s ni o'chirish",
)
def delete_selected_uz(modeladmin, request, queryset):
    """
    O'zbekcha 'delete_selected' action.
    Bu funktsiyani admin classlaringizga qo'shing.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    (
        deletable_objects,
        model_count,
        perms_needed,
        protected,
    ) = modeladmin.get_deleted_objects(queryset, request)

    if request.POST.get("post") and not protected:
        if perms_needed:
            raise PermissionDenied
        n = len(queryset)
        if n:
            modeladmin.log_deletions(request, queryset)
            modeladmin.delete_queryset(request, queryset)
            modeladmin.message_user(
                request,
                f"{n} ta {model_ngettext(modeladmin.opts, n)} muvaffaqiyatli o'chirildi.",
                messages.SUCCESS,
            )
        return None

    objects_name = model_ngettext(queryset)

    if perms_needed or protected:
        title = f"{objects_name} ni o'chirib bo'lmaydi"
    else:
        title = "Bir nechta ob'ektni o'chirish"

    context = {
        **modeladmin.admin_site.each_context(request),
        "title": title,
        "subtitle": None,
        "objects_name": str(objects_name),
        "deletable_objects": [deletable_objects],
        "model_count": dict(model_count).items(),
        "queryset": queryset,
        "perms_lacking": perms_needed,
        "protected": protected,
        "opts": opts,
        "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        "media": modeladmin.media,
    }

    request.current_app = modeladmin.admin_site.name

    return TemplateResponse(
        request,
        modeladmin.delete_selected_confirmation_template
        or [
            f"admin/{app_label}/{opts.model_name}/delete_selected_confirmation.html",
            f"admin/{app_label}/delete_selected_confirmation.html",
            "admin/delete_selected_confirmation.html",
        ],
        context,
    )


def register_uz_actions():
    """
    Global delete_selected action ni o'zbekcha versiyasi bilan almashtirish.
    Bu funktsiyani settings.py yoki apps.py da chaqiring.

    Misol (apps.py):
        class MyAppConfig(AppConfig):
            def ready(self):
                from .admin_overrides import register_uz_actions
                register_uz_actions()
    """
    # Eski global actionni o'chirish
    admin.site.disable_action("delete_selected")
    # O'zbekcha versiyani qo'shish
    admin.site.add_action(delete_selected_uz, "delete_selected")
