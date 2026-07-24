import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from models import OTP, db, User
from flask import current_app
import os


def generate_otp(user):
    """
    Generate a 6-digit OTP and store in database
    OTP expires in 5 minutes
    """
    # Delete previous unused OTPs for this user
    OTP.query.filter_by(user_id=user.id, used=False).delete()
    db.session.commit()

    # Generate random 6-digit code
    code = f"{random.randint(0, 999999):06d}"
    
    # Create OTP record (expires in 5 minutes)
    otp = OTP(user_id=user.id, code=code, ttl=5)
    db.session.add(otp)
    db.session.commit()

    print(f"[SUCCESS] OTP generated for user {user.id}: {code} (expires at {otp.expires_at})")
    return code


def send_email_otp(user, code):
    """
    Send OTP via email with HTML template
    Fallback to console if SMTP is not configured
    """
    if not user.email:
        print(f"[WARNING] User {user.id} has no email address")
        return False

    # Get SMTP config
    smtp_host = current_app.config.get('SMTP_HOST', os.getenv('SMTP_HOST'))
    smtp_port = current_app.config.get('SMTP_PORT', os.getenv('SMTP_PORT', 587))
    smtp_user = current_app.config.get('SMTP_USER', os.getenv('SMTP_USER'))
    smtp_pass = current_app.config.get('SMTP_PASS', os.getenv('SMTP_PASS'))

    # If no SMTP config, just log to console
    if not all([smtp_host, smtp_user, smtp_pass]):
        print(f"[DEMO MODE] OTP for {user.email}: {code}")
        print("[INFO] SMTP not configured. Email not sent. Use OTP above for testing.")
        return True

    try:
        # Create HTML email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Poppins', Arial, sans-serif; background: #f8fafc; }}
                .container {{ background: white; margin: 20px auto; max-width: 500px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #2563eb, #1e40af); color: white; padding: 2rem; text-align: center; }}
                .content {{ padding: 2rem; }}
                .otp-box {{ background: #f1f5f9; border: 2px solid #2563eb; padding: 1rem; text-align: center; border-radius: 8px; margin: 1.5rem 0; }}
                .otp-code {{ font-size: 2rem; font-weight: 800; color: #2563eb; letter-spacing: 4px; }}
                .timer {{ color: #64748b; font-size: 0.9rem; margin-top: 1rem; }}
                .footer {{ background: #f8fafc; padding: 1rem; text-align: center; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 0.85rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>VehicleHub</h1>
                    <p>Secure Login Verification</p>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>You requested to log in to your VehicleHub account. Use the code below to verify your identity:</p>
                    <div class="otp-box">
                        <div class="otp-code">{code}</div>
                        <div class="timer">⏱ Expires in 5 minutes</div>
                    </div>
                    <p style="color: #64748b; font-size: 0.9rem;">
                        <strong>Important:</strong> Never share this code with anyone. VehicleHub support will never ask for your OTP.
                    </p>
                    <p style="color: #64748b; font-size: 0.9rem;">
                        If you didn't request this code, please ignore this email.
                    </p>
                </div>
                <div class="footer">
                    <p>© 2026 VehicleHub. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Your OTP Code: {code}'
        msg['From'] = smtp_user
        msg['To'] = user.email

        # Attach HTML
        part = MIMEText(html_content, 'html')
        msg.attach(part)

        # Send email
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        print(f"[SUCCESS] OTP email sent to {user.email}")
        return True

    except smtplib.SMTPAuthenticationError:
        print(f"[ERROR] SMTP authentication failed for {smtp_user}. Please check your App Password.")
        print(f"[DEMO] Fallback OTP for {user.email}: {code}")
        return True  # Continue with demo mode for development

    except Exception as e:
        print(f"[ERROR] Failed to send email to {user.email}: {type(e).__name__}: {e}")
        print(f"[DEMO] Fallback OTP for {user.email}: {code}")
        return True  # Continue with demo mode for development


def verify_otp(user, code):
    """
    Verify OTP code for user
    - Check if code exists
    - Check if not already used
    - Check if not expired
    """
    if not code:
        return False

    # Find OTP
    otp = OTP.query.filter_by(user_id=user.id, code=code).first()

    if not otp:
        print(f"[WARNING] Invalid OTP for user {user.id}")
        return False

    # Check if already used
    if otp.used:
        print(f"[WARNING] OTP already used for user {user.id}")
        return False

    # Check if valid (not expired)
    if not otp.is_valid():
        print(f"[WARNING] OTP expired for user {user.id}")
        return False

    # Mark as used
    otp.used = True
    db.session.commit()

    print(f"[SUCCESS] OTP verified for user {user.id}")
    return True


def send_sms_otp(user, code):
    """
    Send OTP via SMS (Twilio)
    Optional - for future implementation
    """
    if not user.phone:
        print(f"[WARNING] User {user.id} has no phone number")
        return False

    # TODO: Implement Twilio SMS sending
    print(f"[DEMO] SMS OTP for {user.phone}: {code}")
    return True

