# baseuser/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import BaseUser, Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_django_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(django_user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()


@receiver(post_save, sender=BaseUser)
def create_student_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(student_user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()