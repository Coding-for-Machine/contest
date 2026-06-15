from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from baseuser.models import BaseUser

class Order(models.Model):
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    # Polimorfizm (Generic Foreign Key) uchun maydonlar
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE) # Model turini aniqlaydi
    object_id = models.PositiveIntegerField()                               # Model ichidagi ID raqamini saqlaydi
    item = GenericForeignKey('content_type', 'object_id')                  # Dinamik bog'liqlik

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.user.telegram_id} ({self.item})"

class Invoice(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Invoice {self.id} for Order {self.order.id}"