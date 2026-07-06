from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from problems.models import Problem  # Modelni to'g'ridan-to'g'ri import qilamiz

@receiver(post_save, sender=Problem)
def on_problem_save(sender, instance, created, **kwargs):
    if created:
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern("problems_list_*")
        else:
            cache.clear()

        # 2. Umumiy sanoq keshini ham o'chiramiz
        cache.delete("problems_total_count")