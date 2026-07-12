from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from problems.models import Problem  # Modelni to'g'ridan-to'g'ri import qilamiz

@receiver(post_save, sender=Problem)
def on_problem_save(sender, instance, created, **kwargs):
    pass