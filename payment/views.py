from django.shortcuts import render, redirect
import razorpay
from django.conf import settings
from customer.models import Order, Cart, CartItem, Wallet, OrderItem
from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.csrf import csrf_exempt
from accounts.models import Customer
from django.contrib import messages
from customer.views import create_order
from django.contrib.auth.decorators import login_required
import logging
from django.db import transaction

# Customer Payment Session

# RazorPay intergration

# Authorize razorpay client with API Key.

razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
)


@login_required
def razorpay_order_creation(request, amount):
    currency = "INR"
    amount = int(amount) * 100

    data = {"amount": amount, "currency": currency, "receipt": str(request.user.id)}
    razorpay_order = razorpay_client.order.create(data)

    razorpay_order_id = razorpay_order["id"]
    callback_url = reverse("razorpay_paymenthandler")
    context = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_merchant_key": settings.RAZOR_KEY_ID,
        "razorpay_amount": amount,
        "actual_amount": amount / 100,
        "currency": currency,
        "callback_url": callback_url,
    }

    return render(request, "customer/customer-payment.html", context=context)


logger = logging.getLogger(__name__)



@csrf_exempt
@login_required
def razorpay_paymenthandler(request):
    if request.method != "POST":
        return HttpResponseBadRequest()

    try:
        payment_id = request.POST.get("razorpay_payment_id", "")
        razorpay_order_id = request.POST.get("razorpay_order_id", "")
        signature = request.POST.get("razorpay_signature", "")

        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }

        razorpay_client.utility.verify_payment_signature(params_dict)

        if request.session.get("pay_now"):
            order_id = request.session.get("order_id")
            order = Order.objects.get(id=order_id)
            order.is_paid = True
            order.payment_method = "razorpay"
            order.save()

            del request.session["pay_now"]
            del request.session["order_id"]

        request.session["payment_successful"] = True
        request.session["payment_method"] = "razorpay"

        return redirect("orders")

    except Exception as e:
        request.session["payment_successful"] = False
        return redirect("payment_failed")





@login_required
def cash_on_delivery(request):
    request.session["payment_method"] = "cod"
    request.session["payment_successful"] = True
    return redirect("finalize_order")



def handle_cod_payment(request, customer, total_amount):
    if total_amount > 1000:
        messages.error(request, "COD is not available for orders above 1000 Rs.")
    else:
        request.session["payment_successful"] = True
        request.session["payment_method"] = "cod"
        return redirect("finalize_order")
    return redirect("payment_failed")


@login_required
def pay_now(request, order_id):
    order = Order.objects.get(id=order_id)
    request.session["pay_now"] = "pay_now"
    request.session["order_id"] = order_id
    return redirect("razorpay_order_creation", amount=order.total_amount)


@login_required
def pay_now_update(request):
    try:
        order_id = request.session.get("order_id")
        order = Order.objects.get(id=order_id)
        order.is_paid = True
        order.payment_method = "razorpay"
        order.save()
        del request.session["pay_now"]
        del request.session["order_id"]
        return True
    except Exception as e:
        logger.error(f"Error in pay_now_update: {str(e)}")
        return False
    
    
@login_required
def razorpay_callback(request):
    if request.method == "GET":
        payment_id = request.GET.get("razorpay_payment_id", "")
        razorpay_order_id = request.GET.get("razorpay_order_id", "")
        signature = request.GET.get("razorpay_signature", "")
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }
        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
            order = razorpay_client.order.fetch(razorpay_order_id)
            amount = order["amount"] / 100
            customer = request.user.customer
            wallet = Wallet.objects.get(customer=customer)
            wallet.balance += amount
            wallet.save()

            messages.success(request, f"Successfully added ₹{amount} to your wallet!")
        except:
            messages.error(request, "Payment verification failed. Please try again.")
    return redirect("customer_wallet")


def handle_wallet_payment(request, customer, total_amount):
    wallet = Wallet.objects.get(customer=customer)
    if wallet.balance >= total_amount:
        with transaction.atomic():
            wallet.balance -= total_amount
            wallet.save()
            request.session["payment_successful"] = True
            request.session["payment_method"] = "wallet"
        return redirect("finalize_order")
    else:
        messages.error(request, "Insufficient wallet balance.")
    return redirect("payment_failed")




@login_required
def payment_success(request):
    return render(request, "customer/customer-payment-success.html")


@login_required
def payment_failed(request):
    total_amount = request.session.get("total_amount")
    payment_method = request.session.get("payment_method")
    address_id = request.session.get("address_id")

    if not total_amount or not payment_method or not address_id:
        messages.error(request, "Invalid order data. Please try again.")
        return redirect("checkout")

    customer = request.user.customer
    wallet = Wallet.objects.get(customer=customer)

    context = {
        "total_amount": total_amount,
        "payment_method": payment_method,
        "wallet_balance": wallet.balance,
    }

    if request.method == "POST":
        retry_method = request.POST.get("retry_method")

        if retry_method == "razorpay":
            return redirect("razorpay_order_creation", amount=total_amount)
        elif retry_method == "wallet":
            return handle_wallet_payment(request, customer, total_amount)
        elif retry_method == "cod":
            return handle_cod_payment(request, customer, total_amount)
        else:
            messages.error(request, "Invalid payment method selected.")

    return render(request, "customer/payment_failed.html", context)



@login_required
def wallet_recharge_complete(request):
    if (
        request.session.get("payment_successful")
        and request.session.get("payment_method") == "razorpay"
    ):
        # Get the order details from Razorpay
        razorpay_order_id = request.session.get("razorpay_order_id")
        order = razorpay_client.order.fetch(razorpay_order_id)

        amount = order["amount"] / 100  # Convert back to rupees
        customer = request.user.customer
        customer.wallet.balance += amount
        customer.wallet.save()

        messages.success(request, f"Successfully added ₹{amount} to your wallet!")

        # Clear session variables
        del request.session["payment_successful"]
        del request.session["payment_method"]
        del request.session["razorpay_order_id"]

    return redirect("customer_wallet")


@login_required
def wallet_payment_complete(request):
    try:
        if request.session.get("payment_method") != "wallet":
            messages.error(
                request,
                "Wallet payment was not initiated. Please select a payment method.",
            )
            return redirect("checkout")

        total_amount = request.session.get("total_amount")
        if not total_amount:
            raise ValueError("Total amount not found in session")

        customer = request.user
        wallet = Wallet.objects.get(customer=customer)

        if wallet.balance >= total_amount:
            with transaction.atomic():
                wallet.balance -= total_amount
                wallet.save()
                request.session["payment_successful"] = True
            return redirect("finalize_order")
        else:
            messages.error(request, "Insufficient wallet balance.")
            return redirect("checkout")
    except Exception as e:
        logger.error(f"Wallet payment error: {str(e)}")
        messages.error(request, f"An error occurred during wallet payment: {str(e)}")
        return redirect("checkout")


