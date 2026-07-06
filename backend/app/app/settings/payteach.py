

def payteach():
    PAYTECHUZ = {
        'PAYME': {
            'PAYME_ID': 'your_payme_id',
            'PAYME_KEY': 'your_payme_key',
            'ACCOUNT_MODEL': 'payment.models.Invoice',  #  Your invoice model
            'ACCOUNT_FIELD': 'id',
            'AMOUNT_FIELD': 'amount',
            'ONE_TIME_PAYMENT': True,
            'IS_TEST_MODE': True,  # Set to False in production
        },
        'CLICK': {
            'SERVICE_ID': 'your_service_id',
            'MERCHANT_ID': 'your_merchant_id',
            'MERCHANT_USER_ID': 'your_merchant_user_id',
            'SECRET_KEY': 'your_secret_key',
            'ACCOUNT_MODEL': 'payment.models.Invoice',
            'ACCOUNT_FIELD': 'id',
            'COMMISSION_PERCENT': 0.0,
            'ONE_TIME_PAYMENT': True,
            'IS_TEST_MODE': True,  # Set to False in production
        },
        'UZUM': {
            'SERVICE_ID': 'your_service_id',  # Uzum Service ID for Biller URL
            'USERNAME': 'your_uzum_username',  # For webhook Basic Auth
            'PASSWORD': 'your_uzum_password',  # For webhook Basic Auth
            'ACCOUNT_MODEL': 'payment.models.Invoice',
            'ACCOUNT_FIELD': 'id',  # or 'id'
            'AMOUNT_FIELD': 'amount',
            'ONE_TIME_PAYMENT': True, # Set to False if you want to allow multiple payments for the same invoice
            'IS_TEST_MODE': True,  # Set to False in production
        },
        'PAYNET': {
            'MERCHANT_ID': 'your_merchant_id', # Paynet Merchant ID
            'SERVICE_ID': 'your_paynet_service_id',
            'USERNAME': 'your_paynet_username',
            'PASSWORD': 'your_paynet_password',
            'ACCOUNT_MODEL': 'payment.models.Invoice',
            'ACCOUNT_FIELD': 'id',
            'AMOUNT_FIELD': 'amount',
            'ONE_TIME_PAYMENT': True,
            'IS_TEST_MODE': True,
        }
    }
    return PAYTECHUZ