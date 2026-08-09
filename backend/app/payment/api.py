from django_bolt import Router, Depends, Request

from baseuser.authenticate import get_current_user
from baseuser.models import BaseUser
from payment.models import Invoice
from payment.serializers import (
    PaymentCreateRequest,
    PaymentResponse,
    InvoiceListItem,
    InvoiceDetailResponse,
)
from payment.services import PaymentService

api = Router(tags=["Payment api"])


# ============================================================
# TO'LOV YARATISH
# ============================================================
@api.post("/create")
async def create_payment(
    request: Request,
    data: PaymentCreateRequest,
    current_user: BaseUser = Depends(get_current_user),
) -> PaymentResponse:
    # 1. Ob'ektni olish (async ORM)
    item = await PaymentService.get_item(data.item_type, data.item_id)

    # 2. Narx mavjudmi tekshirish
    amount = PaymentService.get_item_price(item)
    if amount <= 0:
        return {"error": "Bu ob'ekt bepul yoki narxi noto'g'ri!"}, 400

    # 3. Allaqachon to'laganmi?
    already_paid = await PaymentService.has_existing_paid_invoice(
        current_user, data.item_type, data.item_id
    )
    if already_paid:
        return {"error": "Siz allaqachon bu ob'ekt uchun to'lov qilgansiz!"}, 409

    # 4. Invoice yaratish
    invoice = await PaymentService.create_invoice(
        user=current_user,
        item=item,
        item_type=data.item_type,
        provider=data.provider,
    )

    # 5. To'lov URL yaratish
    payment_url = PaymentService.generate_payment_url(invoice, data.return_url)

    return PaymentResponse(
        invoice_id=invoice.id,
        amount=float(invoice.amount),
        payment_url=payment_url,
        provider=invoice.provider,
        status=invoice.status,
        item_type=data.item_type,
        item_title=getattr(item, "title", "Noma'lum"),
        created_at=invoice.created_at,
    )


# ============================================================
# INVOICE STATUSINI TEKSHIRISH
# ============================================================
@api.get("/{invoice_id}")
async def get_payment_status(
    request: Request,
    invoice_id: int,
    current_user: BaseUser = Depends(get_current_user),
) -> InvoiceDetailResponse:
    # select_related optimizatsiya
    invoice = await Invoice.objects.select_related(
        "course", "test", "contest", "user"
    ).aget(id=invoice_id)

    # Xavfsizlik: faqat o'z invoicelarini ko'radi
    if invoice.user_id != current_user.id:
        return {"error": "Ruxsat yo'q!"}, 403

    item = invoice.item
    return InvoiceDetailResponse(
        id=invoice.id,
        amount=float(invoice.amount),
        status=invoice.status,
        provider=invoice.provider,
        transaction_id=invoice.transaction_id,
        item_type=invoice.item_type or "unknown",
        item_title=getattr(item, "title", "Noma'lum"),
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


# ============================================================
# TO'LOV TARIXI (Pagination bilan)
# ============================================================
@api.get("/history")
async def payment_history(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    current_user: BaseUser = Depends(get_current_user),
):
    offset = (page - 1) * page_size

    # Optimized queryset
    base_qs = (
        Invoice.objects.filter(user=current_user)
        .select_related("course", "test", "contest")
        .order_by("-created_at")
    )

    # async ORM: count + slice
    total = await base_qs.acount()
    items = []
    async for inv in base_qs[offset : offset + page_size]:
        item = inv.item
        items.append(
            InvoiceListItem(
                id=inv.id,
                amount=float(inv.amount),
                status=inv.status,
                provider=inv.provider,
                item_type=inv.item_type or "unknown",
                item_title=getattr(item, "title", "Noma'lum"),
                created_at=inv.created_at,
            )
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size,
    }


# ============================================================
# TEKSHIRISH ENDPOINTI — Kirish huquqi
# ============================================================
@api.get("/check-access")
async def check_access(
    request: Request,
    item_type: str,
    item_id: int,
    current_user: BaseUser = Depends(get_current_user),
):
    has_access = await PaymentService.has_existing_paid_invoice(
        current_user, item_type, item_id
    )

    return {
        "has_access": has_access,
        "item_type": item_type,
        "item_id": item_id,
    }