from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Video
from .tasks import convert_to_hls

@receiver(post_save, sender=Video)
def trigger_video_processing(sender, instance, created, **kwargs):
    if created and instance.video:
        convert_to_hls.delay(str(instance.id))
