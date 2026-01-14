import pyotp
from datetime import datetime, timedelta
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from .models import Account


def send_otp(request):
    email = request.session.get("email")
    if not email:
        return False

    try:
        account = Account.objects.get(email=email)
    except Account.DoesNotExist:
        return False

    # Generate OTP
    secret_key = pyotp.random_base32()
    counter = 1
    hotp = pyotp.HOTP(secret_key)
    otp = hotp.at(counter).zfill(6)

    # OTP expiry (60 seconds)
    valid_till = datetime.now() + timedelta(seconds=60)

    # Store OTP in session
    request.session.update({
        "otp_secret_key": secret_key,
        "otp_counter": counter,
        "otp_valid_till": valid_till.isoformat(),
    })

    # SendGrid Email
    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=email,
        subject="OTP Verification - Amart Fashions",
        plain_text_content=f"""
Dear {account.first_name} {account.last_name},

Welcome to Amart Fashions!

Your OTP for email verification is:

{otp}

This OTP is valid for 60 seconds.
If you didn’t request this, please ignore this email.

Best regards,
Amart Fashions Team
"""
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
        return True
    except Exception as e:
        print("SendGrid Error:", e)
        return False
