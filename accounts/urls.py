from django.urls import path
from . import views

urlpatterns = [
    # customer account urls
    path("customer-signup/", views.customer_signup, name="customer_signup"),
    path("customer-login/", views.customer_login, name="customer_login"),
    path("customer-logout/", views.customer_logout, name="customer_logout"),
    # Custom admin account urls
    path("admin-login/", views.admin_login, name="admin_login"),
    path("admin-logout/", views.admin_logout, name="admin_logout"),
    # Account activation urls
    path("customer-activation/", views.customer_activation, name="customer_activation"),
    path("customer-resend-otp/", views.resend_otp, name="resend_otp"),
    path("customer-otp-view/", views.otp_view, name="otp_view"),
]
