# centers/models.py
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Center(models.Model):
    name = models.CharField(max_length=255, verbose_name="Markaz nomi")
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    address = models.TextField(blank=True, verbose_name="Manzil")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Faol")
    
    # Markaz direktori (faqat bitta direktor)
    director = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='directed_centers',
        verbose_name="Markaz direktori"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def get_staff_count(self):
        return self.staff_profiles.count()
    
    def get_students_count(self): 
        return self.students.count()
    
    class Meta:
        verbose_name = "🏢 O'quv Markaz"
        verbose_name_plural = "🏢 O'quv Markazlar"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class CenterScopedMixin(models.Model):
    """
    Barcha markazga tegishli modellar uchun mixin.
    Course, Test, Contest, Problem va hk.
    """
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        related_name='%(class)ss',  # courses, tests, contests...
        verbose_name="Markaz"
    )
    
    class Meta:
        abstract = True