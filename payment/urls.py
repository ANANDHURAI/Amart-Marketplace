from django.urls import path; from . import views

urlpatterns = [
    path("payments/razorpay/order/<int:amount>/", views.razorpay_order_creation, name="razorpay_order_creation"),
    path("payments/razorpay/handler/", views.razorpay_paymenthandler, name="razorpay_paymenthandler"),
    path("payments/cash-on-delivery/", views.cash_on_delivery, name="cash_on_delivery"),
    path("payments/pay-now/<int:order_id>/", views.pay_now, name="pay_now"),
    path("payments/success/", views.payment_success, name="payment_success"),
    path("payments/failed/", views.payment_failed, name="payment_failed"),
    path("payments/wallet/retry/", views.wallet_retry_payment, name="wallet_retry_payment"),
]