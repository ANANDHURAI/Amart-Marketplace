from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name="admin_dashboard"),
    path('customer-list/', views.customer_list, name="customer_list"),
    path('customer-approval/<pk>/', views.customer_approval, name="customer_approval"),    
    path('categories/', views.category_list, name="category_list"),
    
    
    path('add-category/', views.add_category, name="add_category"),
    path('edit-category/<slug>', views.edit_category, name="edit_category"),
    path(
        "delete-category/<slug:slug>/",
        views.delete_category,
        name="delete_category",
    ),
    path(
        "restore-category/<slug:slug>/",
        views.restore_category,
        name="restore_category",
    ),
    

    path('remove-product-image/<int:image_id>/', views.remove_product_image, name='remove_product_image'),
    path('product-list/', views.product_list, name="product_list"),
    path("products/add/", views.product_form, name="add_product"),
    path("products/edit/<int:product_id>/", views.product_form, name="edit_product"),
    path('product/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    
    
    path('product-approval/<pk>/', views.product_approval, name="product_approval"),
    
    path('add-account/', views.add_account, name="add_account"),
    path('order-list/', views.order_list, name="order_list"),
    path(
        "orders/<int:order_id>/details/",
        views.admin_order_detail,
        name="admin_order_detail",
    ),
    path('update-order-status/<int:order_item_id>/', views.update_order_status, name='update_order_status'),
    path('sales-report/', views.sales_report, name="sales_report"),
    
    
    path('coupons/', views.coupon_list, name="coupon_list"),
    path('add-coupon/', views.add_coupon, name="add_coupon"),
    path('edit-coupon/<id>', views.edit_coupon, name="edit_coupon"),
    path('delete-coupon/<id>', views.delete_coupon, name="delete_coupon"),
    
    
    path('offers/', views.offer_list, name="offer_list"),
    path('add-offer/', views.add_offer, name="add_offer"),
    path('edit-offer/<id>', views.edit_offer, name="edit_offer"),
    path('delete-offer/<id>', views.delete_offer, name="delete_offer"),

    #inventory
    path('inventory/add/', views.add_edit_inventory, name='add_inventory'),
    path('inventory/edit/<int:inventory_id>/', views.add_edit_inventory, name='edit_inventory'),
    path('inventory/list/', views.inventory_list, name='inventory_list'),
    path('inventory/status/<int:inventory_id>/', views.inventory_status, name='inventory_status'),
    path('inventory/delete/<int:inventory_id>/', views.delete_inventory, name='delete_inventory'),
    

]