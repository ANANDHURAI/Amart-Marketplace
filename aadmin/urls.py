from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name="admin_dashboard"),

    # Customers
    path('customers/', views.customer_list, name="customer_list"),
    path('customers/<int:pk>/approval/', views.customer_approval, name="customer_approval"),

    # Profile
    path("profile/", views.admin_profile, name="admin_profile"),
    path("profile/edit/", views.edit_admin_profile, name="edit_admin_profile"),

    # Categories
    path('categories/', views.category_list, name="category_list"),
    path('categories/add/', views.add_category, name="add_category"),
    path('categories/<slug:slug>/edit/', views.edit_category, name="edit_category"),
    path('categories/<slug:slug>/delete/', views.delete_category, name="delete_category"),
    path('categories/<slug:slug>/restore/', views.restore_category, name="restore_category"),

    # Products
    path('products/', views.product_list, name="product_list"),
    path("products/add/", views.product_form, name="add_product"),
    path("products/<int:product_id>/edit/", views.product_form, name="edit_product"),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('products/<int:pk>/approval/', views.product_approval, name="product_approval"),
    path("products/<int:product_id>/", views.restore_product, name="restore_product"),

    # Product Images
    path('products/images/<int:image_id>/delete/', views.remove_product_image, name='remove_product_image'),

    # Orders
    path('orders/', views.order_list, name="order_list"),
    path('orders/<int:order_id>/details/', views.admin_order_detail, name="admin_order_detail"),
    path('orders/items/<int:order_item_id>/status/', views.update_order_status, name='update_order_status'),

    # Reports
    path('reports/sales/', views.sales_report, name="sales_report"),

    # Coupons
    path('coupons/', views.coupon_list, name="coupon_list"),
    path('coupons/add/', views.add_coupon, name="add_coupon"),
    path('coupons/<int:id>/edit/', views.edit_coupon, name="edit_coupon"),
    path('coupons/<int:id>/delete/', views.delete_coupon, name="delete_coupon"),

    # Offers
    path('offers/', views.offer_list, name="offer_list"),
    path('offers/add/', views.add_offer, name="add_offer"),
    path('offers/<int:id>/edit/', views.edit_offer, name="edit_offer"),
    path('offers/<int:id>/delete/', views.delete_offer, name="delete_offer"),

    # Inventory
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/add/', views.add_edit_inventory, name='add_inventory'),
    path('inventory/<int:inventory_id>/edit/', views.add_edit_inventory, name='edit_inventory'),
    path('inventory/<int:inventory_id>/status/', views.inventory_status, name='inventory_status'),
    path('inventory/<int:inventory_id>/delete/', views.delete_inventory, name='delete_inventory'),
    
    
    path("admin/return-requests/", views.return_requests_list, name="return-requests-list"),
    path("admin/return-requests/approve/<int:return_id>/", views.approve_return, name="approve-return"),
    path("admin/return-requests/reject/<int:return_id>/", views.reject_return, name="reject-return"),
]