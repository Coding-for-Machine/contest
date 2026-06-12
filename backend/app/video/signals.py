# movies/signals.py
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Video
from .tasks import convert_to_hls, generate_thumbnail


@receiver(post_save, sender=Video)
def process_video_on_upload(sender, instance, created, **kwargs):
    if instance.video and not instance.hls_url:
        # DB ga yozilgandan KEYIN task yuboriladi
        transaction.on_commit(lambda: convert_to_hls.delay(instance.id))
        transaction.on_commit(lambda: generate_thumbnail.delay(instance.id))