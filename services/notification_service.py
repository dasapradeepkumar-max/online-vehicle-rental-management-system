import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import os


def send_booking_confirmation(booking, user, vehicle):
    """Send booking confirmation email to the user."""
    smtp_user = current_app.config.get('SMTP_USER') or os.getenv('SMTP_USER')
    smtp_pass = current_app.config.get('SMTP_PASS') or os.getenv('SMTP_PASS')
    smtp_host = current_app.config.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(current_app.config.get('SMTP_PORT', 587))

    if not smtp_user or not smtp_pass:
        print(f'[DEMO] Booking #{booking.id} confirmed for {user.email} — {vehicle.name} '
              f'{booking.start_date} → {booking.end_date} ₹{booking.total_price}')
        return True

    try:
        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: 'Segoe UI', sans-serif; background:#f8fafc; margin:0; padding:0;">
          <div style="max-width:520px; margin:30px auto; background:white; border-radius:16px;
               box-shadow:0 4px 20px rgba(0,0,0,0.1); overflow:hidden;">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2); padding:30px; text-align:center;">
              <h1 style="color:white; margin:0; font-size:24px;">🚗 VehicleHub</h1>
              <p style="color:rgba(255,255,255,0.85); margin:8px 0 0;">Booking Confirmed!</p>
            </div>
            <div style="padding:32px;">
              <p style="color:#334155; font-size:16px;">Hi <strong>{user.full_name}</strong>,</p>
              <p style="color:#64748b;">Your vehicle booking has been confirmed. Here are the details:</p>
              <div style="background:#f1f5f9; border-radius:12px; padding:20px; margin:20px 0;">
                <table style="width:100%; border-collapse:collapse;">
                  <tr><td style="color:#64748b; padding:6px 0;">Vehicle</td>
                      <td style="color:#0f172a; font-weight:600; text-align:right;">{vehicle.name}</td></tr>
                  <tr><td style="color:#64748b; padding:6px 0;">Type</td>
                      <td style="color:#0f172a; font-weight:600; text-align:right;">{vehicle.type.capitalize()}</td></tr>
                  <tr><td style="color:#64748b; padding:6px 0;">Start Date</td>
                      <td style="color:#0f172a; font-weight:600; text-align:right;">{booking.start_date}</td></tr>
                  <tr><td style="color:#64748b; padding:6px 0;">End Date</td>
                      <td style="color:#0f172a; font-weight:600; text-align:right;">{booking.end_date}</td></tr>
                  <tr><td style="color:#64748b; padding:6px 0;">Total Amount</td>
                      <td style="color:#7c3aed; font-weight:700; font-size:18px; text-align:right;">
                          ₹{booking.total_price:,.0f}</td></tr>
                </table>
              </div>
              <p style="color:#64748b; font-size:14px;">
                Booking ID: <strong>#{booking.id}</strong><br>
                Thank you for choosing VehicleHub!
              </p>
            </div>
            <div style="background:#f8fafc; padding:16px; text-align:center; color:#94a3b8; font-size:13px;">
              © 2026 VehicleHub. All rights reserved.
            </div>
          </div>
        </body>
        </html>
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'✅ Booking Confirmed — {vehicle.name} | VehicleHub'
        msg['From'] = smtp_user
        msg['To'] = user.email
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        print(f'[SUCCESS] Booking confirmation email sent to {user.email}')
        return True
    except Exception as e:
        print(f'[ERROR] send_booking_confirmation: {e}')
        return False


def notify_admin_new_booking(booking, customer, vehicle):
    """Notify admin via email about new booking."""
    smtp_user = current_app.config.get('SMTP_USER') or os.getenv('SMTP_USER')
    smtp_pass = current_app.config.get('SMTP_PASS') or os.getenv('SMTP_PASS')
    admin_email = smtp_user  # Notify same address in demo setup

    if not smtp_user or not smtp_pass:
        print(f'[DEMO] Admin alert: New booking #{booking.id} by {customer.full_name} '
              f'for {vehicle.name}')
        return True

    try:
        html = f"""
        <html><body style="font-family:Arial,sans-serif;">
          <h2>🔔 New Booking Alert</h2>
          <p><strong>Customer:</strong> {customer.full_name} ({customer.email})</p>
          <p><strong>Vehicle:</strong> {vehicle.name}</p>
          <p><strong>Dates:</strong> {booking.start_date} → {booking.end_date}</p>
          <p><strong>Amount:</strong> ₹{booking.total_price:,.0f}</p>
          <p><strong>Booking ID:</strong> #{booking.id}</p>
        </body></html>
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🔔 New Booking #{booking.id} — VehicleHub Admin'
        msg['From'] = smtp_user
        msg['To'] = admin_email
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(current_app.config.get('SMTP_HOST', 'smtp.gmail.com'),
                          int(current_app.config.get('SMTP_PORT', 587))) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f'[ERROR] notify_admin_new_booking: {e}')
        return False
