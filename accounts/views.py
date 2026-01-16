from django.shortcuts import render, redirect
from .models import Customer, Account
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .utils import send_otp, pyotp
from datetime import datetime
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re


def customer_signup(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip().title()
        last_name = request.POST.get("last_name", "").strip().title()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        # Basic empty validation
        if not all([first_name, last_name, email, password, password2]):
            messages.error(request, "All fields are required")
            return redirect("customer_signup")

    
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Enter a valid email address")
            return redirect("customer_signup")

        #  Password match
        
        name_regex = r'^[A-Za-z ]+$'

        if not re.match(name_regex, first_name):
            messages.error(request, "First name should contain only letters")
            return redirect("customer_signup")

        if not re.match(name_regex, last_name):
            messages.error(request, "Last name should contain only letters")
            return redirect("customer_signup")

        if password != password2:
            messages.error(request, "Passwords do not match")
            return redirect("customer_signup")

        #  Strong password (min 8 chars, 1 number)
        if not re.match(r"^(?=.*\d).{8,}$", password):
            messages.error(
                request,
                "Password must be at least 8 characters and contain a number",
            )
            return redirect("customer_signup")

        #  Email existence
        if Account.objects.filter(email=email).exists():
            messages.error(
                request,
                "Email already registered. Please login or use another email",
            )
            return redirect("customer_signup")

        #  Create customer
        customer = Customer.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
        )
        customer.is_customer = True
        customer.is_active = False
        customer.approved = True
        customer.save()

        #  OTP session setup
        request.session.update({
            "email": email,
            "target_page": "customer_login",
            "account_type": "customer",
        })

        messages.success(request, "OTP sent to your email for verification")
        return redirect("otp_view")

    return render(request, "accounts/customer-signup.html", {"title": "Signup"})





def customer_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")

        if not email or not password:
            messages.error(request, "Email and password are required")
            return redirect("customer_login")

        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            messages.error(request, "Account not found. Please check your email.")
            return redirect("customer_login")

        # Blocked / inactive
        if not customer.is_active:
            messages.error(request, "Your account is currently blocked. Please contact support.")
            return redirect("customer_login")

        # Not approved by admin
        if not customer.approved:
            messages.error(request, "Your account is pending approval.")
            return redirect("customer_login")

        # Admin trying customer login
        if customer.is_superadmin or customer.is_staff:
            messages.error(request, "Admin accounts cannot login here.")
            return redirect("customer_login")

        user = authenticate(request, email=email, password=password)
        if user is None:
            messages.error(request, "Invalid email or password.")
            return redirect("customer_login")

        login(request, user)
        return redirect("home")

    return render(request, "accounts/customer-login.html", {"title": "Login"})




def customer_logout(request):
    logout(request)
    return redirect("home")


# Custom admin Login and logout views


def admin_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")

        if not email or not password:
            messages.error(request, "Email and password are required")
            return redirect("admin_login")

        try:
            admin = Account.objects.get(email=email)
        except Account.DoesNotExist:
            messages.error(request, "Access denied.")
            return redirect("admin_login")

        if not admin.is_superadmin:
            messages.error(request, "Access denied.")
            return redirect("admin_login")

        if not admin.is_active:
            messages.error(request, "Admin account is blocked.")
            return redirect("admin_login")

        user = authenticate(request, email=email, password=password)
        if user is None:
            messages.error(request, "Invalid email or password.")
            return redirect("admin_login")

        login(request, user)
        return redirect("admin_dashboard")

    return render(request, "aadmin/admin-login.html")






def admin_logout(request):
    logout(request)
    return redirect("admin_login")


# Account activation views
def otp_view(request):
    if not request.session.get("email"):
        messages.error(request, "Session expired. Please signup again")
        return redirect("customer_signup")

    send_otp(request)
    return redirect("customer_activation")



from datetime import datetime
import pyotp


def customer_activation(request):
    email = request.session.get("email")
    otp_secret_key = request.session.get("otp_secret_key")
    otp_counter = request.session.get("otp_counter")
    otp_valid_till = request.session.get("otp_valid_till")

    if not all([email, otp_secret_key, otp_counter, otp_valid_till]):
        messages.error(request, "OTP session expired. Please resend OTP")
        return redirect("otp_view")

    otp_valid_till = datetime.fromisoformat(otp_valid_till)
    time_left = max(0, int((otp_valid_till - datetime.now()).total_seconds()))

    if request.method == "POST":
        otp = request.POST.get("otp", "").strip()

        if not otp.isdigit() or len(otp) != 6:
            messages.error(request, "Enter a valid 6-digit OTP")
            return redirect("customer_activation")

        if datetime.now() > otp_valid_till:
            messages.error(request, "OTP expired. Please resend OTP")
            return redirect("customer_activation")

        hotp = pyotp.HOTP(otp_secret_key)
        if not hotp.verify(otp, otp_counter):
            messages.error(request, "Invalid OTP")
            return redirect("customer_activation")

        # Activate account
        account = Account.objects.get(email=email)
        account.is_active = True
        account.save()

        # Clear OTP session
        for key in ["otp_secret_key", "otp_counter", "otp_valid_till"]:
            request.session.pop(key, None)

        messages.success(request, "Email verified successfully. Please login")
        return redirect(request.session.get("target_page", "customer_login"))

    return render(
        request,
        "accounts/customer-activation.html",
        {"time_left": time_left},
    )


def resend_otp(request):
    email = request.session.get("email")
    otp_valid_till = request.session.get("otp_valid_till")

    if not email or not otp_valid_till:
        messages.error(request, "Session expired. Please signup again")
        return redirect("customer_signup")

    otp_valid_till = datetime.fromisoformat(otp_valid_till)

    if datetime.now() < otp_valid_till:
        messages.error(request, "Please wait until OTP expires before resending")
        return redirect("customer_activation")

    send_otp(request)
    messages.success(request, "New OTP sent to your email")
    return redirect("customer_activation")
