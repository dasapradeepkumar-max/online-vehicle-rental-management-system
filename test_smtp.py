import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables if .env exists
load_dotenv()

def test_smtp_connection():
    # Configuration
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    
    print(f"Testing SMTP connection to {smtp_host}:{smtp_port}")
    print(f"User: {smtp_user}")
    
    if not smtp_user or not smtp_pass:
        print("ERROR: SMTP_USER and SMTP_PASS environment variables must be set.")
        return

    # Create a simple test email
    msg = MIMEMultipart()
    msg['From'] = str(smtp_user)
    msg['To'] = str(smtp_user)  # Send to self for testing
    msg['Subject'] = "VehicleHub SMTP Test"
    
    body = "This is a test email from your VehicleHub application to verify SMTP configuration."
    msg.attach(MIMEText(body, 'plain'))

    try:
        print("Connecting to server...")
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.set_debuglevel(1)  # Show detailed SMTP logs
        server.starttls()
        
        print("Logging in...")
        server.login(smtp_user, smtp_pass)
        
        print("Sending test email...")
        server.send_message(msg)
        server.quit()
        
        print("\nSUCCESS: SMTP connection and email delivery verified!")
    except Exception as e:
        print(f"\nFAILURE: SMTP test failed.")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_smtp_connection()
