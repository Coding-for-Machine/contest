from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Video
from .tasks import convert_to_hls, generate_thumbnail


@receiver(post_save, sender=Video)
def process_video_on_upload(sender, instance, created, **kwargs):
    # Agar yangi video bo'lsa, fayli bo'lsa va hali HLS yaratilmagan bo'lsa
    if created and instance.video and not instance.hls_url:
        transaction.on_commit(lambda: convert_to_hls.delay(instance.id))
        transaction.on_commit(lambda: generate_thumbnail.delay(instance.id))
