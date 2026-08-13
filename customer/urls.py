from django.urls import path
from . import views

urlpatterns = [
    
    path("", views.dashboard, name="customer-dashboard"),
    path("orders/", views.orders, name="customer-orders"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel-order"),
    path("orders/items/<int:order_item_id>/cancel/", views.cancel_order_item, name="cancel-order-item"),
    path("orders/<int:order_id>/invoice/", views.invoice, name="invoice"),
    path("orders/<int:order_id>/confirmation/", views.order_confirmation, name="order-confirmation"),
    path("request-return/<int:order_item_id>/", views.request_return, name="request-return"),

    
    path("addresses/", views.address, name="customer-addresses"),
    path("addresses/new/", views.new_address, name="new-address"),
    path("addresses/<int:address_id>/edit/", views.edit_address, name="edit-address"),
    path("addresses/<int:address_id>/delete/", views.remove_address, name="delete-address"),
    path("addresses/<int:address_id>/default/", views.default_address, name="default-address"),
    
    
    path("profile/", views.profile, name="customer-profile"),
    path("profile/edit/", views.edit_profile, name="edit-profile"),
    path("profile/change-password/", views.change_password, name="change-password"),
    
    
    path("wallet/", views.customer_wallet, name="customer-wallet"),
    
]