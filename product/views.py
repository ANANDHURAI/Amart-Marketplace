from django.shortcuts import render
import logging
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.db import transaction
from django.db.models import F, Prefetch, Sum
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

import razorpay
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from accounts.models import Customer
from aadmin.models import CategoryOffer, Coupon
from ecom.views import get_next_url

from .models import Product, ProductImage, Inventory
from customer.models import Address, Cart, CartItem, FavouriteItem, Order, Wallet


logger = logging.getLogger(__name__)
from customer.views import _get_customer , customer_required ,create_order
from customer.utils import list_of_states_in_india


@customer_required
def cart(request):
    """Cart page with items, primary image, available sizes, and total."""
    customer = _get_customer(request)
    cart, _ = Cart.objects.get_or_create(customer=customer)
    cart_items = (
        CartItem.objects.filter(cart=cart)
        .select_related("product", "inventory")
        .prefetch_related("product__product_images", "product__inventory_sizes")
    )

    total_amount = 0
    for item in cart_items:
        item.product.primary_image = (
            item.product.product_images.order_by("priority").first()
        )
        item.available_inventories = item.product.inventory_sizes.filter(
            is_active=True, stock__gt=0
        )
        total_amount += item.quantity * item.inventory.price

    cart.total_amount = total_amount
    return render(request, "customer/cart.html", {
        "customer": customer,
        "cart_items": cart_items,
        "cart": cart,
    })





@customer_required
def add_to_cart(request, product_id):
    if request.method == "POST":
        customer = get_object_or_404(Customer, email=request.user.email)
        product = get_object_or_404(Product, pk=product_id)
        cart, cart_created = Cart.objects.get_or_create(customer=customer)
        quantity = int(request.POST.get("product-quantity"))
        size = request.POST.get("product-size")

        inventory_items = Inventory.objects.filter(product=product, size=size)
        if not inventory_items.exists():
            messages.error(request, "Selected size is not available for this product.")
            return redirect("product_page", slug=product.slug)

        inventory = inventory_items.first()

        if quantity > inventory.stock:
            error_message = (
                f"Only {inventory.stock} item(s) available in stock for this size."
            )
            messages.error(request, error_message)
            return redirect("product_page", slug=product.slug)

        with transaction.atomic():
            cart_item, cart_item_created = CartItem.objects.get_or_create(
                cart=cart, product=product, inventory=inventory
            )

            
            FavouriteItem.objects.filter(customer=customer, product=product).delete()

            # Managing the maximum number of products per customer
            if not cart_item_created:
                if cart_item.quantity + quantity > 10:
                    cart_item.quantity = 10
                else:
                    cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()

    return redirect("cart")






@customer_required
def update_cart_item(request, cart_item_id):
    if request.method != "POST":
        return redirect("cart")

    customer = _get_customer(request)
    cart = get_object_or_404(Cart, customer=customer)
    cart_item = get_object_or_404(
        CartItem,
        id=cart_item_id,
        cart=cart
    )

    try:
        quantity = int(request.POST.get("product-quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    size = request.POST.get("product-size")

    inventory = get_object_or_404(
        Inventory,
        product=cart_item.product,
        size=size
    )

    if quantity < 1:
        message = "Quantity must be at least 1."

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "message": message
            }, status=400)

        messages.warning(request, message)
        return redirect("cart")

    if quantity > 10:
        message = "Maximum limit is 10 units."

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "message": message
            }, status=400)

        messages.warning(request, message)
        return redirect("cart")

    if quantity > inventory.stock:
        message = f"Only {inventory.stock} left in stock."

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "message": message
            }, status=400)

        messages.error(request, message)
        return redirect("cart")

    cart_item.quantity = quantity
    cart_item.inventory = inventory
    cart_item.save()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "success": True,
            "quantity": cart_item.quantity
        })

    return redirect("cart")





@customer_required
def remove_cart_item(request, cart_item_id):
    """Remove a cart item; item must belong to current customer's cart."""
    customer = _get_customer(request)
    cart = get_object_or_404(Cart, customer=customer)
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart=cart)
    cart_item.delete()
    return redirect("cart")





@customer_required
def favourites(request):
    """List favourite products with primary image and lowest price."""
    customer = _get_customer(request)
    favourite_items = (
        FavouriteItem.objects.filter(customer=customer)
        .select_related("product", "product__main_category")
        .prefetch_related("product__product_images", "product__inventory_sizes")
    )

    for fi in favourite_items:
        fi.product.primary_image = (
            fi.product.product_images.order_by("priority").first()
        )
        inv = fi.product.inventory_sizes.filter(is_active=True).first()
        fi.product.price = inv.price if inv else 0

    return render(request, "customer/favourites.html", {
        "favourite_items": favourite_items,
        "customer": customer,
    })





@customer_required
def add_to_favourite(request, product_id):
    """Add a product to favourites; redirects back to referrer or home."""
    next_url = get_next_url(request) or "home"
    customer = _get_customer(request)
    product = get_object_or_404(Product, id=product_id)
    favourite_item, created = FavouriteItem.objects.get_or_create(
        customer=customer, product=product
    )

    if created:
        messages.success(request, "Product added to favourites!")
    else:
        messages.info(request, "Product is already in favourites.")

    return redirect(next_url)






@customer_required
def remove_favourite_item(request, favourite_item_id):
    """Remove an item from favourites; redirects back to referrer."""
    next_url = get_next_url(request) or "home"
    customer = _get_customer(request)
    favourite_item = get_object_or_404(
        FavouriteItem, id=favourite_item_id, customer=customer
    )
    favourite_item.delete()
    return redirect(next_url)





def _build_checkout_context(request, customer=None):
    """Rebuild the full checkout page context (cart, totals, addresses, wallet)."""
    customer = customer or _get_customer(request)
    cart, _ = Cart.objects.get_or_create(customer=customer)
    cart_items = (
        CartItem.objects.filter(cart=cart)
        .select_related("product", "product__main_category", "inventory")
        .prefetch_related("product__product_images")
    )

    wallet, _ = Wallet.objects.get_or_create(customer=customer)
    category_ids = list({ci.product.main_category_id for ci in cart_items})
    offers_by_category = {
        co["category_id"]: co["discount"]
        for co in CategoryOffer.objects.filter(
            category_id__in=category_ids
        ).values("category_id", "discount")
    }

    total_amount = 0
    total_offer = 0
    for cart_item in cart_items:
        cart_item.product.primary_image = (
            cart_item.product.product_images.order_by("priority").first()
        )
        offer_discount = offers_by_category.get(cart_item.product.main_category_id, 0)
        amount = cart_item.quantity * cart_item.inventory.price
        total_amount += amount
        total_offer += round(amount * offer_discount / 100)

    cart.total_amount = total_amount
    cart.total_offer = total_offer
    cart.remaining_amount = total_amount - total_offer
    cart.save()

    addresses = Address.objects.filter(customer=customer)
    return {
        "customer": customer,
        "cart_items": cart_items,
        "cart": cart,
        "addresses": addresses,
        "states": list_of_states_in_india,
        "selected_address_id": request.session.get("address_id"),
        "selected_payment_method": request.session.get("payment_method"),
        "wallet_balance": wallet.balance,
        "remaining_amount": total_amount - total_offer,
    }




@customer_required
def checkout(request):
    """Checkout: cart summary, addresses, payment method, category offers and wallet."""
    customer = _get_customer(request)
    cart, _ = Cart.objects.get_or_create(customer=customer)
    if not CartItem.objects.filter(cart=cart).exists():
        return redirect("cart")

    context = _build_checkout_context(request, customer=customer)
    return render(request, "customer/checkout.html", context)









from payment.views import handle_wallet_payment

@customer_required
def place_order(request):
    if request.method != "POST":
        return redirect("checkout")

    address_id     = request.POST.get("address_id")
    payment_method = request.POST.get("payment_method")
    coupon_code    = request.POST.get("coupon_code", "").strip().upper()

    request.session["address_id"]     = address_id
    request.session["payment_method"] = payment_method

    try:
        customer   = _get_customer(request)
        cart       = Cart.objects.get(customer=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related(
            "product__main_category", "inventory"
        )

        if not cart_items.exists():
            messages.error(request, "Your cart is empty!")
            return redirect("checkout")

        total_amount = sum(
            item.quantity * item.inventory.price for item in cart_items
        )

        total_offer = 0
        for item in cart_items:
            offer = CategoryOffer.objects.filter(
                category=item.product.main_category, is_active=True
            ).first()
            if offer:
                total_offer += round(
                    item.quantity * item.inventory.price * offer.discount / 100
                )

        amount_after_offers = total_amount - total_offer

        coupon          = None
        coupon_discount = 0

        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code, is_active=True).first()

            if not coupon:
                messages.error(request, "Invalid or expired coupon code.")
                return redirect("checkout")

            already_used = Order.objects.filter(
                customer=customer, coupon=coupon
            ).exists()
            if already_used:
                messages.error(request, "You have already used this coupon.")
                return redirect("checkout")

            if coupon.quantity < 1:
                messages.error(request, "This coupon is no longer available.")
                return redirect("checkout")

            if amount_after_offers < coupon.minimum_purchase:
                messages.error(
                    request,
                    f"Minimum purchase of ₹{coupon.minimum_purchase} required. "
                    f"Your amount after offers: ₹{amount_after_offers}."
                )
                return redirect("checkout")

            coupon_discount = min(coupon.discount, amount_after_offers)

        final_amount = max(amount_after_offers - coupon_discount, 0)

        request.session["total_amount"]     = final_amount
        request.session["coupon_code"]      = coupon.code if coupon else ""
        request.session["coupon_discount"]  = coupon_discount 

        if payment_method == "wallet":
            return handle_wallet_payment(request, customer, final_amount)

        if payment_method == "cod":
            if final_amount > 1000:
                messages.error(request, "COD is not available for orders above ₹1000.")
                return redirect("checkout")
            request.session["payment_successful"] = False
            return redirect("finalize-order")

        if payment_method == "razorpay":
            return redirect("razorpay_order_creation", amount=final_amount)

        messages.error(request, "Invalid payment method selected.")
        return redirect("checkout")

    except Exception as exc:
        logger.exception("place_order error: %s", exc)
        messages.error(request, "Something went wrong. Please try again.")
        return redirect("checkout")
    
    
    


@customer_required
@require_POST
def preview_coupon(request):
    customer = _get_customer(request)
    cart = Cart.objects.filter(customer=customer).first()
    if not cart:
        return JsonResponse({"valid": False, "message": "Cart not found."})

    code = request.POST.get("coupon_code", "").strip().upper()
    if not code:
        return JsonResponse({"valid": False, "message": "Please enter a coupon code."})

    coupon = Coupon.objects.filter(code=code, is_active=True).first()
    if not coupon:
        return JsonResponse({"valid": False, "message": "Invalid or expired coupon."})

    already_used = Order.objects.filter(customer=customer, coupon=coupon).exists()
    if already_used:
        return JsonResponse({"valid": False, "message": "You have already used this coupon."})

    if coupon.quantity < 1:
        return JsonResponse({"valid": False, "message": "This coupon has been fully redeemed."})

    cart_items = CartItem.objects.filter(cart=cart).select_related(
        "product__main_category", "inventory"
    )

    total_amount = sum(
        item.quantity * item.inventory.price for item in cart_items
    )

    total_offer = 0
    for item in cart_items:
        offer = CategoryOffer.objects.filter(
            category=item.product.main_category, is_active=True
        ).first()
        if offer:
            total_offer += round(
                item.quantity * item.inventory.price * offer.discount / 100
            )

    remaining_amount = total_amount - total_offer 

    if remaining_amount < coupon.minimum_purchase:
        return JsonResponse({
            "valid": False,
            "message": (
                f"Minimum purchase of ₹{coupon.minimum_purchase} required. "
                f"Your amount after offers: ₹{remaining_amount}."
            ),
        })

    coupon_discount = min(coupon.discount, remaining_amount)
    final_amount    = remaining_amount - coupon_discount

    return JsonResponse({
        "valid":           True,
        "coupon_discount": coupon_discount,
        "final_amount":    final_amount,
        "message":         f"Coupon applied! You save ₹{coupon_discount}.",
    })




@customer_required
def finalize_order(request):
    payment_method = request.session.get("payment_method")

    if payment_method != "cod" and not request.session.get("payment_successful"):
        messages.error(request, "Payment not completed")
        return redirect("checkout")

    order = create_order(request)

    if not order:
        messages.error(request, "Order creation failed")
        return redirect("checkout")

    for key in [
        "payment_successful",
        "total_amount",
        "payment_method",
        "address_id",
        "coupon_code",
        "coupon_discount",  
    ]:
        request.session.pop(key, None)

    messages.success(request, "Order placed successfully!")
    return redirect("order-confirmation", order_id=order.id)






def product_page(request, slug):
    product = get_object_or_404(
        Product.approved_objects.select_related("main_category"),
        slug=slug,
    )
    product_images = ProductImage.objects.filter(product=product).order_by("priority")
    inventory = Inventory.objects.filter(product=product, is_active=True)

    discount = CategoryOffer.objects.filter(
        category=product.main_category
    ).values_list("discount", flat=True).first() or 0

    # Calculate discounted price for each size
    for item in inventory:
        if discount > 0:
            item.discounted_price = int(item.price * (1 - discount / 100))
        else:
            item.discounted_price = item.price

    product.is_favourite = False
    if request.user.is_authenticated:
        product.is_favourite = FavouriteItem.objects.filter(
            customer_id=request.user.pk,
            product=product,
        ).exists()

    return render(request, "home/product-page.html", {
        "product": product,
        "offer": discount,
        "inventory": inventory,
        "product_images": product_images,
        "title": product.name,
    })