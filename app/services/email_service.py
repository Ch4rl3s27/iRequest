"""
Email service for sending notifications
"""

import smtplib
import ssl
import random
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formataddr
from flask import current_app
from app.utils.exceptions import EmailError


class EmailService:
    """Email service class"""
    
    @staticmethod
    def send_otp_email(to_email: str, full_name: str, otp: str, purpose: str = "verification") -> bool:
        """
        Send OTP email
        
        Args:
            to_email: Recipient email
            full_name: Recipient full name
            otp: OTP code
            purpose: Purpose of OTP
            
        Returns:
            True if sent successfully
        """
        try:
            subject = f"iRequest {purpose.title()} Code"
            html_content = EmailService._create_otp_email_template(full_name, otp, purpose)
            
            return EmailService._send_email_html(to_email, subject, html_content)
            
        except Exception as e:
            raise EmailError(f"Failed to send OTP email: {str(e)}")
    
    @staticmethod
    def send_notification_email(to_email: str, subject: str, message: str) -> bool:
        """
        Send notification email
        
        Args:
            to_email: Recipient email
            subject: Email subject
            message: Email message
            
        Returns:
            True if sent successfully
        """
        try:
            return EmailService._send_email_html(to_email, subject, message)
        except Exception as e:
            raise EmailError(f"Failed to send notification email: {str(e)}")
    
    @staticmethod
    def _create_otp_email_template(full_name: str, otp: str, purpose: str = "verification") -> str:
        """Create OTP email template"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>iRequest {purpose.title()}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">iRequest {purpose.title()}</h2>
                <p>Hello {full_name},</p>
                <p>Your {purpose} code is:</p>
                <div style="background-color: #f3f4f6; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #2563eb; font-size: 32px; margin: 0;">{otp}</h1>
                </div>
                <p>This code will expire in 10 minutes.</p>
                <p>If you didn't request this, please ignore this email.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 14px;">
                    This is an automated message from iRequest system.
                </p>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def _send_email_html(to_email: str, subject: str, html_content: str) -> bool:
        """Send HTML email"""
        try:
            # Get email configuration
            mail_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            mail_port = current_app.config.get('MAIL_PORT', 587)
            mail_username = current_app.config.get('MAIL_USERNAME')
            mail_password = current_app.config.get('MAIL_PASSWORD')
            
            if not all([mail_username, mail_password]):
                raise EmailError("Email configuration not found")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr(("iRequest System", mail_username))
            msg['To'] = to_email
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(mail_server, mail_port) as server:
                server.starttls(context=context)
                server.login(mail_username, mail_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            raise EmailError(f"Failed to send email: {str(e)}")
    
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP"""
        return str(random.randint(100000, 999999))
