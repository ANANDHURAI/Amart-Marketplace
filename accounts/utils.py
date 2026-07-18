import random
from datetime import timedelta
from django.utils.timezone import now
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_otp(request, purpose="registration"):
    email = request.session.get("email")
    if not email:
        return False

    otp = str(random.randint(100000, 999999))
    valid_till = now() + timedelta(seconds=60)

    request.session.update({
        "otp_code": otp,
        "otp_valid_till": valid_till.isoformat(),
        "otp_purpose": purpose,
    })

    # Dynamic Email Content
    if purpose == "forgot_password":
        subject = "Reset Your Password - Amart Fashions"
        title_text = "Password Reset"
        msg_text = (
            "We received a request to reset your password. "
            "Use the code below to proceed:"
        )
    else:
        subject = "Verify Your Email - Amart Fashions"
        title_text = "Email Verification"
        msg_text = (
            "Thank you for choosing Amart Fashions. "
            "Use the code below to verify your email:"
        )

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; background-color:#f4f4f7; font-family:Arial, sans-serif;">
        <table align="center" width="100%" style="max-width:600px; background:#ffffff; margin-top:30px; border-radius:10px; overflow:hidden;">
            <tr>
                <td style="background-color:#111827; color:#ffffff; text-align:center; padding:20px;">
                    <h2 style="margin:0;">Amart Fashions</h2>
                </td>
            </tr>
            <tr>
                <td style="padding:30px; color:#333333;">
                    <h3>{title_text}</h3>
                    <p>Dear Customer,</p>
                    <p>{msg_text}</p>

                    <div style="text-align:center; margin:30px 0;">
                        <span style="display:inline-block;
                                     font-size:28px;
                                     letter-spacing:6px;
                                     font-weight:bold;
                                     background:#f3f4f6;
                                     padding:15px 25px;
                                     border-radius:8px;
                                     color:#111827;">
                            {otp}
                        </span>
                    </div>

                    <p><strong>Valid for 60 seconds.</strong></p>

                    <p>If you didn't request this, you can safely ignore this email.</p>

                    <p>Regards,<br>Amart Fashions Team</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=email,
        subject=subject,
        html_content=html_content,
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
        return True
    except Exception as e:
        print(f"SendGrid Error: {e}")
        return False