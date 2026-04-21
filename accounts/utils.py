from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
import random
from datetime import timedelta
from django.utils.timezone import now
from django.conf import settings

# Updated send_otp utility with dynamic content
def send_otp(request, purpose="registration"):
    email = request.session.get("email")
    if not email:
        return False

    otp = str(random.randint(100000, 999999))
    valid_till = now() + timedelta(seconds=60)

    request.session.update({
        "otp_code": otp,
        "otp_valid_till": valid_till.isoformat(),
        "otp_purpose": purpose,  # registration or forgot_password
    })

    # Dynamic Email Content
    if purpose == "forgot_password":
        subject = "Reset Your Password - Amart Fashions"
        title_text = "Password Reset"
        msg_text = "We received a request to reset your password. Use the code below to proceed:"
    else:
        subject = "Verify Your Email - Amart Fashions"
        title_text = "Email Verification"
        msg_text = "Thank you for choosing Amart Fashions. Use the code below to verify your email:"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; background-color:#f4f4f7; font-family:Arial, sans-serif;">
        <table align="center" width="100%" style="max-width:600px; background:#ffffff; margin-top:30px; border-radius:10px; overflow:hidden; box-shadow:0 4px 10px rgba(0,0,0,0.05);">
            <tr>
                <td style="background-color:#111827; color:#ffffff; text-align:center; padding:20px;">
                    <h2 style="margin:0;">Amart Fashions</h2>
                </td>
            </tr>
            <tr>
                <td style="padding:30px; color:#333333;">
                    <h3 style="margin-top:0;">{title_text}</h3>
                    <p>Dear Customer,</p>
                    <p>{msg_text}</p>
                    <div style="text-align:center; margin:30px 0;">
                        <span style="display:inline-block; font-size:28px; letter-spacing:6px; font-weight:bold; background:#f3f4f6; padding:15px 25px; border-radius:8px; color:#111827;">
                            {otp}
                        </span>
                    </div>
                    <p>Valid for 60 seconds.</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    text_content = strip_tags(html_content)
    email_message = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()
    return True
