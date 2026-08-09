from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

from baseuser.models import BaseUser
from courses.models import Course
from quizs.models import Test
from contests.models import Contest


class Invoice(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        PAID = "paid", "To'langan"
        CANCELLED = "cancelled", "Bekor qilingan"
        REFUNDED = "refunded", "Qaytarilgan"

    class Provider(models.TextChoices):
        PAYME = "payme", "Payme"
        CLICK = "click", "Click"
        UZUM = "uzum", "Uzum"
        PAYNET = "paynet", "Paynet"

    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        related_name="invoices",
        verbose_name="Foydalanuvchi",
    )
    amount = models.DecimalField(
        "Summa (UZS)",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(
        "Holati",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    provider = models.CharField(
        "To'lov tizimi",
        max_length=20,
        choices=Provider.choices,
        db_index=True,
    )
    transaction_id = models.CharField(
        "Provider transaction ID",
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
    )

    # Nima uchun to'lov qilinmoqda (faqat bittasi to'ldiriladi)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        null=True, blank=True, related_name="invoices"
    )
    test = models.ForeignKey(
        Test, on_delete=models.CASCADE,
        null=True, blank=True, related_name="invoices"
    )
    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE,
        null=True, blank=True, related_name="invoices"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "🧾 Invoice"
        verbose_name_plural = "🧾 Invoicelar"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["transaction_id"]),
        ]

    def __str__(self):
        item = self.course or self.test or self.contest
        return f"#{self.id} | {self.user} | {item} | {self.amount} UZS"

    @property
    def item(self):
        return self.course or self.test or self.contest

    @property
    def item_type(self):
        if self.course: return "course"
        if self.test: return "test"
        if self.contest: return "contest"
        return None

    def clean(self):
        items = [self.course, self.test, self.contest]
        if sum(x is not None for x in items) != 1:
            raise ValidationError("Invoice faqat bitta ob'ektga (Course/Test/Contest) ulanishi kerak!")