import msgspec
from decimal import Decimal
from datetime import datetime
from typing import Optional, Literal


class PaymentCreateRequest(msgspec.Struct):
    item_type: Literal["course", "test", "contest"]
    item_id: int
    provider: Literal["payme", "click", "uzum", "paynet"]
    return_url: Optional[str] = "https://sizning-saytingiz.uz/payments/success/"


class PaymentItemInfo(msgspec.Struct):
    id: int
    title: str
    price: float
    discount_price: Optional[float] = None


class PaymentResponse(msgspec.Struct):
    invoice_id: int
    amount: float
    payment_url: str
    provider: str
    status: str
    item_type: str
    item_title: str
    created_at: datetime


class InvoiceListItem(msgspec.Struct):
    id: int
    amount: float
    status: str
    provider: str
    item_type: str
    item_title: str
    created_at: datetime


class InvoiceDetailResponse(msgspec.Struct):
    id: int
    amount: float
    status: str
    provider: str
    transaction_id: Optional[str]
    item_type: str
    item_title: str
    created_at: datetime
    updated_at: datetime