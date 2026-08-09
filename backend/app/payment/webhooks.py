from paytechuz.integrations.django.views import (
    BasePaymeWebhookView,
    BaseClickWebhookView,
    BaseUzumWebhookView,
    BasePaynetWebhookView,
)

from .services import PaymentService


class PaymeWebhookView(BasePaymeWebhookView):
    async def successfully_payment(self, params, transaction):
        await PaymentService.process_successful_payment_sync(
            invoice_id=transaction.account_id,
            transaction_id=getattr(transaction, 'id', None)
        )

    async def cancelled_payment(self, params, transaction):
        await PaymentService.process_cancelled_payment_sync(
            invoice_id=transaction.account_id
        )


class ClickWebhookView(BaseClickWebhookView):
    async def successfully_payment(self, params, transaction):
        await PaymentService.process_successful_payment_sync(
            invoice_id=transaction.account_id,
            transaction_id=getattr(transaction, 'id', None)
        )

    async def cancelled_payment(self, params, transaction):
        await PaymentService.process_cancelled_payment_sync(
            invoice_id=transaction.account_id
        )


class UzumWebhookView(BaseUzumWebhookView):
    async def successfully_payment(self, params, transaction):
        await PaymentService.process_successful_payment_sync(
            invoice_id=transaction.account_id,
            transaction_id=getattr(transaction, 'id', None)
        )

    async def cancelled_payment(self, params, transaction):
        await PaymentService.process_cancelled_payment_sync(
            invoice_id=transaction.account_id
        )


class PaynetWebhookView(BasePaynetWebhookView):
    async def successfully_payment(self, params, transaction):
        await PaymentService.process_successful_payment_sync(
            invoice_id=transaction.account_id,
            transaction_id=getattr(transaction, 'id', None)
        )

    async def cancelled_payment(self, params, transaction):
        await PaymentService.process_cancelled_payment_sync(
            invoice_id=transaction.account_id
        )