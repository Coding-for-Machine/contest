# baseuser/permissions/assign.py

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

def assign(group, model_list, actions=None):
    content_types = [ContentType.objects.get_for_model(m) for m in model_list]
    perms = Permission.objects.filter(content_type__in=content_types)

    if actions:
        q = Q()
        for action in actions:
            q |= Q(codename__startswith=f"{action}_")
        perms = perms.filter(q)

    # OGohlantirish: agar permissionlar soni 0 bo'lsa
    if perms.count() == 0:
        models_str = ", ".join([m.__name__ for m in model_list])
        logger.warning(
            f"⚠️ {group.name}: {models_str} uchun HECH QANDAY permission topilmadi! "
            f"Migratsiya to'liq o'tganini tekshiring."
        )

    group.permissions.set(perms)
    print(f"✅ {group.name}: {perms.count()} ta huquq")