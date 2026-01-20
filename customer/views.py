from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import Customer
from django.http import HttpResponse
from .models import Cart, CartItem, Address, Order, OrderItem, FavouriteItem, Wallet
from aadmin.models import Coupon, CategoryOffer
from product.models import Product, Inventory
from .utils import list_of_states_in_india
from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth import logout
from ecom.views import get_next_url
from django.db import transaction
from django.db.models import F
import logging
from django.urls import reverse
import re
from django.core.exceptions import ValidationError
from django.db.models import Sum, Prefetch
from django.http import HttpResponseRedirect
from django.conf import settings
import razorpay 
from functools import wraps


def customer_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('customer_login')
        
        if request.user.is_customer and Customer.objects.filter(pk=request.user.pk).exists():
            return view_func(request, *args, **kwargs)

        return redirect('customer_login')
    return _wrapped_view



@customer_required
def dashboard(request):
    customer = get_object_or_404(Customer, pk=request.user.pk)

    orders = (
        Order.objects.filter(customer=customer)
        .prefetch_related(
            Prefetch("items", queryset=OrderItem.objects.select_related("product"))
        )
        .annotate(total_quantity=Sum("items__quantity"))
        .order_by("-created_at")[:5]
    )

    customer.address = Address.objects.filter(customer=customer, is_default=True).first()

    context = {
        "customer": customer, 
        "orders": orders
    }
    return render(request, "customer/customer-dashboard.html", context)




@customer_required
def address(request):
    customer = Customer.objects.get(id=request.user.id)
    addresses = Address.objects.filter(customer=customer)
    context = {"customer": customer, "addresses": addresses}
    return render(request, "customer/customer-address.html", context)




@customer_required
def profile(request):
    customer = Customer.objects.get(id=request.user.id)
    context = {"customer": customer}
    return render(request, "customer/customer-profile.html", context)




@customer_required
def edit_profile(request):
    if request.method == "POST":
        customer = Customer.objects.get(id=request.user.id)
        customer.first_name = request.POST.get("first_name").title()
        customer.last_name = request.POST.get("last_name").title()
        customer.mobile = request.POST.get("mobile")

        profile_image = request.FILES.get("profile_image")
        if profile_image:
            customer.profile_image = profile_image

        customer.save()
        messages.success(request, "Profile updated successfully!")

    return redirect("customer_profile")




@customer_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        customer = Customer.objects.get(id=request.user.id)

        if not customer.check_password(current_password):
            error_message = "The current password you entered is incorrect."
            messages.error(request, error_message)
            return redirect("change_password")

        if password1 != password2:
            error_message = "The new passwords do not match. Please try again."
            messages.error(request, error_message)
            return redirect("change_password")

        customer.set_password(password1)
        customer.save()
        logout(request)
        success_message = "Your password has been successfully changed. Please Login"
        messages.success(request, success_message)
        return redirect("customer_profile")

    return render(request, "customer/change-password.html")






def validate_address_data(data):
    errors = []

    name = data.get("name", "").strip()
    mobile = data.get("mobile", "").strip()
    pincode = data.get("pincode", "").strip()
    building = data.get("building", "").strip()
    street = data.get("street", "").strip()
    city = data.get("city", "").strip()
    district = data.get("district", "").strip()
    state = data.get("state", "").strip()

    if not re.fullmatch(r"[A-Za-z]+(?:[\s-][A-Za-z]+)*", name):
        errors.append("Invalid full name.")

    if not re.fullmatch(r"[6-9]\d{9}", mobile):
        errors.append("Invalid mobile number.")

    if not re.fullmatch(r"[1-9]\d{5}", pincode):
        errors.append("Invalid pincode.")

    if len(building) < 3:
        errors.append("Building name is too short.")

    if len(street) < 3:
        errors.append("Street name is too short.")

    if not re.fullmatch(r"[A-Za-z ]+", district):
        errors.append("Invalid district name.")

    if state not in list_of_states_in_india:
        errors.append("Invalid state selected.")

    return errors





@customer_required
def new_address(request):
    if request.method == "POST":
        errors = validate_address_data(request.POST)

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("new_address")

        name = request.POST["name"].strip().title()
        mobile = request.POST["mobile"].strip()
        pincode = request.POST["pincode"].strip()
        building = request.POST["building"].strip().title()
        street = request.POST["street"].strip().title()
        city = request.POST.get("city", "").strip().title()
        district = request.POST["district"].strip().title()
        state = request.POST["state"].strip()

        customer = Customer.objects.get(id=request.user.id)

        address_parts = [
            name,
            building,
            street,
            city if city else None,
            f"{district}, {state}",
            f"Pincode - {pincode}",
            f"Mobile: {mobile}",
        ]

        address_text = "\n".join(filter(None, address_parts))

        address = Address.objects.create(
            customer=customer,
            name=name,
            mobile=mobile,
            pincode=pincode,
            building=building,
            street=street,
            city=city,
            district=district,
            state=state,
            address_text=address_text,
        )

        if not Address.objects.filter(customer=customer).exclude(id=address.id).exists():
            address.is_default = True
            address.save()

        return redirect("checkout" if "checkout_submit" in request.POST else "customer_address")

    return render(request, "customer/address_form.html", {
        "states": list_of_states_in_india
    })





@customer_required
def edit_address(request, address_id):
    address = Address.objects.get(id=address_id)
    if request.method == "POST":
        name = request.POST.get("name").title()
        pincode = int(request.POST.get("pincode"))
        mobile = int(request.POST.get("mobile"))
        building = request.POST.get("building").title()
        street = request.POST.get("street").title()
        city = request.POST.get("city").title()
        district = request.POST.get("district").title()
        state = request.POST.get("state").title()
        customer = Customer.objects.get(id=request.user.id)
        address_parts = [
            name,
            building,
            street,
            f"{district}, {state}",
            f"Pincode: {int(pincode)}",
            f"Mobile: {int(mobile)}",
        ]
        if city:
            address_parts.insert(3, city)
        address_text = "\n".join(address_parts)

        address.customer = customer
        address.name = name
        address.pincode = pincode
        address.mobile = mobile
        address.building = building
        address.street = street
        address.city = city
        address.district = district
        address.state = state
        address.address_text = address_text
        address.save()

        return redirect("customer_address")

    context = {"address": address, "states": list_of_states_in_india}
    return render(request, "customer/address_form.html", context)





@customer_required
def remove_address(request, address_id):
    address = Address.objects.get(id=address_id)
    address.delete()
    return redirect("customer_address")





@customer_required
def default_address(request, address_id):
    address = Address.objects.get(id=address_id)

    try:
        address_default = Address.objects.get(is_default=True)
        address_default.is_default = False
        address_default.save()
    except Exception as e:
        pass

    address.is_default = True
    address.save()

    return redirect("customer_address")





@customer_required
def orders(request):
    customer = Customer.objects.get(id=request.user.id)
    orders = (
        Order.objects.filter(customer=customer)
        .annotate(total_quantity=Sum("items__quantity"))
        .order_by("-created_at")
    )

    for order in orders:
        order.order_items = OrderItem.objects.filter(order=order)
        order.sub_total = 0

    
        order.has_active_items = order.order_items.exclude(status="cancelled").exists()

        for order_item in order.order_items:
            order_item.product.primary_image = order_item.product.product_images.filter(
                priority=1
            ).first()
            order.sub_total += order_item.quantity * order_item.inventory.price

    context = {"customer": customer, "orders": orders}
    return render(request, "customer/customer-orders.html", context)




@customer_required
@transaction.atomic
def cancel_order(request, order_id):
    order = Order.objects.get(id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    wallet, created = Wallet.objects.get_or_create(customer=request.user)

    refund_amount = 0
    for order_item in order_items:
        if order_item.status != "cancelled":
            order_item.status = "cancelled"
            order_item.inventory.stock += order_item.quantity
            order_item.inventory.save()
            order_item.save()

            # Refund only for non-COD paid orders
            if order.is_paid and order.payment_method != "COD":
                refund_amount += order_item.quantity * order_item.inventory.price

    order.status = "cancelled"
    order.save()

    if refund_amount > 0:
        wallet.balance += refund_amount
        wallet.save()
        messages.success(request, f"Order cancelled. Refund of ₹{refund_amount} added to your wallet.")
    else:
        messages.success(request, "Order cancelled successfully.")

    return redirect("customer_orders")





@customer_required
def cancel_order_item(request, order_item_id):
    order_item = OrderItem.objects.get(id=order_item_id)
    wallet, created = Wallet.objects.get_or_create(customer=request.user)

    if order_item.status != "cancelled":
        order_item.status = "cancelled"

        # Refund only for non-COD paid orders
        if order_item.order.is_paid and order_item.order.payment_method != "COD":
            wallet.balance += order_item.quantity * order_item.inventory.price
            wallet.save()

        order_item.inventory.stock += order_item.quantity
        order_item.inventory.save()
        order_item.save()

        
        order = order_item.order
        if not OrderItem.objects.filter(order=order).exclude(status="cancelled").exists():
            order.status = "cancelled"
            order.save()

    return redirect("customer_orders")





@customer_required
@transaction.atomic
def return_order(request, order_id):
    order = Order.objects.get(id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    wallet, created = Wallet.objects.get_or_create(customer=request.user)

    if order.status == "delivered":
        refund_amount = 0

        for order_item in order_items:
            if order_item.status != "returned":
                order_item.status = "returned"
                order_item.inventory.stock += order_item.quantity
                order_item.inventory.save()
                order_item.save()

                # Refund only for non-COD paid orders
                if order.is_paid and order.payment_method != "COD":
                    refund_amount += order_item.quantity * order_item.inventory.price

        order.status = "returned"
        order.save()

        if refund_amount > 0:
            wallet.balance += refund_amount
            wallet.save()
            messages.success(request, f"Order returned. Refund of ₹{refund_amount} added to your wallet.")
        else:
            messages.success(request, "Order returned successfully.")
    else:
        messages.error(request, "This order cannot be returned.")

    return redirect("customer_orders")






@customer_required
def favourites(request):
    try:
        customer = Customer.objects.get(id=request.user.id)
    except Customer.DoesNotExist:
        customer = None
    favourite_items = FavouriteItem.objects.filter(customer=customer)

    for favourite_item in favourite_items:
        favourite_item.product.primary_image = (
            favourite_item.product.product_images.filter(priority=1).first()
        )
        available_inventory = favourite_item.product.inventory_sizes.first()
        if available_inventory:
            favourite_item.product.price = available_inventory.price
    context = {"favourite_items": favourite_items, "customer": customer}
    return render(request, "customer/favourites.html", context)





@customer_required
def add_to_favourite(request, product_id):
    next_url = get_next_url(request)
    try:
        customer = Customer.objects.get(id=request.user.id)
    except Customer.DoesNotExist:
        messages.error(request, "Customer not found.")
        return redirect("home")
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:

        messages.error(request, "Product not found.")
        return redirect(next_url)
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
    next_url = get_next_url(request)
    favourite_item = FavouriteItem.objects.get(id=favourite_item_id)
    favourite_item.delete()
    return redirect(next_url)





@customer_required
def cart(request):
    customer = Customer.objects.get(id=request.user.id)
    cart, _ = Cart.objects.get_or_create(customer=customer)

    cart_items = CartItem.objects.select_related(
        "product", "inventory"
    ).prefetch_related(
        "product__inventory_sizes"
    ).filter(cart=cart)

    total_amount = 0

    for item in cart_items:
        # product image
        item.product.primary_image = (
            item.product.product_images.filter(priority=1).first()
        )

        # only available inventories for THIS product
        item.available_inventories = item.product.inventory_sizes.filter(
            is_active=True,
            stock__gt=0
        )

        total_amount += item.quantity * item.inventory.price

    cart.total_amount = total_amount

    return render(
        request,
        "customer/cart.html",
        {
            "customer": customer,
            "cart_items": cart_items,
            "cart": cart,
        },
    )





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
    if request.method == "POST":
        cart_item = CartItem.objects.get(id=cart_item_id)
        quantity = int(request.POST.get("product-quantity"))
        size = request.POST.get("product-size")
        inventory = Inventory.objects.get(product=cart_item.product, size=size)

        if quantity > inventory.stock:
            error_message = (
                f"Only {inventory.stock} item(s) available in stock for this size."
            )
            messages.error(request, error_message)
            return redirect("product_page", slug=cart_item.product.slug)

        cart_item.quantity = quantity
        cart_item.inventory = inventory
        cart_item.save()

    return redirect("cart")






@customer_required
def remove_cart_item(request, cart_item_id):
    cart_item = CartItem.objects.get(id=cart_item_id)

    cart_item.delete()

    return redirect("cart")





@customer_required
def checkout(request):
    customer = Customer.objects.get(id=request.user.id)
    cart, _ = Cart.objects.get_or_create(customer=customer)
    cart_items = CartItem.objects.filter(cart=cart)
    wallet = Wallet.objects.get(customer=customer)
    if not cart_items.exists():
        return redirect("cart")

    total_amount = 0
    total_offer = 0
    selected_address_id = request.session.get("address_id")
    selected_payment_method = request.session.get("payment_method")

    for cart_item in cart_items:
        cart_item.product.primary_image = cart_item.product.product_images.filter(
            priority=1
        ).first()
        offer = CategoryOffer.objects.filter(
            category=cart_item.product.main_category
        ).first()
        offer_discount = offer.discount if offer else 0

        amount = cart_item.quantity * cart_item.inventory.price
        total_amount += amount
        total_offer += round(amount * offer_discount / 100)

    cart.total_amount = total_amount
    cart.total_offer = total_offer
    cart.remaining_amount = total_amount - total_offer
    cart.save()

    addresses = Address.objects.filter(customer=customer)

    context = {
        "customer": customer,
        "cart_items": cart_items,
        "cart": cart,
        "addresses": addresses,
        "states": list_of_states_in_india,
        "selected_address_id": selected_address_id,
        "selected_payment_method": selected_payment_method,
        "wallet_balance": wallet.balance,
    }
    return render(request, "customer/checkout.html", context)







from payment.views import handle_wallet_payment

@customer_required
def place_order(request):
    if request.method != "POST":
        return redirect("checkout")

    address_id = request.POST.get("address_id")
    payment_method = request.POST.get("payment_method")
    coupon_code = request.POST.get("coupon_code", "").upper()

    request.session["address_id"] = address_id
    request.session["payment_method"] = payment_method

    try:
        cart = Cart.objects.get(customer=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items.exists():
            messages.error(request, "Your cart is empty!")
            return redirect("checkout")

        total_amount = cart_items.aggregate(
            total=Sum(F("quantity") * F("inventory__price"))
        )["total"] or 0

        # Category offers
        total_offer = 0
        for item in cart_items:
            offer = CategoryOffer.objects.filter(
                category=item.product.main_category
            ).first()
            if offer:
                total_offer += round(item.quantity * item.inventory.price * offer.discount / 100)

        total_amount -= total_offer

        # Coupon
        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code, is_active=True).first()

            if not coupon:
                messages.error(request, "Invalid coupon code.")
                return redirect("checkout")

            
            if request.session.get("coupon_code") == coupon.code:
                messages.error(request, "You have already used this coupon.")
                return redirect("checkout")

            if coupon.quantity < 1:
                messages.error(request, "This coupon is no longer available.")
                return redirect("checkout")

            if coupon.minimum_purchase > total_amount:
                messages.error(
                    request,
                    f"Minimum purchase of ₹{coupon.minimum_purchase} required to use this coupon."
                )
                return redirect("checkout")

            total_amount -= coupon.discount

            request.session["coupon_code"] = coupon.code
            request.session["discount"] = coupon.discount

        request.session["total_amount"] = total_amount

        
        # PAYMENT DECISION 
        if payment_method == "wallet":
            return handle_wallet_payment(request, request.user.customer, total_amount)

        
        if payment_method == "cod":
            if total_amount > 1000:
                messages.error(request, "COD not available above ₹1000")
                return redirect("checkout")

            request.session["payment_successful"] = False  
            return redirect("finalize_order")

        if payment_method == "razorpay":
            return redirect("razorpay_order_creation", amount=total_amount)

        messages.error(request, "Invalid payment method")
        return redirect("checkout")

    except Exception as e:
        logger.error(f"place_order error: {str(e)}")
        messages.error(request, "Something went wrong. Try again.")
        return redirect("checkout")



logger = logging.getLogger(__name__)





@customer_required
@transaction.atomic
def create_order(request):
    address_id = request.session.get("address_id")
    payment_method = request.session.get("payment_method")
    discount = request.session.get("discount", 0)
    coupon_code = request.session.get("coupon_code")

    customer = request.user.customer
    address = get_object_or_404(Address, id=address_id, customer=customer)
    cart = get_object_or_404(Cart, customer=customer)
    cart_items = CartItem.objects.filter(cart=cart)

    total_amount = sum(
        item.quantity * item.inventory.price for item in cart_items
    )

    total_amount = max(total_amount - discount, 0)
    
    order = Order.objects.create(
        customer=customer,
        address=address.address_text,
        total_amount=total_amount,
        payment_method=payment_method,
        is_paid=payment_method in ["razorpay", "wallet"], 
    )

    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code).first()
        if coupon:
            order.discount = discount
            order.coupon = coupon
            order.save()
            coupon.quantity -= 1
            coupon.save()

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            inventory=item.inventory,
            quantity=item.quantity,
            price=item.inventory.price,
        )
        item.inventory.stock -= item.quantity
        item.inventory.save()

    cart_items.delete()
    return order





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
        "discount",
    ]:
        request.session.pop(key, None)

    messages.success(request, "Order placed successfully!")
    return redirect("order_confirmation", order_id=order.id)






@customer_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    customer = Customer.objects.filter(account_ptr=request.user).first()
    if not customer:
        messages.error(request, "Customer not found.")
        return redirect("home")

    
    order = Order.objects.filter(id=order_id, customer=customer).first()
    if not order:
        messages.error(request, "Order not found.")
        return redirect("customer_orders")
    messages.success(request, f"Your order #{order.id} has been placed successfully!")
    return HttpResponseRedirect(reverse("payment_success"))


razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
)






@customer_required
def customer_wallet(request):
    customer = request.user.customer
    wallet, _ = Wallet.objects.get_or_create(customer=customer)

    order_items = OrderItem.objects.filter(
        order__customer=customer,
        status="cancelled",
        order__is_paid=True
    ).exclude(order__payment_method="COD").order_by("-id")

    context = {
        "customer": customer,
        "wallet": wallet,
        "order_items": order_items,
    }

    if request.method == "POST":
        amount = int(request.POST.get("amount", 0))

        if amount > 0:
            currency = "INR"

            razorpay_order = razorpay_client.order.create({
                "amount": amount * 100,
                "currency": currency,
                "payment_capture": 1,
                "receipt": f"wallet_{customer.id}"
            })

            # store wallet top-up info in session
            request.session["wallet_topup"] = True
            request.session["wallet_amount"] = amount

            context.update({
                "razorpay_order_id": razorpay_order["id"],
                "razorpay_merchant_key": settings.RAZOR_KEY_ID,
                "razorpay_amount": amount * 100,
                "currency": currency,
                "callback_url": reverse("razorpay_paymenthandler"),
            })

    return render(request, "customer/customer-wallet.html", context)






@customer_required
def invoice(request, order_id):
    order = Order.objects.get(id=order_id)
    order.order_items = OrderItem.objects.filter(order=order)
    order.sub_total = 0

    for order_item in order.order_items:
        order_item.product.primary_image = order_item.product.product_images.filter(
            priority=1
        ).first()
        order.sub_total += order_item.quantity * order_item.inventory.price

    context = {"order": order}
    return render(request, "customer/invoice.html", context)
