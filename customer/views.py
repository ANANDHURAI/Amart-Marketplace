"""
Customer app views: dashboard, profile, addresses, cart, checkout, orders.

Access controlled by @customer_required. Query optimization: select_related /
prefetch_related to avoid N+1 in orders, cart, checkout, favourites, invoice.
"""
import logging
import re
import os
from PIL import Image
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.db import transaction
from django.db.models import F, Prefetch, Sum
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import razorpay
from accounts.models import Customer
from aadmin.models import CategoryOffer, Coupon, CustomerCoupon


from .models import Address, Cart, CartItem, Order, OrderItem, Wallet
from .utils import list_of_states_in_india

logger = logging.getLogger(__name__)


def _get_customer(request):
    """Return the Customer for the current request user or None if not a customer."""
    if not request.user.is_authenticated or not request.user.is_customer:
        return None
    return get_object_or_404(Customer, pk=request.user.pk)



def _get_customer_coupon_queryset(customer):
    """
    Coupons visible to this customer:
    - public coupons (no linked CustomerCoupon row)
    - coupons specifically issued to this customer
    """
    ineligible_ids = CustomerCoupon.objects.exclude(
        customer=customer
    ).values_list("coupon_ptr_id", flat=True)
    return Coupon.objects.exclude(id__in=ineligible_ids)


def _is_coupon_eligible_for_customer(coupon, customer):
    """Use this when a coupon was already fetched by code (preview/place_order)."""
    customer_coupon = getattr(coupon, "customercoupon", None)  # reverse OneToOne
    return customer_coupon is None or customer_coupon.customer_id == customer.id


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
    """Update customer profile with strong server-side validation."""

    if request.method != "POST":
        return redirect("customer-profile")

    customer = _get_customer(request)

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    mobile = request.POST.get("mobile", "").strip()
    profile_image = request.FILES.get("profile_image")

    errors = []

    if first_name:
        if len(first_name) < 2:
            errors.append("First name must contain at least 2 characters.")

        if len(first_name) > 50:
            errors.append("First name cannot exceed 50 characters.")

        if not re.fullmatch(r"[A-Za-z]+(?:[ '-][A-Za-z]+)*", first_name):
            errors.append(
                "First name can contain only letters, spaces, hyphens, or apostrophes."
            )


    if last_name:
        if len(last_name) < 2:
            errors.append("Last name must contain at least 2 characters.")

        if len(last_name) > 50:
            errors.append("Last name cannot exceed 50 characters.")

        if not re.fullmatch(r"[A-Za-z]+(?:[ '-][A-Za-z]+)*", last_name):
            errors.append(
                "Last name can contain only letters, spaces, hyphens, or apostrophes."
            )

            
    if mobile:

        if not re.fullmatch(r"[6-9]\d{9}", mobile):
            errors.append(
                "Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9."
            )
            
        elif len(set(mobile)) == 1:
            errors.append(
                "Please enter a valid mobile number."
            )


    if profile_image:
        max_size = 5 * 1024 * 1024

        if profile_image.size > max_size:
            errors.append("Profile image must be smaller than 5 MB.")

        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        extension = os.path.splitext(profile_image.name)[1].lower()

        if extension not in allowed_extensions:
            errors.append(
                "Only JPG, JPEG, PNG, and WEBP images are allowed."
            )

        try:
            image = Image.open(profile_image)
            image.verify()
        except Exception:
            errors.append("The uploaded profile image is invalid.")
        finally:
            profile_image.seek(0)
            
            
    if errors:
        for error in errors:
            messages.error(request, error)

        return redirect("customer-profile")

    
    if first_name:
        customer.first_name = first_name.title()

    if last_name:
        customer.last_name = last_name.title()

    customer.mobile = mobile or None

    if profile_image:
        customer.profile_image = profile_image

    customer.save()

    messages.success(
        request,
        "Profile updated successfully!"
    )

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

    if not name:
        errors.append("Please enter your full name.")
    elif not re.fullmatch(r"[A-Za-z]+(?:[\s-][A-Za-z]+)*", name):
        errors.append("Full name should contain only letters, spaces or hyphens (e.g. 'Ramesh Kumar').")

    if not mobile:
        errors.append("Please enter a mobile number.")
    elif not re.fullmatch(r"[6-9]\d{9}", mobile):
        errors.append("Enter a valid 10-digit Indian mobile number starting with 6-9.")

    if not pincode:
        errors.append("Please enter a pincode.")
    elif not re.fullmatch(r"[1-9]\d{5}", pincode):
        errors.append("Enter a valid 6-digit pincode.")

    if not building:
        errors.append("Please enter your building/apartment name.")
    elif len(building) < 3 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9,./#\- ]*", building):
        errors.append("Building/Apartment must be at least 3 characters (letters, numbers, ',./#-' allowed).")

    if not street:
        errors.append("Please enter your street/locality.")
    elif len(street) < 3 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9,./#\- ]*", street):
        errors.append("Street/Locality must be at least 3 characters (letters, numbers, ',./#-' allowed).")

    if city and not re.fullmatch(r"[A-Za-z]+(?:[\s-][A-Za-z]+)*", city):
        errors.append("City should contain only letters and spaces.")

    if not district:
        errors.append("Please enter your district.")
    elif not re.fullmatch(r"[A-Za-z]+(?:[\s-][A-Za-z]+)*", district):
        errors.append("District should contain only letters and spaces.")

    if not state:
        errors.append("Please select a state.")
    elif state not in list_of_states_in_india:
        errors.append("Please select a valid state from the list.")

    return errors





def _address_initial(address=None, form_data=None):
    """Build the field values to prefill the address form with."""
    fields = ["name", "pincode", "mobile", "building", "street", "city", "district", "state"]
    if form_data:
        return {f: form_data.get(f, "") for f in fields}
    if address:
        return {f: getattr(address, f) for f in fields}
    return {f: "" for f in fields}




@customer_required
def new_address(request):
    
    from product.views import _build_checkout_context
    if request.method == "POST":
        errors = validate_address_data(request.POST)

        if errors:
            for error in errors:
                messages.error(request, error, extra_tags="address")

            if "checkout_submit" in request.POST:
                
                context = _build_checkout_context(request)
                context["new_address_initial"] = _address_initial(form_data=request.POST)
                return render(request, "customer/checkout.html", context)

          
            return render(request, "customer/address_form.html", {
                "states": list_of_states_in_india,
                "initial": _address_initial(form_data=request.POST),
            })

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
            name, building, street,
            city if city else None,
            f"{district}, {state}",
            f"Pincode - {pincode}",
            f"Mobile: {mobile}",
        ]
        address_text = "\n".join(filter(None, address_parts))

        address = Address.objects.create(
            customer=customer, name=name, mobile=mobile, pincode=pincode,
            building=building, street=street, city=city,
            district=district, state=state, address_text=address_text,
        )

        if not Address.objects.filter(customer=customer).exclude(id=address.id).exists():
            address.is_default = True
            address.save()

        return redirect("checkout" if "checkout_submit" in request.POST else "customer-addresses")

    return render(request, "customer/address_form.html", {
        "states": list_of_states_in_india,
        "initial": _address_initial(),
    })





@customer_required
def edit_address(request, address_id):
    """Edit an address; address must belong to the current customer."""
    customer = _get_customer(request)
    address = get_object_or_404(Address, id=address_id, customer=customer)

    if request.method == "POST":
        errors = validate_address_data(request.POST)

        if errors:
            for error in errors:
                messages.error(request, error, extra_tags="address")
                
            return render(request, "customer/address_form.html", {
                "address": address,
                "states": list_of_states_in_india,
                "initial": _address_initial(form_data=request.POST),
            })

        name = request.POST["name"].strip().title()
        mobile = request.POST["mobile"].strip()
        pincode = request.POST["pincode"].strip()
        building = request.POST["building"].strip().title()
        street = request.POST["street"].strip().title()
        city = request.POST.get("city", "").strip().title()
        district = request.POST["district"].strip().title()
        state = request.POST["state"].strip()

        address_parts = [
            name, building, street,
            city if city else None,
            f"{district}, {state}",
            f"Pincode - {pincode}",
            f"Mobile: {mobile}",
        ]
        address_text = "\n".join(filter(None, address_parts))

        address.name = name
        address.mobile = mobile
        address.pincode = pincode
        address.building = building
        address.street = street
        address.city = city
        address.district = district
        address.state = state
        address.address_text = address_text
        address.save()

        return redirect("customer-addresses")

    return render(request, "customer/address_form.html", {
        "address": address,
        "states": list_of_states_in_india,
        "initial": _address_initial(address=address),
    })




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




from customer.models import ReturnRequest

@customer_required
def orders(request):
    """List all orders for the current customer with items and subtotals."""
    customer = _get_customer(request)

    order_items_qs = OrderItem.objects.select_related(
        "product", "inventory"
    ).prefetch_related(
        "product__product_images",
        Prefetch(
            "return_requests",
            queryset=ReturnRequest.objects.order_by("-requested_at"),
        ),
    )

    orders_qs = (
        Order.objects.filter(customer=customer)
        .prefetch_related(Prefetch("items", queryset=order_items_qs))
        .annotate(total_quantity=Sum("items__quantity"))
        .order_by("-created_at")
    )

    # Pagination
    paginator = Paginator(orders_qs, 5)
    page = request.GET.get("page")

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    for order in orders_page:
        order.order_items = list(order.items.all())

        order.sub_total = sum(
            oi.quantity * oi.inventory.price
            for oi in order.order_items
        )

        order.has_active_items = any(
            oi.status != "cancelled"
            for oi in order.order_items
        )

        for order_item in order.order_items:
            order_item.product.primary_image = (
                order_item.product.product_images
                .order_by("priority")
                .first()
            )

            
            order_item.rejected_note = None
            if order_item.status == "delivered":
                latest_return = order_item.return_requests.order_by("-requested_at").first()
                if latest_return and latest_return.status == "rejected":
                    order_item.rejected_note = latest_return.admin_note
                    
    return render(
        request,
        "customer/customer-orders.html",
        {
            "customer": customer,
            "orders": orders_page,
            "paginator": paginator,
        },
    )




from .models import WalletTransaction

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
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type="credit",
            source="order_cancel",
            amount=refund_amount,
            order=order,
            description=f"Refund for cancelled Order #{order.id}",
        )
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
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="credit",
                source="item_cancel",
                amount=refund,
                order=order,
                order_item=order_item,
                description=f"Refund for cancelled item in Order #{order.id}",
            )
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





from .models import ReturnRequest
@customer_required
def request_return(request, order_item_id):
    customer = _get_customer(request)
    order_item = get_object_or_404(
        OrderItem, id=order_item_id, order__customer=customer
    )

    if order_item.status != "delivered":
        messages.error(request, "Only delivered items can be returned.")
        return redirect("customer-orders")

    if order_item.return_requests.filter(status="requested").exists():
        messages.error(request, "A return request is already pending for this item.")
        return redirect("customer-orders")

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "Please provide a reason for the return.")
            return redirect("customer-orders")

        ReturnRequest.objects.create(
            order_item=order_item,
            customer=customer,
            reason=reason,
        )
        order_item.status = "return_requested"
        order_item.save()

        messages.success(request, "Return request submitted. We'll review it shortly.")

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
            coupon_discount = coupon.calculate_discount(amount_after_offers)
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

    transactions = wallet.transactions.select_related(
        "order",
        "order_item__product"
    ).all().order_by("-created_at")

    # Pagination
    paginator = Paginator(transactions, 5)
    page = request.GET.get("page")

    try:
        transactions_page = paginator.page(page)
    except PageNotAnInteger:
        transactions_page = paginator.page(1)
    except EmptyPage:
        transactions_page = paginator.page(paginator.num_pages)

    context = {
        "customer": customer,
        "wallet": wallet,
        "transactions": transactions_page,
        "paginator": paginator,
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

    return render(
        request,
        "customer/customer-wallet.html",
        context
    )



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
