
    
    
from django.urls import path
from . import views

urlpatterns = [
    
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add-to-cart"),
    path("cart/items/<int:cart_item_id>/update/", views.update_cart_item, name="update-cart-item"),
    path("cart/items/<int:cart_item_id>/delete/", views.remove_cart_item, name="remove-cart-item"),

    path("favourites/", views.favourites, name="favourites"),
    path("favourites/add/<int:product_id>/", views.add_to_favourite, name="add-to-favourite"),
    path("favourites/items/<int:favourite_item_id>/delete/", views.remove_favourite_item, name="remove-favourite-item"),
    
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/place-order/", views.place_order, name="place-order"),
    path("checkout/finalize/", views.finalize_order, name="finalize-order"),
    path("checkout/coupon/preview/", views.preview_coupon, name="preview-coupon"),
    
    path("<slug:slug>/", views.product_page, name="product_page"),

]
