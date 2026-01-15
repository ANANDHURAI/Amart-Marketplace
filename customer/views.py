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
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
import logging
from django.urls import reverse

from django.db.models import Sum, Prefetch
from django.http import HttpResponseRedirect
from django.conf import settings
import razorpay 


# def@login_required(func):
#     """
#     Custom login required decorator to check if the user is authenticated and a customer.
#     """

#     def wrapper(request, *args, **kwargs):
#         if not request.user.is_authenticated or not request.user.is_customer:
#             target_url = request.build_absolute_uri()
#             request.session["customer_target_url"] = target_url
#             return redirect("customer_login")
#         return func(request, *args, **kwargs)

#     return wrapper


# Customer Profile Session


def dashboard(request):
    try:
        customer = Customer.objects.get(id=request.user.id)
    except Customer.DoesNotExist:
        customer = None

    orders = (
        Order.objects.filter(customer=customer)
        .prefetch_related(
            Prefetch("items", queryset=OrderItem.objects.select_related("product"))
        )
        .annotate(total_quantity=Sum("items__quantity"))
        .order_by("-created_at")[:5]
    )

    try:
        customer.address = Address.objects.get(customer=customer, is_default=True)
    except Address.DoesNotExist:
        pass

    context = {"customer": customer, "orders": orders}
    return render(request, "customer/customer-dashboard.html", context)


@login_required
def address(request):
    customer = Customer.objects.get(id=request.user.id)
    addresses = Address.objects.filter(customer=customer)
    context = {"customer": customer, "addresses": addresses}
    return render(request, "customer/customer-address.html", context)


@login_required
def profile(request):
    customer = Customer.objects.get(id=request.user.id)
    context = {"customer": customer}
    return render(request, "customer/customer-profile.html", context)


@login_required
def edit_profile(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name").title()
        last_name = request.POST.get("last_name").title()
        mobile = request.POST.get("mobile")

        customer = Customer.objects.get(id=request.user.id)
        customer.first_name = first_name
        customer.last_name = last_name
        customer.mobile = mobile
        customer.save()

    return redirect("customer_profile")


@login_required
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


@login_required
def new_address(request):
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
            f"Pincode - {str(pincode)}",
            f"Mobile: {str(mobile)}",
        ]
        if city:
            address_parts.insert(3, city)
        address_text = "\n".join(address_parts)

        if not all([name, pincode, mobile, building, street, district, state]):
            messages.error(request, "Please fill in all required fields.")
            return redirect("new_address")

        new_address = Address.objects.create(
            customer=customer,
            name=name,
            pincode=pincode,
            mobile=mobile,
            building=building,
            street=street,
            city=city,
            district=district,
            state=state,
            address_text=address_text,
        )

        if Address.objects.filter(customer=customer).count() == 1:
            new_address.is_default = True

        if "checkout_submit" in request.POST:
            return redirect("checkout")

        return redirect("customer_address")

    context = {"states": list_of_states_in_india}
    return render(request, "customer/address_form.html", context)


@login_required
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


@login_required
def remove_address(request, address_id):
    address = Address.objects.get(id=address_id)
    address.delete()
    return redirect("customer_address")


@login_required
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


@login_required
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

        for order_item in order.order_items:
            order_item.product.primary_image = order_item.product.product_images.filter(
                priority=1
            ).first()
            order.sub_total += order_item.quantity * order_item.inventory.price

    context = {"customer": customer, "orders": orders}
    return render(request, "customer/customer-orders.html", context)


@login_required
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
            refund_amount += order_item.quantity * order_item.inventory.price

    order.status = "cancelled"
    order.save()

    if order.is_paid:
        wallet.balance += refund_amount
        wallet.save()

    messages.success(request, f"Order cancelled. Refund of ₹{refund_amount} added to your wallet.")
    return redirect("customer_orders")


@login_required
def cancel_order_item(request, order_item_id):
    order_item = OrderItem.objects.get(id=order_item_id)
    wallet, created = Wallet.objects.get_or_create(customer__id=request.user.id)

    if order_item.status != "cancelled":
        order_item.status = "cancelled"
        if order_item.order.is_paid:
            wallet.balance += order_item.quantity * order_item.inventory.price
        order_item.inventory.stock += order_item.quantity
        order_item.inventory.save()
        order_item.save()
        wallet.save()

    return redirect("customer_orders")


@login_required
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
                refund_amount += order_item.quantity * order_item.inventory.price

        order.status = "returned"
        order.save()

        if order.is_paid:
            wallet.balance += refund_amount
            wallet.save()

        messages.success(request, f"Order returned. Refund of ₹{refund_amount} added to your wallet.")
    else:
        messages.error(request, "This order cannot be returned.")

    return redirect("customer_orders")


# Customer Favourite Session


@login_required
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


@login_required
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


@login_required
def remove_favourite_item(request, favourite_item_id):
    next_url = get_next_url(request)
    favourite_item = FavouriteItem.objects.get(id=favourite_item_id)
    favourite_item.delete()
    return redirect(next_url)


# Customer Cart

@login_required
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



@login_required
def add_to_cart(request, product_id):
    if request.method == "POST":
        customer = get_object_or_404(Customer, email=request.user.email)
        product = get_object_or_404(Product, pk=product_id)
        cart, cart_created = Cart.objects.get_or_create(customer=customer)
        quantity = int(request.POST.get("product-quantity"))
        size = request.POST.get("product-size")

        # Use filter to handle multiple inventory entries
        inventory_items = Inventory.objects.filter(product=product, size=size)
        if not inventory_items.exists():
            messages.error(request, "Selected size is not available for this product.")
            return redirect("product_page", slug=product.slug)

        # Assuming you want to use the first inventory item
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

            # Removing from the Favourites
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


@login_required
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


@login_required
def remove_cart_item(request, cart_item_id):
    cart_item = CartItem.objects.get(id=cart_item_id)

    cart_item.delete()

    return redirect("cart")


@login_required
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


# Customer Order Session


@login_required
def place_order(request):
    if request.method != "POST":
        return redirect("checkout")

    address_id = request.POST.get("address_id")
    payment_method = request.POST.get("payment_method")
    request.session["address_id"] = address_id
    request.session["payment_method"] = payment_method
    coupon_code = request.POST.get("coupon_code", "").upper()
    # request.session['order_id'] = order.id

    try:
        cart = Cart.objects.get(customer=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items.exists():
            messages.error(request, "Your cart is empty!")
            return redirect("checkout")

        total_amount = (
            cart_items.aggregate(total=Sum(F("quantity") * F("inventory__price")))[
                "total"
            ]
            or 0
        )

        total_offer = sum(
            round(
                cart_item.quantity
                * cart_item.inventory.price
                * (
                    CategoryOffer.objects.filter(
                        category=cart_item.product.main_category
                    )
                    .first()
                    .discount
                    / 100
                )
                if CategoryOffer.objects.filter(
                    category=cart_item.product.main_category
                ).exists()
                else 0
            )
            for cart_item in cart_items
        )

        total_amount -= total_offer

        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code, is_active=True).first()
            if coupon:
                if coupon.discount >= total_amount:
                    messages.error(request, "Coupon is not valid for this purchase.")
                elif coupon.quantity < 1:
                    messages.error(request, "Coupon expired")
                elif coupon.minimum_purchase > total_amount:
                    messages.error(
                        request,
                        f"You should purchase for {coupon.minimum_purchase} to apply this coupon.",
                    )
                else:
                    total_amount -= coupon.discount
                    request.session["discount"] = coupon.discount
                    request.session["coupon_code"] = coupon.code
            else:
                messages.error(request, "Invalid Coupon")

        request.session["total_amount"] = total_amount

        if payment_method == "wallet":
            wallet = Wallet.objects.get(customer=request.user)
            if wallet.balance >= total_amount:
                with transaction.atomic():
                    wallet.balance -= total_amount
                    wallet.save()
                    request.session["payment_successful"] = True
                return redirect("finalize_order")
            else:
                messages.error(request, "Insufficient wallet balance.")
                return redirect("checkout")

        elif payment_method == "cod":
            if total_amount > 1000:
                messages.error(
                    request, "COD is not available for orders above 1000 Rs."
                )
                return redirect("checkout")
            request.session["payment_successful"] = True
            return redirect("finalize_order")

        elif payment_method == "razorpay":
            return redirect("razorpay_order_creation", amount=total_amount)

        else:
            messages.error(request, "Invalid payment method selected.")
            return redirect("checkout")

    except Exception as e:
        logger.error(f"Error in place_order: {str(e)}")
        messages.error(
            request, f"An error occurred while processing your order: {str(e)}"
        )
        return redirect("checkout")


logger = logging.getLogger(__name__)


@login_required
@transaction.atomic
def create_order(request):
    address_id = request.session.get("address_id")
    payment_method = request.session.get("payment_method")
    coupon_code = request.session.get("coupon_code")
    discount = request.session.get("discount", 0)

    if not address_id or not payment_method:
        messages.error(request, "Invalid order data. Please try again.")
        return None

    # Modified: Retrieve the customer object using the logged-in user
    customer = Customer.objects.filter(email=request.user.email).first()
    if not customer:
        messages.error(request, "Customer not found.")
        return None

    address = Address.objects.filter(id=address_id, customer=customer).first()
    if not address:
        messages.error(request, "Invalid address selected.")
        return None

    cart = Cart.objects.filter(customer=customer).first()
    if not cart:
        messages.error(request, "Cart not found.")
        return None

    cart_items = CartItem.objects.filter(cart=cart)

    if not cart_items.exists():
        messages.error(request, "Your cart is empty!")
        return None

    total_amount = 0
    total_offer = 0

    for cart_item in cart_items:
        offer = CategoryOffer.objects.filter(
            category=cart_item.product.main_category
        ).first()
        offer_discount = offer.discount if offer else 0

        amount = cart_item.quantity * cart_item.inventory.price
        total_amount += amount
        total_offer += round(amount * offer_discount / 100)

    total_amount -= total_offer
    total_amount = max(total_amount - discount, 0)

    order = Order.objects.create(
        customer=customer,
        address=address.address_text,
        total_amount=total_amount,
        offer=total_offer,
        payment_method=payment_method,
        is_paid=(payment_method == "razorpay"),
    )

    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code).first()
        if coupon:
            order.discount = discount
            order.coupon = coupon
            order.save()
            Coupon.objects.filter(id=coupon.id).update(quantity=F("quantity") - 1)

    for cart_item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            inventory=cart_item.inventory,
            quantity=cart_item.quantity,
            price=cart_item.inventory.price,
        )
        cart_item.inventory.stock -= cart_item.quantity
        cart_item.inventory.save()

    cart_items.delete()

    return order


@login_required
def finalize_order(request):
    if not request.session.get("payment_successful"):
        messages.error(
            request, "Invalid order attempt. Please complete the payment process."
        )
        return redirect("checkout")

    order = create_order(request)
    if order:
        request.session.pop("payment_successful", None)
        request.session.pop("total_amount", None)
        request.session.pop("payment_method", None)
        request.session.pop("address_id", None)
        request.session.pop("coupon_code", None)
        request.session.pop("discount", None)

        messages.success(request, "Order placed successfully!")
        return redirect("order_confirmation", order_id=order.id)
    else:
        messages.error(
            request, "An error occurred while creating your order. Please try again."
        )
        return redirect("checkout")


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    customer = Customer.objects.filter(account_ptr=request.user).first()
    if not customer:
        messages.error(request, "Customer not found.")
        return redirect("home")

    # Retrieve the order for this customer
    order = Order.objects.filter(id=order_id, customer=customer).first()
    if not order:
        messages.error(request, "Order not found.")
        return redirect("customer_orders")
    messages.success(request, f"Your order #{order.id} has been placed successfully!")
    return HttpResponseRedirect(reverse("payment_success"))


razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
)


@login_required
def customer_wallet(request):
    customer = request.user.customer
    wallet, _ = Wallet.objects.get_or_create(customer=customer)
    order_items = OrderItem.objects.filter(
        order__customer=customer, status="cancelled"
    ).order_by("-id")

    context = {"customer": customer, "wallet": wallet, "order_items": order_items}

    if request.method == "POST":
        amount = int(request.POST.get("amount", 0))
        if amount > 0:
            currency = "INR"
            razorpay_order = razorpay_client.order.create(
                dict(amount=amount * 100, currency=currency, payment_capture="0")
            )
            razorpay_order_id = razorpay_order["id"]
            callback_url = request.build_absolute_uri(reverse("razorpay_callback"))

            context.update(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_merchant_key": settings.RAZOR_KEY_ID,
                    "razorpay_amount": amount * 100,
                    "currency": currency,
                    "callback_url": callback_url,
                }
            )

    return render(request, "customer/customer-wallet.html", context)



@login_required
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
