"""
Email utility functions
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formataddr
import os

def send_otp_email(email, otp):
    """Send OTP email to user"""
    try:
        # Email configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = os.getenv('EMAIL_USER', 'your-email@gmail.com')
        sender_password = os.getenv('EMAIL_PASSWORD', 'your-app-password')
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = formataddr(("iRequest System", sender_email))
        msg['To'] = email
        msg['Subject'] = "Your OTP Code - iRequest"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Your OTP Code</h2>
            <p>Your One-Time Password (OTP) is: <strong>{otp}</strong></p>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def send_notification_email(email, subject, message):
    """Send notification email"""
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = os.getenv('EMAIL_USER', 'your-email@gmail.com')
        sender_password = os.getenv('EMAIL_PASSWORD', 'your-app-password')
        
        msg = MIMEMultipart()
        msg['From'] = formataddr(("iRequest System", sender_email))
        msg['To'] = email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'html'))
        
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"Notification email failed: {e}")
        return False
