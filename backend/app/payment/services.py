from decimal import Decimal
from django.conf import settings
from asgiref.sync import sync_to_async
from django.db import transaction

from courses.models import Course, Enrollment
from quizs.models import Test, TestEnrollment
from contests.models import Contest, ContestRegistration
from baseuser.models import BaseUser

from paytechuz.gateways.payme import PaymeGateway
from paytechuz.gateways.click import ClickGateway
from paytechuz.gateways.uzum import UzumGateway
from paytechuz.gateways.paynet import PaynetGateway

from payment.models import Invoice


class PaymentService:
    """To'lov biznes logikasi."""

    @staticmethod
    async def get_item(item_type: str, item_id: int):
        """Async ORM bilan ob'ektni olish (N+1 oldini olish uchun)."""
        if item_type == "course":
            return await Course.objects.aget(id=item_id)
        elif item_type == "test":
            return await Test.objects.aget(id=item_id)
        elif item_type == "contest":
            return await Contest.objects.aget(id=item_id)
        raise ValueError(f"Noto'g'ri item_type: {item_type}")

    @staticmethod
    def get_item_price(item) -> Decimal:
        """Chegirmali narxni hisobga olgan holda narxni qaytaradi."""
        price = getattr(item, 'price', Decimal("0"))
        discount = getattr(item, 'discount_price', None)
        if discount is not None and discount > 0 and discount < price:
            return discount
        return price

    @staticmethod
    async def has_existing_paid_invoice(user: BaseUser, item_type: str, item_id: int) -> bool:
        """Foydalanuvchi allaqachon to'laganmi?"""
        filters = {"user": user, "status": Invoice.Status.PAID, f"{item_type}__id": item_id}
        return await Invoice.objects.filter(**filters).aexists()

    @staticmethod
    async def create_invoice(user: BaseUser, item, item_type: str, provider: str) -> Invoice:
        """Invoice yaratish (agar pending invoice bo'lsa, yangisini yaratmaydi)."""
        # Avval pending invoice bormi tekshiramiz
        existing = await Invoice.objects.filter(
            user=user,
            status=Invoice.Status.PENDING,
            **{item_type: item}
        ).afirst()

        if existing:
            return existing

        amount = PaymentService.get_item_price(item)

        invoice = await Invoice.objects.acreate(
            user=user,
            amount=amount,
            status=Invoice.Status.PENDING,
            provider=provider,
            **{item_type: item}
        )
        return invoice

    @staticmethod
    def generate_payment_url(invoice: Invoice, return_url: str) -> str:
        """PayTechUZ gateway orqali to'lov URL yaratish."""
        provider = invoice.provider

        if provider == Invoice.Provider.PAYME:
            gateway = PaymeGateway(
                payme_id=settings.PAYTECHUZ['PAYME']['PAYME_ID'],
                payme_key=settings.PAYTECHUZ['PAYME']['PAYME_KEY'],
                is_test_mode=settings.PAYTECHUZ['PAYME']['IS_TEST_MODE']
            )
            return gateway.create_payment(
                id=invoice.id,
                amount=invoice.amount,
                return_url=return_url,
                account_field_name=settings.PAYTECHUZ['PAYME']['ACCOUNT_FIELD']
            )

        elif provider == Invoice.Provider.CLICK:
            gateway = ClickGateway(
                service_id=settings.PAYTECHUZ['CLICK']['SERVICE_ID'],
                merchant_id=settings.PAYTECHUZ['CLICK']['MERCHANT_ID'],
                merchant_user_id=settings.PAYTECHUZ['CLICK']['MERCHANT_USER_ID'],
                secret_key=settings.PAYTECHUZ['CLICK']['SECRET_KEY'],
                is_test_mode=settings.PAYTECHUZ['CLICK']['IS_TEST_MODE']
            )
            return gateway.create_payment(
                id=invoice.id,
                amount=invoice.amount,
                return_url=return_url
            )

        elif provider == Invoice.Provider.UZUM:
            gateway = UzumGateway(
                service_id=settings.PAYTECHUZ['UZUM']['SERVICE_ID'],
                is_test_mode=settings.PAYTECHUZ['UZUM']['IS_TEST_MODE']
            )
            return gateway.create_payment(
                id=invoice.id,
                amount=invoice.amount,
                return_url=return_url
            )

        elif provider == Invoice.Provider.PAYNET:
            gateway = PaynetGateway(
                merchant_id=settings.PAYTECHUZ['PAYNET']['SERVICE_ID'],
                is_test_mode=settings.PAYTECHUZ['PAYNET']['IS_TEST_MODE']
            )
            return gateway.create_payment(
                id=invoice.id,
                amount=invoice.amount
            )

        raise ValueError(f"Noma'lum provider: {provider}")

    @staticmethod
    @sync_to_async
    def process_successful_payment_sync(invoice_id: int, transaction_id: str):
        """Webhook'dan chaqiriladi — sync context'da ishlaydi."""
        with transaction.atomic():
            invoice = Invoice.objects.select_related(
                'user', 'course', 'test', 'contest'
            ).select_for_update().get(id=invoice_id)

            if invoice.status == Invoice.Status.PAID:
                return  # Allaqachon to'langan

            invoice.status = Invoice.Status.PAID
            invoice.transaction_id = transaction_id
            invoice.save()

            # Course uchun Enrollment yaratish/yangilash
            if invoice.course:
                Enrollment.objects.update_or_create(
                    user=invoice.user,
                    course=invoice.course,
                    defaults={'is_paid': True}
                )

            # Test uchun TestEnrollment yaratish
            elif invoice.test:
                TestEnrollment.objects.update_or_create(
                    user=invoice.user,
                    test=invoice.test,
                    defaults={
                        'amount': invoice.amount,
                        'transaction_id': transaction_id
                    }
                )

            # Contest uchun ContestRegistration yaratish
            elif invoice.contest:
                ContestRegistration.objects.update_or_create(
                    user=invoice.user,
                    contest=invoice.contest,
                    defaults={'status': ContestRegistration.Status.IN_PROGRESS}
                )

    @staticmethod
    @sync_to_async
    def process_cancelled_payment_sync(invoice_id: int):
        """To'lov bekor qilinganda."""
        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
            if invoice.status != Invoice.Status.PAID:
                invoice.status = Invoice.Status.CANCELLED
                invoice.save()