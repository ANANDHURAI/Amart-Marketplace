"""
Customer app views: dashboard, profile, addresses, cart, checkout, orders.

Access controlled by @customer_required. Query optimization: select_related /
prefetch_related to avoid N+1 in orders, cart, checkout, favourites, invoice.
"""
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
from accounts.models import Customer
from aadmin.models import CategoryOffer, Coupon


from .models import Address, Cart, CartItem, Order, OrderItem, Wallet
from .utils import list_of_states_in_india

logger = logging.getLogger(__name__)


def _get_customer(request):
    """Return the Customer for the current request user or None if not a customer."""
    if not request.user.is_authenticated or not request.user.is_customer:
        return None
    return get_object_or_404(Customer, pk=request.user.pk)


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
    """List addresses for the current customer."""
    customer = _get_customer(request)
    addresses = Address.objects.filter(customer=customer)
    return render(request, "customer/customer-address.html", {
        "customer": customer,
        "addresses": addresses,
    })


@customer_required
def profile(request):
    """Display customer profile."""
    customer = _get_customer(request)
    return render(request, "customer/customer-profile.html", {"customer": customer})




@customer_required
def edit_profile(request):
    """Update customer profile (name, mobile, profile image)."""
    if request.method == "POST":
        customer = _get_customer(request)
        customer.first_name = request.POST.get("first_name").title()
        customer.last_name = request.POST.get("last_name").title()
        customer.mobile = request.POST.get("mobile")

        profile_image = request.FILES.get("profile_image")
        if profile_image:
            customer.profile_image = profile_image

        customer.save()
        messages.success(request, "Profile updated successfully!")

    return redirect("customer-profile")




@customer_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        customer = _get_customer(request)

        if not customer.check_password(current_password):
            error_message = "The current password you entered is incorrect."
            messages.error(request, error_message)
            return redirect("change-password")

        if password1 != password2:
            error_message = "The new passwords do not match. Please try again."
            messages.error(request, error_message)
            return redirect("change-password")

        customer.set_password(password1)
        customer.save()
        logout(request)
        success_message = "Your password has been successfully changed. Please Login"
        messages.success(request, success_message)
        return redirect("customer-profile")

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
            return redirect("new-address")

        name = request.POST["name"].strip().title()
        mobile = request.POST["mobile"].strip()
        pincode = request.POST["pincode"].strip()
        building = request.POST["building"].strip().title()
        street = request.POST["street"].strip().title()
        city = request.POST.get("city", "").strip().title()
        district = request.POST["district"].strip().title()
        state = request.POST["state"].strip()

        customer = _get_customer(request)

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

        return redirect("checkout" if "checkout_submit" in request.POST else "customer-addresses")

    return render(request, "customer/address_form.html", {
        "states": list_of_states_in_india
    })




@customer_required
def edit_address(request, address_id):
    """Edit an address; address must belong to the current customer."""
    customer = _get_customer(request)
    address = get_object_or_404(Address, id=address_id, customer=customer)
    if request.method == "POST":
        name = request.POST.get("name").title()
        pincode = int(request.POST.get("pincode"))
        mobile = int(request.POST.get("mobile"))
        building = request.POST.get("building").title()
        street = request.POST.get("street").title()
        city = request.POST.get("city").title()
        district = request.POST.get("district").title()
        state = request.POST.get("state").title()
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

        return redirect("customer-addresses")

    context = {"address": address, "states": list_of_states_in_india}
    return render(request, "customer/address_form.html", context)





@customer_required
def remove_address(request, address_id):
    """Delete an address; address must belong to the current customer."""
    customer = _get_customer(request)
    address = get_object_or_404(Address, id=address_id, customer=customer)
    address.delete()
    return redirect("customer-addresses")




@customer_required
def default_address(request, address_id):
    """Set an address as default; address must belong to the current customer."""
    customer = _get_customer(request)
    address = get_object_or_404(Address, id=address_id, customer=customer)
    Address.objects.filter(customer=customer, is_default=True).update(is_default=False)
    address.is_default = True
    address.save()
    return redirect("customer-addresses")





@customer_required
def orders(request):
    """List all orders for the current customer with items and subtotals."""
    customer = _get_customer(request)
    order_items_qs = OrderItem.objects.select_related(
        "product", "inventory"
    ).prefetch_related("product__product_images")
    orders_qs = (
        Order.objects.filter(customer=customer)
        .prefetch_related(Prefetch("items", queryset=order_items_qs))
        .annotate(total_quantity=Sum("items__quantity"))
        .order_by("-created_at")
    )

    for order in orders_qs:
        order.order_items = list(order.items.all())
        order.sub_total = sum(
            oi.quantity * oi.inventory.price for oi in order.order_items
        )
        order.has_active_items = any(
            oi.status != "cancelled" for oi in order.order_items
        )
        for order_item in order.order_items:
            order_item.product.primary_image = (
                order_item.product.product_images.order_by("priority").first()
            )

    return render(request, "customer/customer-orders.html", {
        "customer": customer,
        "orders": orders_qs,
    })




@customer_required
@transaction.atomic
def cancel_order(request, order_id):
    customer   = _get_customer(request)
    order      = get_object_or_404(Order, id=order_id, customer=customer)
    order_items = OrderItem.objects.select_related("inventory").filter(order=order)
    wallet, _  = Wallet.objects.get_or_create(customer=customer)

    refund_amount = 0
    for order_item in order_items:
        if order_item.status != "cancelled":
            if order.is_paid and order.payment_method.lower() != "cod":
                refund_amount += _proportional_refund(order, order_item)

            order_item.status = "cancelled"
            order_item.inventory.stock += order_item.quantity
            order_item.inventory.save()
            order_item.save()

    order.status = "cancelled"
    order.save()

    if refund_amount > 0:
        wallet.balance += refund_amount
        wallet.save()
        messages.success(
            request,
            f"Order cancelled. Refund of ₹{refund_amount} added to your wallet."
        )
    else:
        messages.success(request, "Order cancelled successfully.")

    return redirect("customer-orders")





@customer_required
def cancel_order_item(request, order_item_id):
    customer = _get_customer(request)
    order_item = get_object_or_404(
        OrderItem, id=order_item_id, order__customer=customer
    )
    order = order_item.order
    wallet, _ = Wallet.objects.get_or_create(customer=customer)

    if order_item.status != "cancelled":
        refund = 0

        if order.is_paid and order.payment_method.lower() != "cod":
            refund = _proportional_refund(order, order_item)

        order_item.status = "cancelled"
        order_item.inventory.stock += order_item.quantity
        order_item.inventory.save()
        order_item.save()

        if refund > 0:
            wallet.balance += refund
            wallet.save()
            messages.success(
                request,
                f"Item cancelled. Refund of ₹{refund} added to your wallet."
            )

        if not OrderItem.objects.filter(order=order).exclude(status="cancelled").exists():
            order.status = "cancelled"
            order.total_amount = 0
            order.save()

        else:
            remaining_items = OrderItem.objects.filter(
                order=order
            ).exclude(status="cancelled")

            new_total = sum(
                item.inventory.price * item.quantity
                for item in remaining_items
            )

            order.total_amount = new_total
            order.save()

    return redirect("customer-orders")





@customer_required
@transaction.atomic
def create_order(request):
    address_id      = request.session.get("address_id")
    payment_method  = request.session.get("payment_method")
    coupon_code     = request.session.get("coupon_code", "")
    coupon_discount = request.session.get("coupon_discount", 0)
    
    customer   = _get_customer(request)
    address    = get_object_or_404(Address, id=address_id, customer=customer)
    cart       = get_object_or_404(Cart, customer=customer)
    cart_items = CartItem.objects.select_related(
        "product__main_category", "inventory"
    ).filter(cart=cart)

    subtotal = sum(item.quantity * item.inventory.price for item in cart_items)

    total_offer = 0
    for item in cart_items:
        offer = CategoryOffer.objects.filter(
            category=item.product.main_category, is_active=True
        ).first()
        if offer:
            total_offer += round(
                item.quantity * item.inventory.price * offer.discount / 100
            )

    amount_after_offers = subtotal - total_offer

    coupon = None
    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code).first()
        if coupon:
            coupon_discount = min(coupon_discount, amount_after_offers)
        else:
            coupon_discount = 0

    final_amount = request.session.get("total_amount", 0)

    order = Order.objects.create(
        customer=customer,
        address=address.address_text,
        total_amount=final_amount,    
        offer=total_offer,           
        discount=coupon_discount,   
        coupon=coupon,
        payment_method=payment_method,
        is_paid=request.session.get("payment_successful", False),
    )

    if coupon:
        coupon.quantity = max(coupon.quantity - 1, 0)
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





def _proportional_refund(order, order_item):

    all_items = OrderItem.objects.filter(order=order).select_related("inventory")
    order_subtotal = sum(oi.quantity * oi.inventory.price for oi in all_items)

    if order_subtotal == 0:
        return 0

    item_subtotal = order_item.quantity * order_item.inventory.price
    return round(item_subtotal / order_subtotal * order.total_amount)



@customer_required
def order_confirmation(request, order_id):
    """Redirect to payment success after order confirmation."""
    customer = _get_customer(request)
    order = get_object_or_404(Order, id=order_id, customer=customer)
    messages.success(request, f"Your order #{order.id} has been placed successfully!")
    return HttpResponseRedirect(reverse("payment_success"))


razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
)




@customer_required
def customer_wallet(request):
    customer = _get_customer(request)
    wallet, _ = Wallet.objects.get_or_create(customer=customer)

    order_items_qs = (
        OrderItem.objects.filter(
            order__customer=customer,
            status="cancelled",
            order__is_paid=True,
        )
        .exclude(order__payment_method__iexact="cod")
        .select_related("order", "product", "inventory")
        .order_by("-id")
    )

    from collections import defaultdict

    order_ids = list({oi.order_id for oi in order_items_qs})

    all_items_in_orders = (
        OrderItem.objects
        .filter(order_id__in=order_ids)
        .select_related("inventory")
    )
    order_subtotals = defaultdict(int)
    for item in all_items_in_orders:
        order_subtotals[item.order_id] += item.quantity * item.inventory.price

    for oi in order_items_qs:
        subtotal = order_subtotals[oi.order_id]
        if subtotal > 0:
            item_subtotal = oi.quantity * oi.inventory.price
            oi.actual_refund = round(item_subtotal / subtotal * oi.order.total_amount)
        else:
            oi.actual_refund = 0

    context = {
        "customer": customer,
        "wallet": wallet,
        "order_items": order_items_qs,
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
    """Invoice for an order; order must belong to the current customer."""
    customer = _get_customer(request)
    order = get_object_or_404(Order, id=order_id, customer=customer)
    order_items = (
        OrderItem.objects.filter(order=order)
        .select_related("product", "inventory")
        .prefetch_related("product__product_images")
    )
    order.order_items = list(order_items)
    order.sub_total = 0
    for oi in order.order_items:
        oi.product.primary_image = (
            oi.product.product_images.order_by("priority").first()
        )
        order.sub_total += oi.quantity * oi.inventory.price

    return render(request, "customer/invoice.html", {"order": order})
