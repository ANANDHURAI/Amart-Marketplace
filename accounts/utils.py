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

    secret_key = pyotp.random_base32()
    totp = pyotp.TOTP(secret_key, interval=60)
    otp = totp.now()

    valid_till = datetime.now() + timedelta(seconds=60)

    request.session.update({
        "otp_secret_key": secret_key,
        "otp_valid_till": valid_till.isoformat(),
    })

    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=email,
        subject="OTP Verification - Amart Fashions",
        plain_text_content=f"""
        Your OTP is: {otp}
        Valid for 60 seconds.
        """
    )

    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    sg.send(message)
    return True
