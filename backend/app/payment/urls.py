from django.urls import path
from .webhooks import (
    PaymeWebhookView,
    ClickWebhookView,
    UzumWebhookView,
    PaynetWebhookView,
)

urlpatterns = [
    # PayTechUZ Webhooks (Django standard CBV)
    path('payme/', PaymeWebhookView.as_view(), name='payme_webhook'),
    path('click/', ClickWebhookView.as_view(), name='click_webhook'),
    path('uzum/<str:action>/', UzumWebhookView.as_view(), name='uzum_webhook'),
    path('paynet/', PaynetWebhookView.as_view(), name='paynet_webhook'),
]