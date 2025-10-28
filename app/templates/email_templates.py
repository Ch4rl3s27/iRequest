def get_otp_email_template(full_name: str, otp: str, purpose: str = "verification") -> str:
    """
    Creates a responsive HTML email template with embedded logo for OTP emails.
    Compatible with Gmail, Outlook, Yahoo, and other major email clients.
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>OTP Verification</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; background-color: #f4f6fa; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f6fa;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); overflow: hidden;">
                    <tr>
                        <td align="center" style="padding: 30px 20px 20px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                            <img src="cid:nclogo" alt="Norzagaray College Logo" width="100" height="100" style="display: block; border: 0; border-radius: 50%; background-color: white; padding: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.2);">
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px 40px;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="padding-bottom: 20px;">
                                        <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #2c3e50; text-align: center; line-height: 1.3;">
                                            Hello, {full_name}!
                                        </h1>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-bottom: 25px;">
                                        <p style="margin: 0; font-size: 16px; color: #555555; text-align: center; line-height: 1.5;">
                                            Your One-Time Password (OTP) for iRequest {purpose}:
                                        </p>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-bottom: 25px;">
                                        <div style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                                            <span style="font-size: 32px; font-weight: bold; color: #ffffff; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                                                {otp}
                                            </span>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-bottom: 25px;">
                                        <p style="margin: 0; font-size: 14px; color: #e74c3c; text-align: center; font-weight: 600;">
                                            ⏰ This OTP will expire in 10 minutes
                                        </p>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-bottom: 20px;">
                                        <div style="background-color: #f8f9fa; border-left: 4px solid #17a2b8; padding: 15px; border-radius: 5px;">
                                            <p style="margin: 0; font-size: 13px; color: #495057; line-height: 1.4;">
                                                <strong>Security Notice:</strong> If you didn't request this OTP, please ignore this email or contact support if you have concerns about your account security.
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px 40px 30px 40px; background-color: #f8f9fa; border-top: 1px solid #e9ecef;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center">
                                        <p style="margin: 0 0 10px 0; font-size: 16px; color: #2c3e50; font-weight: 600;">
                                            Best regards,<br>
                                            <span style="color: #667eea;">iRequest Team</span>
                                        </p>
                                        <p style="margin: 0; font-size: 12px; color: #6c757d;">
                                            © 2025 iRequest - Norzagaray College<br>
                                            This is an automated message, please do not reply.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
