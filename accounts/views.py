"""Account app views: customer signup/login, admin login, and OTP activation."""

import re
from datetime import datetime

import pyotp
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render

from .models import Account, Customer
from .utils import send_otp


def _normalize_email(email: str) -> str:
    """Return a trimmed, lowercased email string."""
    return (email or "").strip().lower()


def customer_signup(request):
    """Customer registration: validate inputs then start OTP flow."""
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip().title()
        last_name = request.POST.get("last_name", "").strip().title()
        email = _normalize_email(request.POST.get("email", ""))
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        if not all([first_name, last_name, email, password, password2]):
            messages.error(request, "All fields are required")
            return redirect("customer_signup")

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Enter a valid email address")
            return redirect("customer_signup")

        name_regex = r"^[A-Za-z ]+$"
        if not re.match(name_regex, first_name):
            messages.error(request, "First name should contain only letters")
            return redirect("customer_signup")

        if not re.match(name_regex, last_name):
            messages.error(request, "Last name should contain only letters")
            return redirect("customer_signup")

        if password != password2:
            messages.error(request, "Passwords do not match")
            return redirect("customer_signup")

        if not re.match(r"^(?=.*\d).{8,}$", password or ""):
            messages.error(
                request,
                "Password must be at least 8 characters and contain a number",
            )
            return redirect("customer_signup")

        if Account.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("customer_signup")


        request.session["signup_data"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": password,
        }

        request.session["email"] = email

        messages.success(request, "OTP sent to your email")
        return redirect("otp_view")

    return render(request, "accounts/customer-signup.html")





def customer_login(request):
    """Customer login with basic account checks."""
    if request.method == "POST":
        email = _normalize_email(request.POST.get("email", ""))
        password = request.POST.get("password")

        if not email or not password:
            messages.error(request, "Email and password are required")
            return redirect("customer_login")

        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            messages.error(request, "Account not found. Please check your email.")
            return redirect("customer_login")

        if not customer.is_active:
            messages.error(request, "Your account is currently blocked. Please contact support.")
            return redirect("customer_login")


       
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
    """Log out a customer."""
    logout(request)
    return redirect("home")




def admin_login(request):
    """Admin login restricted to superadmin accounts."""
    if request.method == "POST":
        email = _normalize_email(request.POST.get("email", ""))
        password = request.POST.get("password")

        if not email:
            messages.error(request, "Email is required.")
            return redirect("admin_login")

        if not password:
            messages.error(request, "Password is required.")
            return redirect("admin_login")

        try:
            admin = Account.objects.get(email=email)
        except Account.DoesNotExist:
            messages.error(request, "Email does not exist.")
            return redirect("admin_login")

        if not admin.is_superadmin:
            messages.error(request, "Access denied.")
            return redirect("admin_login")

        if not admin.is_active:
            messages.error(request, "Admin account is blocked.")
            return redirect("admin_login")

        
        if not admin.check_password(password):
            messages.error(request, "Incorrect password.")
            return redirect("admin_login")

        login(request, admin)
        return redirect("admin_dashboard")

    return render(request, "aadmin/admin-login.html")







def admin_logout(request):
    """Log out an admin user."""
    logout(request)
    return redirect("admin_login")





def otp_view(request):
    """Send OTP and redirect to activation page."""
    if not request.session.get("email"):
        messages.error(request, "Session expired")
        return redirect("customer_signup")

    send_otp(request)
    return redirect("customer_activation")






def customer_activation(request):
    """Verify OTP and activate the customer account."""
    signup_data = request.session.get("signup_data")
    secret_key = request.session.get("otp_secret_key")
    valid_till = request.session.get("otp_valid_till")


    if not all([signup_data, secret_key, valid_till]):
        messages.error(request, "Session expired. Please register again.")
        return redirect("customer_signup")

    valid_till_dt = datetime.fromisoformat(valid_till)

  
    time_left = max(0, int((valid_till_dt - datetime.now()).total_seconds()))

    if request.method == "POST":
        otp = request.POST.get("otp", "").strip()

        if datetime.now() > valid_till_dt:
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect("customer_activation")


        totp = pyotp.TOTP(secret_key, interval=60)

        if not totp.verify(otp):
            messages.error(request, "Invalid OTP. Please enter the correct code.")
            return redirect("customer_activation")

        customer = Customer.objects.create_user(
            first_name=signup_data["first_name"],
            last_name=signup_data["last_name"],
            email=signup_data["email"],
            password=signup_data["password"],
        )
        customer.is_customer = True
        customer.is_active = True
        customer.save()

        for key in ["signup_data", "otp_secret_key", "otp_valid_till", "email"]:
            request.session.pop(key, None)

        messages.success(request, "Account verified successfully. Please login.")
        return redirect("customer_login")

    return render(request, "accounts/customer-activation.html", {
        "time_left": time_left
    })







def resend_otp(request):
    """Resend OTP with basic rate limiting and expiry checks."""
    email = request.session.get("email")
    otp_valid_till = request.session.get("otp_valid_till")
    resend_count = request.session.get("otp_resend_count", 0)

    if not email or not otp_valid_till:
        messages.error(request, "Session expired. Please signup again")
        return redirect("customer_signup")

    if resend_count >= 3:
        messages.error(request, "Maximum OTP resend attempts reached. Please try later")
        return redirect("customer_signup")

    otp_valid_till_dt = datetime.fromisoformat(otp_valid_till)


    if datetime.now() < otp_valid_till_dt:
        messages.error(request, "Please wait until OTP expires before resending")
        return redirect("customer_activation")


    send_otp(request)

    request.session["otp_resend_count"] = resend_count + 1

    messages.success(request, "New OTP sent to your email")
    return redirect("customer_activation")

