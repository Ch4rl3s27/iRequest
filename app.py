import smtplib, random, ssl
try:
  import pymysql
  from pymysql.cursors import DictCursor
except ImportError:
  pymysql = None
  DictCursor = None
from flask import Flask, request, redirect, url_for, render_template_string, jsonify, session, render_template, send_from_directory
from flask_cors import CORS
try:
  from flask_mysqldb import MySQL
except ImportError:
  MySQL = None
from werkzeug.security import generate_password_hash, check_password_hash
import os
from typing import Any, cast, Optional, Tuple, Union

# AWS S3 Configuration
# AWS S3 Configuration - Read from environment (no hardcoded secrets)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'ap-southeast-2')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'irequest-receipts')

if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    raise RuntimeError("Missing AWS credentials in environment. Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY.")
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formataddr
from datetime import datetime, timedelta
import os
import base64
import json
import requests
import re
try:
  from PIL import Image
  import io
except ImportError:
  Image = None
  io = None
try:
  import jwt  # PyJWT
except ImportError:
  jwt = None
# SocketIO removed - chat feature disabled
try:
  import boto3
  from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
  boto3 = None
  ClientError = Exception  # Fallback to Exception when boto3 not available
  NoCredentialsError = Exception

# --- Payment verification helpers ---
# Network connectivity test for AI service
def _test_ai_connectivity():
  """Test if the AI service is reachable"""
  try:
    import socket
    import ssl
    
    # Test DNS resolution
    try:
      socket.gethostbyname('generativelanguage.googleapis.com')
    except socket.gaierror:
      return False, "Cannot resolve AI service domain name"
    
    # Test HTTPS connection
    try:
      context = ssl.create_default_context()
      with socket.create_connection(('generativelanguage.googleapis.com', 443), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname='generativelanguage.googleapis.com') as ssock:
          return True, "AI service is reachable"
    except (socket.timeout, ssl.SSLError, ConnectionRefusedError) as e:
      return False, f"Cannot connect to AI service: {str(e)}"
      
  except Exception as e:
    return False, f"Network test failed: {str(e)}"

# Manual extraction fallback when JSON parsing fails
def _manual_extract_from_text(text: str):
  """Manually extract data from malformed JSON text using regex"""
  import re as _re
  try:
    # Extract amount
    amount = None
    amount_match = _re.search(r'"amount":\s*"?([^",}]+)"?', text)
    if amount_match:
      amt_str = _re.sub(r'[^\d\.]', '', amount_match.group(1))
      try:
        amount = float(amt_str) if amt_str else None
      except:
        amount = None
    
    # Extract reference number
    ref = ''
    ref_match = _re.search(r'"reference_number":\s*"?([^",}]+)"?', text)
    if ref_match:
      ref = _re.sub(r'\D', '', ref_match.group(1))
    
    # Extract raw text
    raw_text = ''
    raw_match = _re.search(r'"raw_text":\s*"([^"]*)', text)
    if raw_match:
      raw_text = raw_match.group(1)
    
    # Extract confidence
    confidence = 0.0
    conf_match = _re.search(r'"confidence_score":\s*"?([^",}]+)"?', text)
    if conf_match:
      try:
        confidence = float(conf_match.group(1))
      except:
        confidence = 0.0
    
    print(f"DEBUG: Manual extraction - amount: {amount}, ref: {ref}, confidence: {confidence}")
    
    return {
      'amount': amount,
      'reference_number': ref,
      'confidence': confidence,
      'raw_text': raw_text,
    }
  except Exception as e:
    print(f"DEBUG: Manual extraction failed: {e}")
    return None

# Gemini-powered extractor (accurate reference number and amount)
def _extract_ref_amount_from_gemini_text(json_text: str):
  import json as _json
  try:
    text = json_text.strip()
    if text.startswith('```json'):
      text = text[7:]
    if text.endswith('```'):
      text = text[:-3]
    text = text.strip()
    
    # Try to parse the JSON as-is first
    try:
      data = _json.loads(text)
    except _json.JSONDecodeError as e:
      print(f"DEBUG: JSON parse error: {e}")
      print(f"DEBUG: Raw text: {text}")
      
      # Try to repair common JSON issues
      # 1. Missing closing brace
      if not text.endswith('"') and not text.endswith('}') and not text.endswith(']'):
        # Look for the last complete field and add missing closing brace
        if '"raw_text":' in text:
          # Find the last quote and add closing brace
          last_quote_pos = text.rfind('"')
          if last_quote_pos > 0:
            # Check if there's already a closing brace after the last quote
            after_quote = text[last_quote_pos + 1:].strip()
            if not after_quote.endswith('}'):
              text = text[:last_quote_pos + 1] + '"}'
        else:
          # If no raw_text field, try to add basic structure
          if text.count('{') > text.count('}'):
            text += '}'
      
      # 2. Try parsing the repaired JSON
      try:
        data = _json.loads(text)
        print(f"DEBUG: Successfully repaired JSON")
      except _json.JSONDecodeError:
        # 3. If still failing, try to extract data manually using regex
        print(f"DEBUG: JSON repair failed, attempting manual extraction")
        return _manual_extract_from_text(text)
        
  except Exception as e:
    print(f"DEBUG: Exception in JSON parsing: {e}")
    return None
  try:
    import re as _re
    # amount
    amount = None
    if data.get('amount') is not None:
      amt = _re.sub(r'[^\d\.]', '', str(data['amount']))
      try:
        amount = float(amt)
      except Exception:
        amount = None
    # reference number: digits only, prefer 13-digit, else 7-16
    raw_text = str(data.get('raw_text') or '')
    digits_only = _re.sub(r'\D', '', str(data.get('reference_number') or ''))
    ref = ''
    
    # First, try to use what AI specifically identified as reference_number
    if digits_only and 7 <= len(digits_only) <= 16:
      ref = digits_only
    else:
      # If AI didn't identify a specific reference number, look in raw text
      # Look for patterns that suggest reference numbers
      ref_patterns = [
        r'(?:REF|REFERENCE|NO\.|NUMBER)[\s#:]*(\d{7,16})',  # After REF/REFERENCE labels
        r'(?:ORIGINAL)[\s\S]*?(\d{7,16})',  # After ORIGINAL text
        r'(?:RECEIPT|TXN|TRANSACTION)[\s#:]*(\d{7,16})',  # After receipt/transaction labels
        r'\b(\d{7,16})\b'  # Any 7-16 digit number as fallback
      ]
      
      for pattern in ref_patterns:
        matches = _re.findall(pattern, raw_text, _re.IGNORECASE)
        if matches:
          # Take the first match from the most specific pattern
          ref = matches[0]
          break
    conf = float(data.get('confidence_score') or 0.0)
    return {
      'amount': amount,
      'reference_number': ref,
      'confidence': conf,
      'raw_text': raw_text,
    }
  except Exception:
    return None

def _gemini_extract(image_b64: str, retry_count=0):
  try:
    # Get API key from Flask app config
    from flask import current_app
    api_key = current_app.config.get('GEMINI_API_KEY')
    
    if not api_key:
      return {'ok': False, 'message': 'GEMINI_API_KEY not configured. Please set your Gemini API key in the app configuration.'}
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    prompt = (
      "You are an expert at analyzing Philippine payment receipts, especially GCash and government receipts. Return ONLY valid JSON with these fields:\n"
      "{\n"
      "  \"amount\": \"number only, e.g. 50.00\",\n"
      "  \"reference_number\": \"digits only, prefer 13-digit; else 7-16 digits\",\n"
      "  \"raw_text\": \"all text you can read\",\n"
      "  \"confidence_score\": \"0.0 to 1.0\"\n"
      "}\n"
      "CRITICAL: For reference_number, focus on these specific locations in Philippine receipts:\n"
      "1. BELOW 'ORIGINAL' text - This is the MOST COMMON location for reference numbers in Philippine receipts\n"
      "2. Look for numbers that appear directly under or near 'ORIGINAL' text\n"
      "3. Check for numbers in red ink or highlighted areas\n"
      "4. Look for transaction numbers, receipt numbers, or confirmation numbers\n"
      "5. Numbers that look like: 6219902, 1234567890123, etc.\n"
      "\n"
      "Rules:\n"
      "- Strip all currency symbols and commas from amount.\n"
      "- For reference_number: DIGITS ONLY. Accept 7-16 digit sequences.\n"
      "- PRIORITIZE numbers found below 'ORIGINAL' text\n"
      "- Look for numbers that appear to be receipt/reference/transaction IDs\n"
      "- If multiple numbers found, prefer the one below 'ORIGINAL' or the longest sequence\n"
      "- If none found, return null.\n"
      "- Be very thorough in scanning the entire receipt, especially the bottom section\n"
      "- ONLY extract reference numbers that are clearly visible and readable\n"
      "- DO NOT guess or make up reference numbers\n"
      "- If the image is blurry or unclear, set confidence_score to 0.0\n"
      "Respond with JSON only."
    )
    payload = {
      "contents": [{
        "parts": [
          {"text": prompt},
          {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
        ]
      }],
      "generationConfig": {"temperature": 0.1, "topK": 1, "topP": 0.8, "maxOutputTokens": 512}
    }
    try:
      resp = requests.post(f"{url}?key={api_key}", json=payload, timeout=30)
    except requests.exceptions.ConnectionError as e:
      print(f"DEBUG: Connection error to Gemini API: {e}")
      if retry_count < 2:
        print(f"DEBUG: Connection failed, retrying in 3 seconds... (attempt {retry_count + 1}/3)")
        import time
        time.sleep(3)
        return _gemini_extract(image_b64, retry_count + 1)
      else:
        # Provide more specific error message based on the type of connection error
        error_msg = str(e).lower()
        if 'name resolution' in error_msg or 'getaddrinfo failed' in error_msg:
          return {'ok': False, 'message': 'AI service connection failed: Cannot resolve domain name. Please check your internet connection and DNS settings.'}
        elif 'timeout' in error_msg:
          return {'ok': False, 'message': 'AI service connection failed: Request timeout. Please check your internet connection speed.'}
        else:
          return {'ok': False, 'message': 'AI service connection failed. Please check your internet connection and try again.'}
    except requests.exceptions.Timeout as e:
      print(f"DEBUG: Timeout error to Gemini API: {e}")
      if retry_count < 2:
        print(f"DEBUG: Request timeout, retrying in 3 seconds... (attempt {retry_count + 1}/3)")
        import time
        time.sleep(3)
        return _gemini_extract(image_b64, retry_count + 1)
      else:
        return {'ok': False, 'message': 'AI service request timed out. Please try again.'}
    except requests.exceptions.RequestException as e:
      print(f"DEBUG: Request error to Gemini API: {e}")
      return {'ok': False, 'message': f'AI service request failed: {str(e)}. Please check your internet connection.'}
    
    if resp.status_code != 200:
      print(f"DEBUG: Gemini API error {resp.status_code}: {resp.text}")
      
      # Handle specific error cases with retry logic
      if resp.status_code == 503 and retry_count < 2:
        print(f"DEBUG: API overloaded, retrying in 2 seconds... (attempt {retry_count + 1}/3)")
        import time
        time.sleep(2)
        return _gemini_extract(image_b64, retry_count + 1)
      elif resp.status_code == 503:
        return {'ok': False, 'message': 'AI service is temporarily overloaded. Please try again in a few minutes.'}
      elif resp.status_code == 429:
        return {'ok': False, 'message': 'Too many requests. Please wait a moment and try again.'}
      elif resp.status_code == 400:
        return {'ok': False, 'message': 'Invalid request. Please check your receipt image.'}
      else:
        return {'ok': False, 'message': f'AI service error ({resp.status_code}). Please try again.'}
    j = resp.json()
    try:
      ai_text = j['candidates'][0]['content']['parts'][0]['text']
      print(f"DEBUG: Raw AI response text: {ai_text[:500]}...")
    except Exception as e:
      print(f"DEBUG: Error parsing AI response: {e}")
      return {'ok': False, 'message': f'No candidates in AI response: {str(e)}'}
    
    parsed = _extract_ref_amount_from_gemini_text(ai_text)
    if not parsed:
      print(f"DEBUG: Failed to parse AI JSON response: {ai_text}")
      return {'ok': False, 'message': f'AI processing failed: Invalid JSON from Gemini. Raw response: ```json {ai_text[:200]}```\n\nPlease try again in a few minutes. The AI service may be experiencing high traffic.'}
    
    print(f"DEBUG: Successfully parsed AI response: {parsed}")
    return {'ok': True, **parsed}
  except Exception as e:
    return {'ok': False, 'message': str(e)}

def _validate_payment(amount, reference_number, confidence, expected_amount=50.00):
  try:
    if not reference_number or not re.fullmatch(r'\d{7,16}', reference_number):
      return False, "Reference number must be 7-16 digits"
    if amount is None or amount <= 0:
      return False, "Invalid amount"
    if abs(amount - expected_amount) > 0.01:
      return False, f"Amount mismatch: found ₱{amount}, expected ₱{expected_amount}"
    if confidence < 0.85:
      return False, f"Low confidence: {confidence:.2f}"
    return True, ""
  except Exception as e:
    return False, str(e)

def _validate_image(file):
  """Validate uploaded image file"""
  try:
    if not file or not file.filename:
      return False, "No file provided"
    
    # Check file size (5MB limit)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > 5 * 1024 * 1024:  # 5MB
      return False, "Image size must be less than 5MB"
    
    # Check file type
    if not file.content_type or file.content_type not in ['image/jpeg', 'image/png', 'image/jpg']:
      return False, "Only JPEG and PNG images are allowed"
    
    return True, "Valid image"
  except Exception as e:
    return False, f"Error validating image: {str(e)}"

def _compress_image(file, max_size=(800, 600), quality=85):
  """Compress and optimize image for storage"""
  try:
    if Image is None:
      # If Pillow is not available, return original file data
      file.seek(0)
      return file.read()
    
    # Read the original image
    file.seek(0)
    original_data = file.read()
    
    # Open image with PIL
    if io is None:
      return original_data  # Return original if io module not available
    img = Image.open(io.BytesIO(original_data))
    
    # Convert to RGB if necessary (for JPEG compatibility)
    if img.mode in ('RGBA', 'LA', 'P'):
      img = img.convert('RGB')
    
    # Resize if image is too large
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Save with compression
    if io is None:
      return original_data  # Return original if io module not available
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    compressed_data = output.getvalue()
    
    # Return compressed data if it's smaller, otherwise return original
    if len(compressed_data) < len(original_data):
      return compressed_data
    else:
      return original_data
      
  except Exception as e:
    # If compression fails, return original data
    file.seek(0)
    return file.read()

# --- AWS S3 helpers ---
def _get_s3_client():
  """Get AWS S3 client with proper configuration"""
  if boto3 is None:
    return None
  
  try:
    # AWS S3 configuration
    s3_client = boto3.client(
      's3',
      aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
      aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
      region_name=os.getenv('AWS_REGION', 'ap-southeast-2')
    )
    return s3_client
  except Exception as e:
    print(f"Error creating S3 client: {e}")
    return None

def _upload_to_s3(file_data, bucket_name, object_key) -> Tuple[Optional[str], Optional[str]]:
  """Upload file data to S3 bucket"""
  s3_client = _get_s3_client()
  if not s3_client:
    return None, "S3 client not available"
  
  try:
    s3_client.put_object(
      Bucket=bucket_name,
      Key=object_key,
      Body=file_data,
      ContentType='image/jpeg'
    )
    # Return public HTTP URL instead of S3 URIng sa 
    public_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
    return public_url, None
  except ClientError as e:
    return None, f"S3 upload error: {e}"
  except Exception as e:
    return None, f"Upload error: {e}"

def _get_s3_presigned_url(bucket_name, object_key, expiration=3600) -> Tuple[Optional[str], Optional[str]]:
  """Generate presigned URL for S3 object"""
  s3_client = _get_s3_client()
  if not s3_client:
    return None, "S3 client not available"
  
  try:
    url = s3_client.generate_presigned_url(
      'get_object',
      Params={'Bucket': bucket_name, 'Key': object_key},
      ExpiresIn=expiration
    )
    return url, None
  except ClientError as e:
    return None, f"S3 presigned URL error: {e}"
  except Exception as e:
    return None, f"URL generation error: {e}"

def _check_s3_object_exists(bucket_name, object_key) -> bool:
  """Check if object exists in S3"""
  s3_client = _get_s3_client()
  if not s3_client:
    return False
  
  try:
    s3_client.head_object(Bucket=bucket_name, Key=object_key)
    return True
  except ClientError:
    return False
  except Exception:
    return False



# --- Separate OTP helpers ---
try:
    from app.templates.email_templates import get_otp_email_template
except ImportError:
    # Fallback if import fails
    def get_otp_email_template(full_name: str, otp: str, purpose: str = "verification") -> str:
        return f"""
        <html>
        <body>
        <h2>OTP Verification</h2>
        <p>Hello {full_name},</p>
        <p>Your OTP code for {purpose} is: <strong>{otp}</strong></p>
        <p>This code will expire in 30 seconds.</p>
        <p>Best regards,<br>iRequest Team</p>
        </body>
        </html>
        """

def _create_otp_email_template(full_name: str, otp: str, purpose: str = "verification") -> str:
    """Wrapper function for backward compatibility"""
    return get_otp_email_template(full_name, otp, purpose)

def _check_duplicate_request(cur, student_id, documents, purposes, document_type):
  """
  Check if student already has a similar pending or approved request
  Returns (is_duplicate, existing_request_info)
  """
  try:
    # Convert documents and purposes to JSON strings for comparison
    documents_json = json.dumps(sorted(documents)) if documents else '[]'
    purposes_json = json.dumps(sorted(purposes)) if purposes else '[]'
    
    # Check for existing requests with same documents, purposes, and document type
    cur.execute("""
      SELECT id, status, created_at, documents, purposes, document_type
      FROM clearance_requests 
      WHERE student_id = %s 
        AND document_type = %s 
        AND status IN ('Pending', 'Approved')
        AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
      ORDER BY created_at DESC
      LIMIT 5
    """, (student_id, document_type))
    
    existing_requests = cur.fetchall()
    
    for req in existing_requests:
      # Compare documents and purposes
      existing_docs = json.dumps(sorted(json.loads(req['documents'] or '[]')))
      existing_purposes = json.dumps(sorted(json.loads(req['purposes'] or '[]')))
      
      if (existing_docs == documents_json and 
          existing_purposes == purposes_json):
        return True, {
          'id': req['id'],
          'status': req['status'],
          'created_at': req['created_at'],
          'document_type': req['document_type']
        }
    
    return False, None
    
  except Exception as e:
    print(f"Error checking duplicate request: {e}")
    return False, None

def _send_email_html(to_email: str, subject: str, html_content: str) -> None:
  try:
    sender_email = "charlesedisonandres@gmail.com"
    app_password = "nphcfscccnwlxzzb"
    
    # Create multipart message for embedded images
    message = MIMEMultipart('related')
    message["Subject"] = subject
    message["From"] = formataddr(("iRequest", sender_email))
    message["To"] = to_email
    
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    # Embed logo image
    logo_path = os.path.join(os.path.dirname(__file__), "app", "static", "assets", "nclogo.png")
    if os.path.exists(logo_path):
      with open(logo_path, "rb") as f:
        img_data = f.read()
        image = MIMEImage(img_data)
        image.add_header("Content-ID", "<nclogo>")
        image.add_header("Content-Disposition", "inline", filename="nclogo.png")
        message.attach(image)
    
    try:
      context = ssl.create_default_context()
      with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, message.as_string())
    except Exception:
      server = smtplib.SMTP("smtp.gmail.com", 587)
      server.starttls()
      server.login(sender_email, app_password)
      server.sendmail(sender_email, to_email, message.as_string())
      server.quit()
  except Exception as e:
    import traceback
    print("[EMAIL ERROR] Failed to send OTP:", e)
    traceback.print_exc()
    try:
      with open("email_error.log", "a") as f:
        f.write(f"[EMAIL ERROR] {e}\n")
        f.write(traceback.format_exc() + "\n")
    except Exception:
      pass

def send_signup_otp(mysql, email, full_name, user_id):
  otp = str(random.randint(100000, 999999))
  cur, conn = mysql.cursor()
  cur.execute("UPDATE students SET otp_code=%s, otp_expires_at=DATE_ADD(NOW(), INTERVAL 30 SECOND), otp_verified=0 WHERE id=%s", (otp, user_id))
  # No need to commit with autocommit=True
  cur.close()
  conn.close()
  html_content = _create_otp_email_template(full_name, otp, "account registration")
  _send_email_html(email, "Your Registration OTP Code", html_content)
  return otp

def send_reset_otp(mysql, email, full_name, role, user_id):
  otp = str(random.randint(100000, 999999))
  cur, conn = mysql.cursor()
  if role == 'student':
    cur.execute("UPDATE students SET reset_code=%s, reset_expires_at=DATE_ADD(NOW(), INTERVAL 10 MINUTE) WHERE id=%s", (otp, user_id))
  else:
    cur.execute("UPDATE staff SET reset_code=%s, reset_expires_at=DATE_ADD(NOW(), INTERVAL 10 MINUTE) WHERE id=%s", (otp, user_id))
  # No need to commit with autocommit=True
  cur.close()
  conn.close()
  html_content = _create_otp_email_template(full_name, otp, "password reset")
  _send_email_html(email, "Password Reset OTP", html_content)
  return otp
# ...existing code...

# SocketIO removed - chat feature disabled

# Global mysql variable
mysql: Any = None

def create_notification(student_id, staff_name, action, phase, message):
    """Create a notification for a student"""
    try:
        cur, conn = mysql.cursor()
        cur.execute("""
            INSERT INTO notifications (student_id, staff_name, action, phase, message)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, staff_name, action, phase, message))
        # No need to commit with autocommit=True
        cur.close()
        conn.close()
        print(f"✅ Notification created for student {student_id}: {message}")
    except Exception as e:
        print(f"❌ Error creating notification: {e}")
        # Don't affect the main transaction if notification fails

def create_app() -> Flask:
  global mysql
  # Serve files from project root so existing asset paths work
  app = Flask(__name__, static_folder='app/static', static_url_path='/static', template_folder='app/templates')
  # Simple secret key for session usage (replace in production)
  app.secret_key = 'dev-secret-key'
  # Configure session to be more persistent
  app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
  # Uploads folder for released documents
  import os
  uploads_root = os.path.join(app.root_path, 'uploads', 'documents')
  os.makedirs(uploads_root, exist_ok=True)
  app.config['UPLOAD_FOLDER'] = uploads_root
  CORS(app)  # Enable CORS for all routes

  # MySQL config - Prefer environment variables with DNS pre-check and safe fallback
  import os
  from socket import gethostbyname, gaierror

  use_local = os.getenv('USE_LOCAL_DB', '').lower() == 'true'
  env_host = os.getenv('MYSQL_HOST', 'irequest.ctyeeiou09cg.ap-southeast-2.rds.amazonaws.com')
  env_user = os.getenv('MYSQL_USER', 'admin')
  env_pass = os.getenv('MYSQL_PASSWORD', 'Thesis_101')
  env_db = os.getenv('MYSQL_DB', 'irequest')

  if use_local:
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
    app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
    app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'irequest')
    print("🔧 Using LOCAL database configuration")
  else:
    # Pre-check DNS for the configured host to surface clearer errors and fallback if needed
    try:
      _ = gethostbyname(env_host)
      app.config['MYSQL_HOST'] = env_host
      app.config['MYSQL_USER'] = env_user
      app.config['MYSQL_PASSWORD'] = env_pass
      app.config['MYSQL_DB'] = env_db
      print("☁️ Using AWS RDS database configuration")
    except gaierror:
      print("❌ DNS resolution failed for configured DB host. Falling back to LOCAL DB. Set USE_LOCAL_DB=true to use local explicitly.")
      app.config['MYSQL_HOST'] = 'localhost'
      app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
      app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
      app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'irequest')
  
  app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

  # Use direct PyMySQL connection for AWS RDS
  try:
    import pymysql
    from pymysql.cursors import DictCursor as PyMySQLDictCursor
    print("✅ Using PyMySQL for direct database connection")
    
    class DirectMySQL:
      def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        
      def get_connection(self):
        """Create a fresh connection for each request"""
        import time
        from socket import gethostbyname, gaierror
        last_error = None
        for attempt in range(1, 4):
          try:
            print(f"🔍 Attempting to connect to: {self.host}:3306 (try {attempt}/3)")
            print(f"🔍 Database: {self.database}")
            print(f"🔍 User: {self.user}")
            # Resolve DNS explicitly to surface DNS issues early
            try:
              _ = gethostbyname(self.host)
            except gaierror as dns_err:
              last_error = dns_err
              print(f"⚠️ DNS resolution error: {dns_err}. Retrying...")
              time.sleep(1.5 * attempt)
              continue
            connection = pymysql.connect(
              host=self.host,
              user=self.user,
              password=self.password,
              database=self.database,
              charset='utf8mb4',
              cursorclass=PyMySQLDictCursor,
              autocommit=True,
              connect_timeout=10,
              read_timeout=60,
              write_timeout=60
            )
            print("✅ Database connection successful")
            return connection
          except pymysql.err.OperationalError as e:
            last_error = e
            # Error 2003 is often DNS/connection. Retry with backoff.
            if len(e.args) > 0 and e.args[0] == 2003:
              print(f"⚠️ OperationalError 2003 on attempt {attempt}: {e}. Retrying...")
              time.sleep(1.5 * attempt)
              continue
            print(f"❌ PyMySQL OperationalError: {e}")
            raise
          except Exception as e:
            last_error = e
            print(f"❌ General connection error on attempt {attempt}: {e}")
            time.sleep(1.0 * attempt)
            continue
        # After retries, raise the last seen error
        if last_error:
          raise last_error
        raise RuntimeError("Unknown database connection failure")
      
      def cursor(self):
        """Create a new connection and cursor for each operation"""
        connection = self.get_connection()
        return connection.cursor(), connection
      
      def commit(self):
        """No-op since we use autocommit"""
        pass
      
      def close(self):
        """No-op since we create fresh connections"""
        pass
    
    mysql = DirectMySQL(
      host=app.config['MYSQL_HOST'],
      user=app.config['MYSQL_USER'],
      password=app.config['MYSQL_PASSWORD'],
      database=app.config['MYSQL_DB']
    )
    print("✅ Direct MySQL connection configured")
    
  except ImportError:
    print("❌ PyMySQL not available - installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"])
    print("✅ PyMySQL installed, please restart the server")
    # Fallback to mock for now
    class MockMySQL:
      class MockConnection:
        def cursor(self):
          raise RuntimeError("PyMySQL not installed - please restart server")
        def commit(self):
          raise RuntimeError("PyMySQL not installed - please restart server")
      connection = MockConnection()
    mysql = MockMySQL()
  import json

  # Helper function for database operations
  def execute_query(query, params=None):
    """Execute a database query with proper connection management"""
    try:
      cur, conn = mysql.cursor()
      if params:
        cur.execute(query, params)
      else:
        cur.execute(query)
      result = cur.fetchall()
      cur.close()
      conn.close()
      return result
    except Exception as e:
      print(f"❌ Database query error: {e}")
      raise

  def execute_query_one(query, params=None):
    """Execute a database query and return one result"""
    try:
      cur, conn = mysql.cursor()
      if params:
        cur.execute(query, params)
      else:
        cur.execute(query)
      result = cur.fetchone()
      cur.close()
      conn.close()
      return result
    except Exception as e:
      print(f"❌ Database query error: {e}")
      raise

  def init_db() -> None:
    try:
      print("🔍 Initializing database...")
      # Test the connection first
      cur, conn = mysql.cursor()
      cur.execute("SELECT 1")
      cur.close()
      conn.close()
      print("✅ Database connection successful")
    except Exception as e:
      print(f"❌ Database initialization failed: {e}")
      return
      
    # Ensure database exists using PyMySQL (server-level connection). If this fails, continue using existing DB.
    if pymysql is not None:
      try:
        server_cnx = pymysql.connect(host=app.config['MYSQL_HOST'], user=app.config['MYSQL_USER'], password=app.config['MYSQL_PASSWORD'], autocommit=True)
        with server_cnx.cursor() as server_cur:
          server_cur.execute("CREATE DATABASE IF NOT EXISTS irequest CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        server_cnx.close()
        print("✅ Database 'irequest' created/verified successfully")
      except Exception as e:
        print(f"⚠️ Could not create database 'irequest': {e}")
        pass

    # Now create tables using direct MySQL connection
    try:
      cur, conn = mysql.cursor()
      print("✅ Database connection established successfully")
    except Exception as e:
      print(f"❌ Database connection failed: {e}")
      raise
    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_no VARCHAR(16) NOT NULL UNIQUE,
        first_name VARCHAR(100) NOT NULL,
        middle_name VARCHAR(100) NULL,
        last_name VARCHAR(100) NOT NULL,
        suffix VARCHAR(20) NULL,
        course_code VARCHAR(10) NOT NULL,
        course_name VARCHAR(150) NOT NULL,
        year_level INT NOT NULL,
        year_level_name VARCHAR(50) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        mobile VARCHAR(20) NOT NULL,
        gender ENUM('Male','Female') NOT NULL,
        address TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      """
    )

    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS staff (
        id INT AUTO_INCREMENT PRIMARY KEY,
        department VARCHAR(100) NOT NULL,
        first_name VARCHAR(100) NOT NULL,
        middle_name VARCHAR(100) NULL,
        last_name VARCHAR(100) NOT NULL,
        suffix VARCHAR(20) NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        contact_no VARCHAR(20) NOT NULL,
        gender ENUM('Male','Female') NOT NULL,
        address TEXT NOT NULL,
        status ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
        approved_by VARCHAR(255) NULL,
        rejection_reason TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      """
    )

  # Initialize database inside application context
  with app.app_context():
    init_db()

  # ---------------- Messenger config ----------------
  app.config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'dev-secret-change-me')
  app.config['JWT_EXPIRES_MIN'] = int(os.environ.get('JWT_EXPIRES_MIN', '43200'))  # 30 days
  
  # ---------------- Gemini API config ----------------
  app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', 'AIzaSyD5jvqYTkavoko_sFKbCYj5cXhIOtqf42I')

  def _get_or_create_user_from_session(cur):
    me_student = _get_current_student(cur)
    if me_student:
      # Map to users table
      cur.execute("""
        INSERT IGNORE INTO users (external_type, external_id, email, display_name, role)
        VALUES ('student', %s, (SELECT email FROM students WHERE id=%s),
                CONCAT(IFNULL((SELECT first_name FROM students WHERE id=%s),''),' ',IFNULL((SELECT last_name FROM students WHERE id=%s),'')), 'student')
      """, (me_student['id'], me_student['id'], me_student['id'], me_student['id']))
      cur.execute("SELECT id FROM users WHERE external_type='student' AND external_id=%s", (me_student['id'],))
      row = cur.fetchone()
      return row['id'] if row else None
    staff = _get_current_staff(cur)
    if staff:
      cur.execute("""
        INSERT IGNORE INTO users (external_type, external_id, email, display_name, role)
        VALUES ('staff', %s, (SELECT email FROM staff WHERE id=%s),
                CONCAT(IFNULL((SELECT first_name FROM staff WHERE id=%s),''),' ',IFNULL((SELECT last_name FROM staff WHERE id=%s),'')), 'staff')
      """, (staff['id'], staff['id'], staff['id'], staff['id']))
      cur.execute("SELECT id FROM users WHERE external_type='staff' AND external_id=%s", (staff['id'],))
      row = cur.fetchone()
      return row['id'] if row else None
    return None

  def _safe_jwt_decode(token: str):
    if not token or jwt is None:
      return None
    try:
      return jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
    except Exception:
      return None

  def _jwt_current_user_id(cur):
    auth = request.headers.get('Authorization', '')
    token = None
    if auth.lower().startswith('bearer '):
      token = auth.split(' ', 1)[1].strip()
    if token:
      payload = _safe_jwt_decode(token)
      if payload is not None:
        try:
          uid = int(payload.get('uid'))
        except Exception:
          uid = None
        if uid is not None:
          cur.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL", (uid,))
          row = cur.fetchone()
          if row:
            return uid
    # fallback to session mapping for backward compatibility
    return _get_or_create_user_from_session(cur)

  def _require_user(cur):
    uid = _jwt_current_user_id(cur)
    if not uid:
      return None, (jsonify({'ok': False, 'message': 'Unauthorized'}), 401)
    return uid, None

  # Chat functions removed - chat feature disabled

  # ---------------- Messenger REST APIs ----------------
  # use existing global _derive_dean_office defined later in module
  @app.route('/api/auth/token', methods=['GET'])
  def issue_jwt_token():
    cur, conn = mysql.cursor()
    uid = _jwt_current_user_id(cur)
    if not uid:
      return jsonify({'ok': False, 'message': 'Unauthorized'}), 401
    if jwt is None:
      return jsonify({'ok': False, 'message': 'JWT not available. Please install PyJWT (pip install PyJWT).'}), 500
    exp = datetime.utcnow() + timedelta(minutes=app.config['JWT_EXPIRES_MIN'])
    token = jwt.encode({'uid': uid, 'exp': exp}, app.config['JWT_SECRET'], algorithm='HS256')
    return jsonify({'ok': True, 'token': token})

  # Chat routes removed - chat feature disabled

  # Chat routes removed - chat feature disabled

  # Chat routes removed - chat feature disabled

  # Chat routes removed - chat feature disabled

  # Chat routes removed - chat feature disabled

  # Chat routes removed - chat feature disabled


  # SocketIO removed - chat feature disabled

  # ---------------- Chat APIs ----------------
  def _get_current_student(cur):
    student_email = session.get('student_email')
    if not student_email:
      return None
    cur.execute("SELECT id, first_name, last_name, student_no, course_code, course_name FROM students WHERE email=%s", (student_email,))
    return cur.fetchone()

  def _get_current_staff(cur):
    email = session.get('dean_email') or session.get('staff_email')
    if not email:
      return None
    cur.execute("SELECT id, first_name, last_name, department, email FROM staff WHERE email=%s AND status='Approved'", (email,))
    return cur.fetchone()


    # Ensure new approval-related columns exist even if table was created previously
    # Open a cursor for the following schema migration steps
    cur, conn = mysql.cursor()
    try:
      cur.execute("ALTER TABLE staff ADD COLUMN status ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending'")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE staff ADD COLUMN approved_by VARCHAR(255) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE staff ADD COLUMN rejection_reason TEXT NULL")
    except Exception:
      pass

    # Add new course structure columns to students table
    try:
      cur.execute("ALTER TABLE students ADD COLUMN course_code VARCHAR(10) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN course_name VARCHAR(150) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN year_level INT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN year_level_name VARCHAR(50) NULL")
    except Exception:
      pass
    
    # Migrate existing data to new structure
    try:
      cur.execute("""
        UPDATE students SET 
          course_code = CASE 
            WHEN course LIKE '%BEED%' THEN 'BEED'
            WHEN course LIKE '%BSED%' THEN 'BSED'
            WHEN course LIKE '%BSHM%' OR course LIKE '%HM%' THEN 'BSHM'
            WHEN course LIKE '%BSCS%' OR course LIKE '%Computer Science%' THEN 'BSCS'
            WHEN course LIKE '%ACT%' OR course LIKE '%Computer Technology%' THEN 'ACT'
            ELSE 'UNKNOWN'
          END,
          course_name = course,
          year_level = CASE 
            WHEN year_level LIKE '%1st%' OR year_level LIKE '%First%' THEN 1
            WHEN year_level LIKE '%2nd%' OR year_level LIKE '%Second%' THEN 2
            WHEN year_level LIKE '%3rd%' OR year_level LIKE '%Third%' THEN 3
            WHEN year_level LIKE '%4th%' OR year_level LIKE '%Fourth%' THEN 4
            ELSE 1
          END,
          year_level_name = year_level
        WHERE course_code IS NULL OR course_name IS NULL OR year_level IS NULL OR year_level_name IS NULL
      """)
    except Exception:
      pass

    # Add clearance-related columns to students table
    try:
      cur.execute("ALTER TABLE students ADD COLUMN status ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending'")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN signature TEXT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN rejection_reason TEXT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN approved_by VARCHAR(255) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN has_clearance_request TINYINT(1) NOT NULL DEFAULT 0")
    except Exception:
      pass
    # OTP columns for student email verification (first login)
    try:
      cur.execute("ALTER TABLE students ADD COLUMN otp_code VARCHAR(6) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN otp_expires_at DATETIME NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN otp_verified TINYINT(1) NOT NULL DEFAULT 0")
    except Exception:
      pass

    # Password reset OTP for students
    try:
      cur.execute("ALTER TABLE students ADD COLUMN reset_code VARCHAR(6) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE students ADD COLUMN reset_expires_at DATETIME NULL")
    except Exception:
      pass

    # Password reset OTP for staff
    try:
      cur.execute("ALTER TABLE staff ADD COLUMN reset_code VARCHAR(6) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE staff ADD COLUMN reset_expires_at DATETIME NULL")
    except Exception:
      pass

    # Legacy compatibility: ensure old 'course' column (if exists) is nullable
    try:
      cur.execute("ALTER TABLE students MODIFY COLUMN course VARCHAR(255) NULL")
    except Exception:
      pass

    # Before creating workflow tables, persist prior schema changes and reset cursor
    try:
      # No need to commit with autocommit=True
      pass
    except Exception:
      pass
    try:
      cur.close()
      conn.close()
    except Exception:
      pass
    # Clearance workflow tables
    cur, conn = mysql.cursor()
    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS clearance_requests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        status ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
        document_type VARCHAR(100) NULL,
        documents TEXT NULL,
        purposes TEXT NULL,
        reason TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_clearance_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      """
    )
    # Backfill columns in case table already existed without the new fields
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN fulfillment_status ENUM('Pending','Processing','Released','Rejected') NOT NULL DEFAULT 'Pending'")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN registrar_status ENUM('Pending','Processing','Complete') NOT NULL DEFAULT 'Pending'")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN document_type VARCHAR(100) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN documents TEXT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN purposes TEXT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN reason TEXT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN payment_method VARCHAR(20) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN payment_amount DECIMAL(10,2) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN payment_verified BOOLEAN DEFAULT FALSE")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN payment_receipt LONGTEXT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN payment_details TEXT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN payment_receipt LONGTEXT NULL")
    except Exception:
      pass
    # Add an explicit reference_number column for quick lookup if missing
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN reference_number VARCHAR(32) NULL")
    except Exception:
      pass
    # Add unique constraint to reference_number column to prevent duplicates
    try:
      cur.execute("ALTER TABLE clearance_requests ADD UNIQUE INDEX idx_unique_reference_number (reference_number)")
    except Exception:
      pass
    # Add S3 columns for receipt storage
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN payment_receipt_s3_url VARCHAR(500) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN payment_receipt_s3_key VARCHAR(255) NULL")
    except Exception:
      pass
    # Add index for duplicate checking performance
    try:
      cur.execute("ALTER TABLE clearance_requests ADD INDEX idx_duplicate_check (student_id, document_type, status, created_at)")
    except Exception:
      pass
    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS clearance_signatories (
        id INT AUTO_INCREMENT PRIMARY KEY,
        request_id INT NOT NULL,
        office VARCHAR(100) NOT NULL,
        status ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
        signed_by VARCHAR(255) NULL,
        signed_at TIMESTAMP NULL,
        rejection_reason TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_signatory_request FOREIGN KEY (request_id) REFERENCES clearance_requests(id) ON DELETE CASCADE,
        INDEX idx_req_office (request_id, office)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      """
    )


    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS document_requests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        document_type VARCHAR(255) NOT NULL,
        purpose TEXT NULL,
        status ENUM('Pending','Processing','Completed','Released','Unclaimed','Rejected') NOT NULL DEFAULT 'Pending',
        rejection_reason TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        completed_at TIMESTAMP NULL,
        auto_transferred_at TIMESTAMP NULL,
        clearance_request_id INT NULL,
        payment_method VARCHAR(50) NULL,
        payment_amount DECIMAL(10,2) NULL,
        payment_details TEXT NULL,
        payment_verified BOOLEAN DEFAULT FALSE,
        CONSTRAINT fk_doc_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        INDEX idx_student_status (student_id, status),
        INDEX idx_status_created (status, created_at),
        INDEX idx_auto_transferred_at (auto_transferred_at),
        INDEX idx_clearance_request_id (clearance_request_id)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      """
    )

    # Backfill for existing deployments where columns or indexes may be missing
    try:
      cur.execute("ALTER TABLE document_requests ADD COLUMN auto_transferred_at TIMESTAMP NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE document_requests ADD COLUMN clearance_request_id INT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE document_requests ADD COLUMN payment_method VARCHAR(50) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE document_requests ADD COLUMN payment_amount DECIMAL(10,2) NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE document_requests ADD COLUMN payment_details TEXT NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE document_requests ADD COLUMN payment_verified BOOLEAN DEFAULT FALSE")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE clearance_requests ADD COLUMN pickup_date TIMESTAMP NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE document_requests ADD COLUMN pickup_date TIMESTAMP NULL")
    except Exception:
      pass
    try:
      cur.execute("ALTER TABLE document_requests ADD COLUMN reference_number VARCHAR(32) NULL")
    except Exception:
      pass
    # Add unique constraint to reference_number column to prevent duplicates
    try:
      cur.execute("ALTER TABLE document_requests ADD UNIQUE INDEX idx_unique_reference_number (reference_number)")
    except Exception:
      pass
    # Try to extend ENUM to include Released/Unclaimed for older deployments
    try:
      cur.execute("ALTER TABLE document_requests MODIFY status ENUM('Pending','Processing','Completed','Released','Unclaimed','Rejected') NOT NULL DEFAULT 'Pending'")
    except Exception:
      pass

    # Ensure helpful indexes exist (wrapped to avoid errors on existing ones)
    try:
      cur.execute("CREATE INDEX idx_auto_transferred_at ON document_requests (auto_transferred_at)")
    except Exception:
      pass
    try:
      cur.execute("CREATE INDEX idx_clearance_request_id ON document_requests (clearance_request_id)")
    except Exception:
      pass

    # Create auto_transfer_logs table to track automatic transfers
    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS auto_transfer_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        clearance_request_id INT NOT NULL,
        document_request_id INT NOT NULL,
        student_id INT NOT NULL,
        transferred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reason VARCHAR(255) DEFAULT 'All office clearances approved',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_clearance_request (clearance_request_id),
        INDEX idx_document_request (document_request_id),
        INDEX idx_student_id (student_id),
        INDEX idx_transferred_at (transferred_at)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      """
    )

    # Files uploaded by registrar for released document requests
    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS document_files (
        id INT AUTO_INCREMENT PRIMARY KEY,
        document_request_id INT NOT NULL,
        original_name VARCHAR(255) NOT NULL,
        file_path VARCHAR(500) NOT NULL,
        mime_type VARCHAR(100) NULL,
        file_size INT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_doc_file_request (document_request_id),
        CONSTRAINT fk_doc_files_request FOREIGN KEY (document_request_id) REFERENCES document_requests(id) ON DELETE CASCADE
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      """
    )

    # Files uploaded by registrar for clearance requests
    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS clearance_files (
        id INT AUTO_INCREMENT PRIMARY KEY,
        clearance_request_id INT NOT NULL,
        original_name VARCHAR(255) NOT NULL,
        file_path VARCHAR(500) NOT NULL,
        mime_type VARCHAR(100) NULL,
        file_size INT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_clearance_file_request (clearance_request_id),
        CONSTRAINT fk_clearance_files_request FOREIGN KEY (clearance_request_id) REFERENCES clearance_requests(id) ON DELETE CASCADE
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      """
    )


    # Create departmental/year-level views to simulate per-table splits
    try:
      dept_to_course_code = {
        'HM': 'BSHM',
        'CS': 'BSCS',
        'BEED': 'BEED',
        'BSED': 'BSED',
      }
      year_to_suffix = {
        1: 'firstyear',
        2: 'secondyear',
        3: 'thirdyear',
        4: 'fourthyear',
      }
      # Per-year views (e.g., HM_Students_firstyear)
      for dept_prefix, course_code in dept_to_course_code.items():
        for year_num, year_suffix in year_to_suffix.items():
          view_name = f"{dept_prefix}_Students_{year_suffix}"
          cur.execute(
            f"""
            CREATE OR REPLACE VIEW {view_name} AS
            SELECT * FROM students
            WHERE course_code = '{course_code}' AND year_level = {year_num}
            """
          )
        # All-year view (e.g., HM_Students_all)
        all_view_name = f"{dept_prefix}_Students_all"
        cur.execute(
          f"""
          CREATE OR REPLACE VIEW {all_view_name} AS
          SELECT * FROM students
          WHERE course_code = '{course_code}'
          """
        )
    except Exception:
      # If views cannot be created (e.g., permissions), skip silently
      pass

    cur.close()
    conn.close()

  @app.route('/')
  def index():
    # Redirect to student signup page by default
    return redirect('/Student_Signup.html')

  # Routes to serve HTML templates
  @app.route('/login.html')
  def login_page():
    return render_template('login.html')
  
  @app.route('/Student_Signup.html')
  def student_signup_page():
    return render_template('Student_Signup.html')
  
  @app.route('/staff_signup.html')
  def staff_signup_page():
    return render_template('staff_signup.html')
  
  @app.route('/student_dashboard.html')
  def student_dashboard_page():
    return render_template('student_dashboard.html')
  
  @app.route('/Admin_Dashboard.html')
  def admin_dashboard_page():
    return render_template('Admin_Dashboard.html')
  
  @app.route('/Registrar_Dashboard.html')
  def registrar_dashboard_page():
    return render_template('Registrar_Dashboard.html')
  
  @app.route('/Dean_Dashboard.html')
  def dean_dashboard_page():
    return render_template('Dean_Dashboard.html')

  @app.route('/Dean_CoEd_Dashboard.html')
  def dean_coed_dashboard_page():
    return render_template('Dean_CoEd_Dashboard.html')
  
  @app.route('/Dean_CS_Dashboard.html')
  def dean_cs_dashboard_page():
    return render_template('Dean_CS_Dashboard.html')
  
  @app.route('/Dean_HM_Dashboard.html')
  def dean_hm_dashboard_page():
    return render_template('Dean_HM_Dashboard.html')
  
  @app.route('/ComputerLaboratory_Dashboard.html')
  def computer_lab_dashboard_page():
    return render_template('ComputerLaboratory_Dashboard.html')
  
  @app.route('/GuidanceOffice_Dashboard.html')
  def guidance_office_dashboard_page():
    return render_template('GuidanceOffice_Dashboard.html')
  
  @app.route('/StudentAffairs_dashboard.html')
  def student_affairs_dashboard_page():
    return render_template('StudentAffairs_dashboard.html')
  
  @app.route('/Library_Dashboard.html')
  def library_dashboard_page():
    return render_template('Library_Dashboard.html')
  
  @app.route('/Accounting_Dashboard.html')
  def accounting_dashboard_page():
    return render_template('Accounting_Dashboard.html')
  
  @app.route('/PropertyCustodian_Dashboard.html')
  def property_custodian_dashboard_page():
    return render_template('PropertyCustodian_Dashboard.html')
  
  @app.route('/forgot_password.html')
  def forgot_password_page():
    return render_template('forgot_password.html')
  
  @app.route('/reset_password.html')
  def reset_password_page():
    return render_template('reset_password.html')

  @app.route('/otp', methods=['GET', 'POST'])
  def otp_verification():
    if request.method == 'POST':
      # Handle OTP verification
      otp_code = request.form.get('otp', '').strip()
      email = session.get('pending_otp_email', '')
      
      if not email:
        session['otp_error'] = 'No email found in session. Please sign up again.'
        return redirect('/otp')
      
      if not otp_code or len(otp_code) != 6:
        session['otp_error'] = 'Please enter a valid 6-digit OTP code.'
        return redirect('/otp')
      
      # Verify OTP with database
      try:
        cur, conn = mysql.cursor()
        cur.execute("""
          SELECT id, otp_code, otp_expires_at 
          FROM students 
          WHERE email = %s AND otp_verified = 0
        """, (email,))
        student = cur.fetchone()
        
        if not student:
          session['otp_error'] = 'No pending verification found for this email.'
          return redirect('/otp')
        
        if student['otp_code'] != otp_code:
          session['otp_error'] = 'Invalid OTP code. Please try again.'
          return redirect('/otp')
        
        # Check if OTP is expired
        from datetime import datetime
        if student['otp_expires_at'] and datetime.now() > student['otp_expires_at']:
          session['otp_error'] = 'OTP code has expired. Please request a new one.'
          return redirect('/otp')
        
        # Mark email as verified
        cur.execute("""
          UPDATE students 
          SET otp_verified = 1, otp_code = NULL, otp_expires_at = NULL
          WHERE id = %s
        """, (student['id'],))
        # No need to commit with autocommit=True
        cur.close()
        conn.close()
        
        # Clear session variables
        session.pop('pending_otp_email', None)
        session.pop('otp_error', None)
        session['student_email'] = email
        
        return redirect('/student_dashboard.html')
        
      except Exception as e:
        session['otp_error'] = f'Verification failed: {str(e)}'
        return redirect('/otp')
    
    email = session.get('pending_otp_email', 'user@example.com')
    error_message = session.get('otp_error', '')
    show_signup_link = session.get('show_signup_link', False)
    
    if error_message:
      session.pop('otp_error', None)
    
    return render_template('otp_verification.html', 
                         email=email, 
                         error_message=error_message,
                         show_signup_link=show_signup_link)

  @app.route('/favicon.ico')
  def favicon():
    return send_from_directory(os.path.join(app.root_path, 'app', 'static', 'assets'), 'nclogo.png', mimetype='image/png')

  @app.route('/student/signup', methods=['POST'])
  def student_signup():
    form = request.form
    student_no = form.get('student_no', '').strip()
    first_name = form.get('first_name', '').strip()
    middle_name = form.get('middle_name', '').strip() or None
    last_name = form.get('last_name', '').strip()
    suffix = form.get('suffix', '').strip() or None
    course = form.get('course', '').strip()
    year_level = form.get('year_level', '').strip()
    email = form.get('email', '').strip().lower()
    password = form.get('password', '')
    confirm_password = form.get('confirm_password', '')
    mobile = form.get('mobile', '').strip()
    gender = form.get('gender', '').strip()
    address = form.get('address', '').strip()

    if not all([student_no, first_name, last_name, course, year_level, email, password, confirm_password, mobile, gender, address]):
      return jsonify({"ok": False, "message": "Please fill out all required fields."}), 400
    if password != confirm_password:
      return jsonify({"ok": False, "message": "Passwords do not match."}), 400

    # Parse course and year level
    course_code = ''
    course_name = course
    year_level_num = 1
    year_level_name = year_level
    
    # Extract course code
    if 'BEED' in course:
      course_code = 'BEED'
    elif 'BSED' in course:
      course_code = 'BSED'
    elif 'BSHM' in course or 'HM' in course:
      course_code = 'BSHM'
    elif 'BSCS' in course or 'Computer Science' in course:
      course_code = 'BSCS'
    elif 'ACT' in course or 'Computer Technology' in course:
      course_code = 'ACT'
    else:
      course_code = 'UNKNOWN'
    
    # Extract year level number
    if '1st' in year_level or 'First' in year_level:
      year_level_num = 1
    elif '2nd' in year_level or 'Second' in year_level:
      year_level_num = 2
    elif '3rd' in year_level or 'Third' in year_level:
      year_level_num = 3
    elif '4th' in year_level or 'Fourth' in year_level:
      year_level_num = 4
    else:
      year_level_num = 1

    password_hash = generate_password_hash(password)

    try:
      cur, conn = mysql.cursor()
      # Detect legacy 'course' column; if present, include it in INSERT
      cur.execute("SHOW COLUMNS FROM students LIKE 'course'")
      has_legacy_course_col = cur.fetchone() is not None

      base_columns = [
        'student_no', 'first_name', 'middle_name', 'last_name', 'suffix',
        'course_code', 'course_name', 'year_level', 'year_level_name',
        'email', 'password_hash', 'mobile', 'gender', 'address'
      ]
      base_values = [
        student_no, first_name, middle_name, last_name, suffix,
        course_code, course_name, year_level_num, year_level_name,
        email, password_hash, mobile, gender, address
      ]

      if has_legacy_course_col:
        base_columns.append('course')
        base_values.append(course_name)

      cols_sql = ', '.join(base_columns)
      placeholders_sql = ', '.join(['%s'] * len(base_columns))
      insert_sql = f"INSERT INTO students ({cols_sql}) VALUES ({placeholders_sql})"
      cur.execute(insert_sql, tuple(base_values))

      # No need to commit with autocommit=True
      # Send signup OTP and set pending session to verify email before first login
      try:
        full_name = f"{first_name} {last_name}".strip()
        # Fetch the inserted user id for OTP update (get by email)
        cur.execute("SELECT id FROM students WHERE email=%s", (email,))
        newly = cur.fetchone()
        if newly and newly.get('id'):
          send_signup_otp(mysql, email, full_name or 'User', newly['id'])
          session['pending_otp_email'] = email
      except Exception as _otp_err:
        # Do not fail signup on email errors; allow retry via resend on OTP page
        pass
      cur.close()
      conn.close()
    except Exception as err:
      return jsonify({"ok": False, "message": f"Database error: {err}"}), 500

    return jsonify({"ok": True, "message": "Student registered successfully! Please verify your email.", "redirect": "/otp"})

  @app.route('/staff/signup', methods=['POST'])
  def staff_signup():
    form = request.form
    department = form.get('department', '').strip()
    first_name = form.get('first_name', '').strip()
    middle_name = form.get('middle_name', '').strip() or None
    last_name = form.get('last_name', '').strip()
    suffix = form.get('suffix', '').strip() or None
    email = form.get('email', '').strip().lower()
    password = form.get('password', '')
    confirm_password = form.get('confirm_password', '')
    contact_no = form.get('mobile', '').strip()  # Frontend sends 'mobile' field
    gender = form.get('gender', '').strip()
    address = (form.get('address', '') or '').strip()
    # If hidden address wasn't constructed on the frontend, derive from parts
    if not address:
      province = (form.get('province') or '').strip()
      municipality = (form.get('municipality') or '').strip()
      barangay = (form.get('barangay') or '').strip()
      street = (form.get('street') or '').strip()
      block = (form.get('block') or '').strip()
      parts = []
      if block: parts.append(block)
      if street: parts.append(street)
      if barangay: parts.append(f"Brgy. {barangay}")
      if municipality and province: parts.append(f"{municipality}, {province}")
      elif municipality: parts.append(municipality)
      elif province: parts.append(province)
      address = ', '.join(parts)

    if not all([department, first_name, last_name, email, password, confirm_password, contact_no, gender, address]):
      return jsonify({"ok": False, "message": "Please fill out all required fields."}), 400
    if password != confirm_password:
      return jsonify({"ok": False, "message": "Passwords do not match."}), 400

    password_hash = generate_password_hash(password)

    is_admin_signup = department.strip().lower() == 'admin'

    try:
      cur, conn = mysql.cursor()
      if is_admin_signup:
        # Auto-approve Admin signups
        cur.execute(
          """
          INSERT INTO staff (department, first_name, middle_name, last_name, suffix,
                             email, password_hash, contact_no, gender, address, status, approved_by)
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Approved', 'System')
          """,
          (department, first_name, middle_name, last_name, suffix,
           email, password_hash, contact_no, gender, address)
        )
      else:
        cur.execute(
          """
          INSERT INTO staff (department, first_name, middle_name, last_name, suffix,
                             email, password_hash, contact_no, gender, address, status)
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
          """,
          (department, first_name, middle_name, last_name, suffix,
           email, password_hash, contact_no, gender, address)
        )
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
    except Exception as err:
      return jsonify({"ok": False, "message": f"Database error: {err}"}), 500

    if is_admin_signup:
      return jsonify({"ok": True, "message": "Admin account created and auto-approved. You can log in now."})
    return jsonify({"ok": True, "message": "Staff registered successfully! Please wait for admin approval before logging in."})

  @app.route('/health', methods=['GET'])
  def health_check():
    """Health check endpoint to test database connection"""
    try:
        cur, conn = mysql.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({"ok": True, "message": "Database connection is working"}), 200
    except Exception as err:
        return jsonify({"ok": False, "message": f"Database connection failed: {str(err)}"}), 500

  # Add Property Custodian to existing clearance requests
  @app.route('/api/fix-property-custodian', methods=['POST'])
  def fix_property_custodian_clearance():
    try:
      cur, conn = mysql.cursor()
      
      # Find clearance requests that don't have Property Custodian as a signatory
      cur.execute("""
        SELECT DISTINCT cr.id, cr.student_id, cr.status
        FROM clearance_requests cr
        WHERE cr.id NOT IN (
          SELECT DISTINCT cs.request_id 
          FROM clearance_signatories cs 
          WHERE cs.office = 'Property Custodian'
        )
        AND cr.status IN ('Pending', 'Approved', 'Rejected')
        ORDER BY cr.id
      """)
      
      requests_without_property_custodian = cur.fetchall()
      
      if not requests_without_property_custodian:
        return jsonify({"ok": True, "message": "All clearance requests already have Property Custodian signatory", "added": 0})
      
      # Add Property Custodian to each request
      added_count = 0
      for request in requests_without_property_custodian:
        request_id = request['id']
        
        # Check if Property Custodian already exists for this request
        cur.execute("""
          SELECT COUNT(*) as count 
          FROM clearance_signatories 
          WHERE request_id = %s AND office = 'Property Custodian'
        """, (request_id,))
        
        if cur.fetchone()['count'] == 0:
          # Add Property Custodian as Pending signatory
          cur.execute("""
            INSERT INTO clearance_signatories (request_id, office, status) 
            VALUES (%s, 'Property Custodian', 'Pending')
          """, (request_id,))
          added_count += 1
      
      # Commit changes
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      
      return jsonify({
        "ok": True, 
        "message": f"Successfully added Property Custodian to {added_count} clearance requests",
        "added": added_count
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/login', methods=['POST'])
  def login():
    form = request.form
    email = form.get('email', '').strip().lower()
    password = form.get('password', '')

    if not email or not password:
      return jsonify({"ok": False, "message": "Please enter both email and password."}), 400

    try:
        # Test database connection first
        try:
            cur, conn = mysql.cursor()
        except Exception as db_err:
            print(f"Database connection error: {db_err}")
            return jsonify({"ok": False, "message": "Database connection failed. Please try again later."}), 500
        
        # Check if user is a student
        cur.execute("SELECT id, first_name, last_name, password_hash, COALESCE(otp_verified, 0) AS otp_verified FROM students WHERE email = %s", (email,))
        student = cur.fetchone()
        if student and check_password_hash(student['password_hash'], password):
            # Login should not send or require OTP. Allow if credentials match.
            session['student_email'] = email
            session.permanent = True  # Make session permanent
            cur.close()
            conn.close()
            return jsonify({"ok": True, "redirect": "/student_dashboard.html"})
        # Check staff next; only allow Approved status
        cur.execute("SELECT id, department, first_name, last_name, password_hash, status FROM staff WHERE email = %s", (email,))
        staff = cur.fetchone()
        cur.close()
        conn.close()
        if staff and check_password_hash(staff['password_hash'], password):
            # Admin department bypasses approval
            department_lower = (staff.get('department') or '').strip().lower()
            if department_lower != 'admin' and staff.get('status') != 'Approved':
                return jsonify({"ok": False, "message": "Your account is not approved yet. Please wait for admin approval."}), 403
            # Save admin name in session for audit trails
            if department_lower == 'admin':
                admin_name = f"{staff.get('first_name','').strip()} {staff.get('last_name','').strip()}".strip()
                session['admin_name'] = admin_name or 'Admin'
            # Save dean email in session for dean dashboards
            elif 'dean' in department_lower:
                session['dean_email'] = email
            else:
                # Ensure previous dean session data doesn't leak into non-dean roles
                session.pop('dean_email', None)
            # Save generic staff department
            session['staff_department'] = department_lower
            # Save staff email for profile endpoints
            session['staff_email'] = email
            # Make session permanent for staff members
            session.permanent = True
            # Redirect by department
            department = department_lower
            dept_to_page = {
                'admin': '/Admin_Dashboard.html',
                'computer laboratory': '/ComputerLaboratory_Dashboard.html',
                'guidance office': '/GuidanceOffice_Dashboard.html',
                'student affairs': '/StudentAffairs_dashboard.html',
                'library': '/Library_Dashboard.html',
                'dean of coed': '/Dean_CoEd_Dashboard.html',
                'dean of hm': '/Dean_HM_Dashboard.html',
                'dean of cs': '/Dean_CS_Dashboard.html',
                'accounting': '/Accounting_Dashboard.html',
                'property custodian': '/PropertyCustodian_Dashboard.html',
                'registrar': '/Registrar_Dashboard.html',
            }
            return jsonify({"ok": True, "redirect": dept_to_page.get(department, '/Admin_Dashboard.html')})
        return jsonify({"ok": False, "message": "Invalid email or password."}), 401
    except Exception as err:
        print(f"Login error details: {err}")
        return jsonify({"ok": False, "message": f"Login error: {str(err)}"}), 500

  def _message_and_back(message: str):
    return render_template_string(
      """
      <!doctype html>
      <html lang=\"en\">
        <head>
          <meta charset=\"utf-8\">
          <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
          <title>Notice</title>
          <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
          <script src=\"https://cdn.jsdelivr.net/npm/sweetalert2@11\"></script>
        </head>
        <body class=\"p-4\">
          <script>
            (function(){
              const msg = {{ message|tojson }};
              const lower = msg.toLowerCase();
              let icon = 'info';
              if (lower.includes('error')) icon = 'error';
              else if (lower.includes('success')) icon = 'success';
              else if (lower.includes('warning')) icon = 'warning';
              Swal.fire({
                title: icon === 'error' ? 'Error' : (icon === 'success' ? 'Success' : 'Notice'),
                text: msg,
                icon: icon,
                confirmButtonText: 'OK',
                allowOutsideClick: false,
              }).then(() => {
                if (window.history.length > 1) {
                  history.back();
                } else {
                  window.location.href = '/';
                }
              });
            })();
          </script>
        </body>
      </html>
      """,
      message=message
    )
    # Resend OTP API (POST only, rate-limited by 30s and replaces previous code)
  @app.route('/otp/resend', methods=['POST'])
  def otp_resend() -> Any:
    pending_email = session.get('pending_otp_email')
    if not pending_email:
      return jsonify({"ok": False, "message": "No pending verification."}), 400
    try:
      cur, conn = mysql.cursor()
      cur.execute("SELECT id, first_name, last_name, otp_expires_at FROM students WHERE email=%s", (pending_email,))
      row = cur.fetchone()
      if not row:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Account not found."}), 404
      # Enforce 30-second rate-limit: if not expired yet, block resend
      expires = row.get('otp_expires_at')
      can_resend = True
      if expires is not None:
        try:
          can_resend = datetime.utcnow() > (expires if expires.tzinfo is None else expires)
        except Exception:
          can_resend = True
      if not can_resend:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Please wait until the countdown finishes before resending."}), 429
      full_name = f"{row.get('first_name','').strip()} {row.get('last_name','').strip()}".strip() or 'User'
      send_signup_otp(mysql, pending_email, full_name, row['id'])
      cur.close()
      conn.close()
      return jsonify({"ok": True, "message": "A new code has been sent."})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500
    return render_template_string("""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"UTF-8\">
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
      <title>Email Verification - OTP</title>
      <link href=\"https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap\" rel=\"stylesheet\">
      <style>
        {% raw %}
        * {{
          margin: 0;
          padding: 0;
          box-sizing: border-box;
          font-family: 'Poppins', sans-serif;
        }}

        body {{
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100vh;
          position: relative;
          overflow: hidden;
        }}

        /* Background with dark overlay */
        body::before {{
          content: "";
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: url("/assets/NC_Facade.jpg") no-repeat center center/cover;
          filter: brightness(0.55);
          z-index: -1;
        }}

        .verify-container {{
          background: rgba(255, 255, 255, 0.15);
          -webkit-backdrop-filter: blur(15px);
          backdrop-filter: blur(15px);
          border: 1px solid rgba(255, 255, 255, 0.25);
          padding: 45px 35px;
          border-radius: 20px;
          box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4);
          width: 400px;
          animation: fadeIn 0.8s ease;
          text-align: center;
        }}

        .logo {{
          width: 80px;
          height: 80px;
          margin: 0 auto 15px;
          background: rgba(255, 255, 255, 0.9);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}

        .logo img {{
          width: 60px;
          height: 60px;
          object-fit: contain;
        }}

        .verify-container h2 {{
          color: #fff;
          font-weight: 600;
          font-size: 24px;
          margin-bottom: 8px;
          letter-spacing: 0.5px;
        }}

        .subtitle {{
          color: #f1f1f1;
          font-size: 14px;
          margin-bottom: 25px;
          opacity: 0.9;
        }}

        .email-info {{
          color: #ffdd57;
          font-size: 13px;
          margin-bottom: 25px;
          font-weight: 500;
        }}

        .otp-form-group {{
          display: flex;
          justify-content: center;
          gap: 8px;
          margin-bottom: 30px;
        }}

        .otp-inputbar {{
          width: 45px;
          height: 45px;
          border-radius: 12px;
          text-align: center;
          font-size: 18px;
          font-weight: bold;
          color: #333;
          border: 2px solid rgba(255, 255, 255, 0.3);
          background: rgba(255, 255, 255, 0.85);
          transition: all 0.3s ease;
        }}

        .otp-inputbar:focus {{
          background: #fff;
          border-color: #007bff;
          box-shadow: 0 0 8px rgba(0, 123, 255, 0.5);
          outline: none;
        }}

        .btn {{
          width: 100%;
          padding: 14px;
          background: linear-gradient(135deg, #007bff, #0056b3);
          border: none;
          border-radius: 12px;
          color: #fff;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
        }}

        .btn:hover {{
          background: linear-gradient(135deg, #0056b3, #004099);
          transform: translateY(-2px);
          box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
        }}

        #errmsg {{
          color: #ff6b6b;
          font-size: 13px;
          margin-top: 15px;
          font-weight: 500;
        }}

        /* Fade-in animation */
        @keyframes fadeIn {{
          from {{ opacity: 0; transform: translateY(-20px); }}
          to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Responsive */
        @media (max-width: 420px) {{
          .verify-container {{
            width: 90%;
            padding: 35px 25px;
          }}
          
          .otp-inputbar {{
            width: 40px;
            height: 40px;
            font-size: 16px;
          }}
        }}
        {% endraw %}
        {% endraw %}
      </style>
    </head>
    <body>
      <div class=\"verify-container\">
        <div class=\"logo\">
          <img src=\"/assets/nclogo.png\" alt=\"Norzagaray College Logo\">
        </div>
        <h2>Email Verification</h2>
        <p class=\"subtitle\">OTP Verification</p>
        <p class=\"email-info\">Enter the 6-digit code sent to {{ email }}</p>
        
        <form method=\"POST\" id=\"otpForm\">
          <div class=\"otp-form-group\">
            <input type=\"text\" name=\"otp1\" minlength=\"1\" maxlength=\"1\" class=\"otp-inputbar\" required>
            <input type=\"text\" name=\"otp2\" minlength=\"1\" maxlength=\"1\" class=\"otp-inputbar\" required>
            <input type=\"text\" name=\"otp3\" minlength=\"1\" maxlength=\"1\" class=\"otp-inputbar\" required>
            <input type=\"text\" name=\"otp4\" minlength=\"1\" maxlength=\"1\" class=\"otp-inputbar\" required>
            <input type=\"text\" name=\"otp5\" minlength=\"1\" maxlength=\"1\" class=\"otp-inputbar\" required>
            <input type=\"text\" name=\"otp6\" minlength=\"1\" maxlength=\"1\" class=\"otp-inputbar\" required>
          </div>
          
          <button type=\"submit\" class=\"btn\">Verify Email</button>
        </form>
        <div style=\"margin-top:12px;color:#f1f1f1;font-size:13px;\">
          <button id=\"resendBtn\" class=\"btn\" disabled style=\"width:auto;padding:8px 12px;\">Resend OTP</button>
          <span id=\"countdown\" style=\"margin-left:8px;\">00:30</span>
        </div>
        
        <div id=\"errmsg\"></div>
      </div>
      
      <script>
        // OTP input navigation
        const inputs = document.querySelectorAll('.otp-inputbar');
        document.querySelectorAll('.otp-inputbar').forEach((input, index, inputs) => {{
          input.addEventListener('input', function() {{
            if (this.value && index < inputs.length - 1) {{
              inputs[index + 1].focus();
            }}
          }});
          
          input.addEventListener('keydown', function(e) {{
            if ((e.key === 'Backspace' || e.key === 'Delete') && !this.value && index > 0) {{
              inputs[index - 1].focus();
            }}
          }});
          
          // Only allow digits
          input.addEventListener('keypress', function(e) {{
            if (e.which < 48 || e.which > 57) {{
              document.getElementById('errmsg').textContent = 'Digits only';
              setTimeout(() => document.getElementById('errmsg').textContent = '', 2000);
              e.preventDefault();
            }}
          }});
        }});

        // Countdown + resend logic
        let remaining = 30;
        const resendBtn = document.getElementById('resendBtn');
        const countdownEl = document.getElementById('countdown');
        const timer = setInterval(() => {{
          remaining -= 1;
          const mm = '00';
          const ss = String(Math.max(remaining,0)).padStart(2,'0');
          countdownEl.textContent = mm + ':' + ss;
          if (remaining <= 0) {{
            clearInterval(timer);
            resendBtn.disabled = false;
          }}
        }}, 1000);

        resendBtn.addEventListener('click', async function() {{
          resendBtn.disabled = true;
          document.getElementById('errmsg').textContent = '';
          try {{
            const resp = await fetch('/otp/resend', {{ method: 'POST' }});
            const data = await resp.json();
            if (!resp.ok || !data.ok) {{
              document.getElementById('errmsg').textContent = data && data.message ? data.message : 'Failed to resend code.';
              return;
            }}
            // Restart countdown and disable button again
            remaining = 30;
            countdownEl.textContent = '00:30';
            const newTimer = setInterval(() => {{
              remaining -= 1;
              countdownEl.textContent = '00:' + String(Math.max(remaining,0)).padStart(2,'0');
              if (remaining <= 0) {{
                clearInterval(newTimer);
                resendBtn.disabled = false;
              }}
            }}, 1000);
          }} catch (e) {{
            document.getElementById('errmsg').textContent = 'Network error. Please try again.';
          }}
        }});
      </script>
    </body>
    </html>
    """)

  # --- Simple Admin APIs ---
  @app.route('/admin/staff/pending')
  def admin_list_pending():
    try:
      cur, conn = mysql.cursor()
      cur.execute("SELECT id, first_name, last_name, department, email, status FROM staff WHERE status = 'Pending'")
      rows = cur.fetchall()
      cur.close()
      conn.close()
      rows_html = ''.join([
        f"<tr><td>{r['first_name']} {r['last_name']}</td><td>{r['department']}</td><td>{r['email']}</td>"
        f"<td>{r['status']}</td><td>"
        f"<form method='POST' action='/admin/staff/approve' style='display:inline'>"
        f"<input type='hidden' name='id' value='{r['id']}'/>"
        f"<button class='btn btn-success btn-sm' type='submit'>Approve</button></form> "
        f"<form method='POST' action='/admin/staff/reject' style='display:inline'>"
        f"<input type='hidden' name='id' value='{r['id']}'/>"
        f"<input type='text' name='reason' placeholder='Reason' required/> "
        f"<button class='btn btn-danger btn-sm' type='submit'>Reject</button></form>"
        f"</td></tr>" for r in rows
      ])
      return render_template_string(
        """
        <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css' rel='stylesheet'>
        <div class='container p-4'>
          <h3>Pending Staff Approvals</h3>
          <table class='table table-bordered table-sm'>
            <thead><tr><th>Name</th><th>Department</th><th>Email</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>{{ rows_html|safe }}</tbody>
          </table>
          <a class='btn btn-link' href='/Admin_Dashboard.html'>Back to Admin Dashboard</a>
        </div>
        """,
        rows_html=rows_html,
      )
    except Exception as err:
      return _message_and_back(f"Error: {err}")

  @app.route('/admin/staff/approve', methods=['POST'])
  def admin_approve_staff():
    body = request.get_json(silent=True) or {}
    staff_id = request.form.get('id') or body.get('id')
    approver = session.get('admin_name') or request.form.get('approver') or body.get('approver') or 'Admin'
    if not staff_id:
      return _message_and_back('Missing staff id.')
    try:
      cur, conn = mysql.cursor()
      cur.execute("UPDATE staff SET status='Approved', approved_by=%s, rejection_reason=NULL WHERE id=%s", (approver, staff_id))
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      if request.is_json:
        return jsonify({"ok": True})
      return redirect('/admin/staff/pending')
    except Exception as err:
      if request.is_json:
        return jsonify({"ok": False, "message": f"Error: {err}"}), 500
      return _message_and_back(f"Error: {err}")

  @app.route('/admin/staff/reject', methods=['POST'])
  def admin_reject_staff():
    body = request.get_json(silent=True) or {}
    staff_id = request.form.get('id') or body.get('id')
    reason = (request.form.get('reason', '') or body.get('reason', ''))
    reason = (reason or '').strip()
    approver = session.get('admin_name') or request.form.get('approver') or body.get('approver') or 'Admin'
    if not staff_id or not reason:
      if request.is_json:
        return jsonify({"ok": False, "message": 'Missing staff id or reason.'}), 400
      return _message_and_back('Missing staff id or reason.')
    try:
      cur, conn = mysql.cursor()
      cur.execute("UPDATE staff SET status='Rejected', approved_by=%s, rejection_reason=%s WHERE id=%s", (approver, reason, staff_id))
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      if request.is_json:
        return jsonify({"ok": True})
      return redirect('/admin/staff/pending')
    except Exception as err:
      if request.is_json:
        return jsonify({"ok": False, "message": f"Error: {err}"}), 500
      return _message_and_back(f"Error: {err}")

  @app.route('/api/admin/staff')
  def api_admin_staff_list():
    status = (request.args.get('status') or '').strip()
    try:
      cur, conn = mysql.cursor()
      if status:
        cur.execute("SELECT id, first_name, last_name, department, email, status, approved_by, rejection_reason, created_at FROM staff WHERE status = %s ORDER BY created_at DESC", (status,))
      else:
        cur.execute("SELECT id, first_name, last_name, department, email, status, approved_by, rejection_reason, created_at FROM staff ORDER BY created_at DESC")
      rows = cur.fetchall()
      cur.close()
      conn.close()
      return jsonify({"ok": True, "data": rows})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/admin/staff/counts')
  def api_admin_staff_counts():
    try:
      cur, conn = mysql.cursor()
      cur.execute("SELECT status, COUNT(*) AS c FROM staff GROUP BY status")
      rows = cur.fetchall()
      cur.execute("SELECT COUNT(*) AS total FROM staff")
      total_row = cur.fetchone()
      cur.close()
      conn.close()
      counts = { 'Pending': 0, 'Approved': 0, 'Rejected': 0 }
      for r in rows:
        counts[r['status']] = r['c']
      counts['Total'] = total_row['total'] if total_row else 0
      return jsonify({"ok": True, "data": counts})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/admin/me')
  def api_admin_me():
    return jsonify({"ok": True, "admin_name": session.get('admin_name', 'Admin')})

  # Helper function to build student information from database result
  def _build_student_info(result):
    """Build student information object from database result"""
    if not result:
      return None
    
    # Build full name
    first_name = result.get('first_name', '').strip()
    middle_name = result.get('middle_name', '').strip()
    last_name = result.get('last_name', '').strip()
    
    full_name = first_name
    if middle_name:
      full_name += f" {middle_name}"
    if last_name:
      full_name += f" {last_name}"
    
    # Build year level name
    year_level_name = result.get('year_level_name')
    year_level = result.get('year_level')
    if not year_level_name and year_level:
      try:
        num = int(str(year_level).strip().split()[0])
        year_level_name = f"Year {num}"
      except Exception:
        year_level_name = str(year_level)
    
    return {
      "full_name": full_name,
      "first_name": first_name,
      "middle_name": middle_name,
      "last_name": last_name,
      "student_id": result.get('student_no'),  # Use student_no from students table
      "course_name": result.get('course_name'),
      "course_code": result.get('course_code'),
      "year_level": year_level,
      "year_level_name": year_level_name,
      "email": result.get('email')
    }

  # --- Receipt Image API ---
  @app.route('/api/receipt/<int:request_id>', methods=['GET'])
  def api_get_receipt_image(request_id):
    """Get receipt image for a clearance request - SIMPLIFIED to use only clearance_requests table"""
    try:
      print(f"🔍 Receipt API: Fetching receipt for clearance_request_id: {request_id}")
      
      # Check if mysql connection is available
      if not mysql:
        print(f"🔍 Receipt API: MySQL connection not available")
        return jsonify({"ok": False, "message": "Database connection not available"}), 500
      
      cur, conn = mysql.cursor()
      
      # SIMPLIFIED: Only query clearance_requests table with student info
      try:
        # First, let's check what columns exist in clearance_requests table
        print(f"🔍 Receipt API: Checking clearance_requests table structure...")
        cur.execute("SHOW COLUMNS FROM clearance_requests")
        columns_result = cur.fetchall()
        # When using DictCursor, results are dictionaries, not tuples
        columns = [row['Field'] for row in columns_result] if columns_result else []
        print(f"🔍 Receipt API: Available columns in clearance_requests: {columns}")
        
        if not columns:
          print(f"🔍 Receipt API: No columns found - table might not exist")
          return jsonify({"ok": False, "message": "clearance_requests table not found"}), 404
        
        # Build query based on available columns
        base_columns = ["cr.id", "cr.student_id", "cr.created_at"]
        if "payment_receipt" in columns:
          base_columns.append("cr.payment_receipt")
        if "payment_receipt_s3_url" in columns:
          base_columns.append("cr.payment_receipt_s3_url")
        if "payment_receipt_s3_key" in columns:
          base_columns.append("cr.payment_receipt_s3_key")
        if "payment_method" in columns:
          base_columns.append("cr.payment_method")
        if "payment_amount" in columns:
          base_columns.append("cr.payment_amount")
        if "reference_number" in columns:
          base_columns.append("cr.reference_number")
        
        student_columns = [
          "s.first_name", "s.last_name", "s.middle_name", "s.student_no", 
          "s.course_name", "s.course_code", "s.year_level", "s.year_level_name", "s.email"
        ]
        
        all_columns = base_columns + student_columns
        query = f"""
          SELECT {', '.join(all_columns)}
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE cr.id = %s
        """
        
        print(f"🔍 Receipt API: Executing query: {query}")
        print(f"🔍 Receipt API: Query parameters: request_id={request_id}")
        cur.execute(query, (request_id,))
        
        result = cur.fetchone()
        print(f"🔍 Receipt API: Query result: {result}")
        cur.close()
        conn.close()
        
        if not result:
          print(f"🔍 Receipt API: No clearance request found with ID: {request_id}")
          return jsonify({"ok": False, "message": "Clearance request not found"}), 404
        
        # Build student information
        try:
          print(f"🔍 Receipt API: Building student info from result: {result}")
          student_info = _build_student_info(result)
          print(f"🔍 Receipt API: Student info built successfully: {student_info}")
        except Exception as student_error:
          print(f"🔍 Receipt API: Error building student info: {student_error}")
          print(f"🔍 Receipt API: Student error type: {type(student_error)}")
          print(f"🔍 Receipt API: Student error str: '{str(student_error)}'")
          import traceback
          traceback.print_exc()
          student_info = None
        
        # Check for receipt image - prioritize S3, fallback to database
        s3_url = result.get('payment_receipt_s3_url')
        s3_key = result.get('payment_receipt_s3_key')
        receipt_data = result.get('payment_receipt')
        
        print(f"🔍 Receipt API: S3 URL exists: {s3_url is not None}")
        print(f"🔍 Receipt API: S3 Key exists: {s3_key is not None}")
        print(f"🔍 Receipt API: Database receipt exists: {receipt_data is not None}, length: {len(receipt_data) if receipt_data else 0}")
        
        # Try S3 first
        if s3_url and s3_key:
          try:
            # Use the direct public URL from S3
            print(f"🔍 Receipt API: Using S3 public URL: {s3_url[:100]}...")
            return jsonify({
              "ok": True,
              "image_url": s3_url,
              "source": "s3",
              "student_info": student_info
            })
          except Exception as s3_error:
            print(f"🔍 Receipt API: S3 error: {s3_error}")
            # Fall back to database if S3 fails
        
        # Fallback to database storage
        if receipt_data:
          print(f"🔍 Receipt API: Using database storage (length: {len(receipt_data)})")
          return jsonify({
            "ok": True,
            "image_data": receipt_data,
            "source": "database",
            "student_info": student_info
          })
        
        # If no receipt image, return payment information
        payment_method = result.get('payment_method')
        payment_amount = result.get('payment_amount')
        reference_number = result.get('reference_number')
        
        if payment_method or payment_amount or reference_number:
          print(f"🔍 Receipt API: No receipt image, but payment info available")
          return jsonify({
            "ok": True,
            "no_receipt": True,
            "payment_info": {
              "method": payment_method or "Not specified",
              "amount": payment_amount or "Not specified",
              "reference_number": reference_number or "Not provided"
            },
            "message": "No receipt image uploaded, but payment information is available.",
            "student_info": student_info
          })
        
        print(f"🔍 Receipt API: No receipt image or payment information found")
        return jsonify({
          "ok": False, 
          "message": "No receipt image or payment information found for this clearance request"
        }), 404
        
      except pymysql.Error as query_error:
        cur.close()
        conn.close()
        print(f"🔍 Receipt API: PyMySQL Error: {query_error}")
        print(f"🔍 Receipt API: Error Code: {query_error.args[0]}")
        print(f"🔍 Receipt API: Error Message: {query_error.args[1]}")
        return jsonify({
          "ok": False, 
          "message": f"Database query error - PyMySQL Error {query_error.args[0]}: {query_error.args[1]}"
        }), 500
      except Exception as query_error:
        cur.close()
        conn.close()
        print(f"🔍 Receipt API: Database query error: {query_error}")
        print(f"🔍 Receipt API: Error type: {type(query_error)}")
        print(f"🔍 Receipt API: Error str: '{str(query_error)}'")
        print(f"🔍 Receipt API: Error repr: {repr(query_error)}")
        import traceback
        traceback.print_exc()
        return jsonify({
          "ok": False, 
          "message": f"Database query error: {str(query_error)}"
        }), 500
      
    except pymysql.Error as e:
      print(f"🔍 Receipt API: PyMySQL Error: {e}")
      print(f"🔍 Receipt API: Error Code: {e.args[0]}")
      print(f"🔍 Receipt API: Error Message: {e.args[1]}")
      import traceback
      traceback.print_exc()
      return jsonify({
        "ok": False, 
        "message": f"Error fetching receipt - PyMySQL Error {e.args[0]}: {e.args[1]}"
      }), 500
    except Exception as e:
      print(f"🔍 Receipt API: General error: {e}")
      import traceback
      traceback.print_exc()
      return jsonify({
        "ok": False, 
        "message": f"Error fetching receipt: {str(e)}"
      }), 500

  # Test endpoint to check database connection
  @app.route('/api/test-db', methods=['GET'])
  def api_test_db():
    """Test database connection and clearance_requests table"""
    try:
      print("🔍 Test DB: Testing database connection...")
      
      if not mysql:
        return jsonify({"ok": False, "message": "MySQL connection not available"}), 500
      
      print("🔍 Test DB: Creating cursor...")
      cur, conn = mysql.cursor()
      print("🔍 Test DB: Cursor created successfully")
      
      # Test basic query
      print("🔍 Test DB: Testing basic query...")
      cur.execute("SELECT COUNT(*) as count FROM clearance_requests")
      count_result = cur.fetchone()
      print(f"🔍 Test DB: Count query result: {count_result}")
      
      # Test columns
      print("🔍 Test DB: Testing columns query...")
      cur.execute("SHOW COLUMNS FROM clearance_requests")
      columns = [row[0] for row in cur.fetchall()]
      print(f"🔍 Test DB: Available columns: {columns}")
      
      # Test a sample record
      print("🔍 Test DB: Testing sample record query...")
      cur.execute("SELECT id, student_id FROM clearance_requests LIMIT 1")
      sample = cur.fetchone()
      print(f"🔍 Test DB: Sample record: {sample}")
      
      cur.close()
      conn.close()
      print("🔍 Test DB: Connection closed successfully")
      
      return jsonify({
        "ok": True,
        "message": "Database connection successful",
        "clearance_requests_count": count_result['count'] if count_result else 0,
        "available_columns": columns,
        "sample_record": sample
      })
      
    except pymysql.Error as e:
      print(f"🔍 Test DB: PyMySQL Error: {e}")
      print(f"🔍 Test DB: Error Code: {e.args[0]}")
      print(f"🔍 Test DB: Error Message: {e.args[1]}")
      import traceback
      traceback.print_exc()
      return jsonify({
        "ok": False, 
        "message": f"Database test failed - PyMySQL Error {e.args[0]}: {e.args[1]}"
      }), 500
    except Exception as e:
      print(f"🔍 Test DB: General Error: {e}")
      import traceback
      traceback.print_exc()
      return jsonify({
        "ok": False, 
        "message": f"Database test failed: {str(e)}"
      }), 500

  @app.route('/api/test-s3', methods=['GET'])
  def test_s3_connection():
    """Test S3 bucket connection and upload capability"""
    try:
      s3_client = _get_s3_client()
      if not s3_client:
        return jsonify({"ok": False, "message": "S3 client not available"}), 500
      
      # Test bucket access
      bucket_name = os.getenv('AWS_S3_BUCKET', 'irequest-receipts')
      response = s3_client.head_bucket(Bucket=bucket_name)
      
      # Test upload a small test file
      test_data = b"test receipt upload - " + datetime.now().strftime('%Y-%m-%d %H:%M:%S').encode()
      test_key = f"test/test_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
      
      s3_client.put_object(
        Bucket=bucket_name,
        Key=test_key,
        Body=test_data,
        ContentType='text/plain'
      )
      
      # Generate public URL
      public_url = f"https://{bucket_name}.s3.amazonaws.com/{test_key}"
      
      return jsonify({
        "ok": True, 
        "message": "S3 bucket is accessible and upload successful",
        "bucket": bucket_name,
        "region": "ap-southeast-2",
        "test_file_url": public_url,
        "test_key": test_key
      })
    except Exception as e:
      return jsonify({
        "ok": False, 
        "message": f"S3 connection failed: {str(e)}"
      }), 500

  @app.route('/api/student/me')
  def api_student_me():
    try:
      cur, conn = mysql.cursor()
      student_email = session.get('student_email')
      if not student_email:
        return jsonify({"ok": False, "message": "No student session found (HTTP 401)"}), 401
      
      # Select all columns to be compatible with varying schemas
      cur.execute(
        """
        SELECT *
        FROM students
        WHERE email = %s
        """,
        (student_email,)
      )
      
      student_info = cur.fetchone()
      cur.close()
      conn.close()
      
      if student_info:
        # Build robust mapping to support legacy/alternate schemas
        fn = (student_info.get('first_name') or '').strip()
        mn = (student_info.get('middle_name') or '').strip()
        ln = (student_info.get('last_name') or '').strip()
        sx = (student_info.get('suffix') or '').strip()
        full_name = fn
        if mn:
          full_name += f" {mn}"
        if ln:
          full_name += f" {ln}"
        if sx and sx != 'None':
          full_name += f" {sx}"

        # ID and identifiers
        student_no = student_info.get('student_no') or student_info.get('student_id')
        course_name = student_info.get('course_name') or student_info.get('program') or student_info.get('course')
        course_code = student_info.get('course_code')
        # Year level normalization
        yl_name = student_info.get('year_level_name')
        yl = student_info.get('year_level')
        if not yl_name and yl:
          try:
            num = int(str(yl).strip().split()[0])
            yl_name = f"Year {num}"
          except Exception:
            # If already like '1st Year', keep as-is
            yl_name = str(yl)
        mobile = student_info.get('mobile') or student_info.get('contact_no')
        created_at = None
        try:
          ca = student_info.get('created_at')
          if ca:
            created_at = ca.strftime('%Y-%m-%d')
        except Exception:
          created_at = None

        return jsonify({
          "ok": True,
          "student_info": {
            "id": student_info.get('id'),
            "student_no": student_no,
            "full_name": full_name.strip() or None,
            "first_name": fn or None,
            "middle_name": mn or None,
            "last_name": ln or None,
            "suffix": sx or None,
            "course_code": course_code,
            "course_name": course_name,
            "course": course_name,  # Backward compatibility
            "year_level": yl,
            "year_level_name": yl_name,
            "email": student_info.get('email'),
            "mobile": mobile,
            "gender": student_info.get('gender'),
            "address": student_info.get('address'),
            "nationality": student_info.get('nationality') or "Filipino",
            "created_at": created_at
          }
        })
      else:
        return jsonify({"ok": False, "message": "Student not found"}), 404
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/student/clearance')
  def api_student_clearance_overview():
    try:
      student_email = session.get('student_email')
      if not student_email:
        return jsonify({"ok": False, "message": "No student session found (HTTP 401)"}), 401
      cur, conn = mysql.cursor()
      # Find student and latest request
      cur.execute("SELECT id FROM students WHERE email=%s", (student_email,))
      stu = cur.fetchone()
      if not stu:
        cur.close()
        conn.close()
        return jsonify({"ok": True, "data": {"has_request": False }})
      student_id = stu['id'] if stu else None
      cur.execute("""
        SELECT id, status, created_at, updated_at, pickup_date
        FROM clearance_requests
        WHERE student_id = %s
        ORDER BY created_at DESC
        LIMIT 1
      """, (student_id,))
      req = cur.fetchone()
      if not req:
        cur.close()
        conn.close()
        return jsonify({"ok": True, "data": {"has_request": False }})
      request_id = req['id']
      cur.execute("""
        SELECT office, status, signed_by, signed_at, rejection_reason
        FROM clearance_signatories
        WHERE request_id = %s
        ORDER BY id ASC
      """, (request_id,))
      sigs = cur.fetchall() or []
      cur.close()
      conn.close()
      return jsonify({
        "ok": True,
        "data": {
          "has_request": True,
          "request": {"id": request_id, "status": req['status'], "created_at": req['created_at'], "updated_at": req['updated_at']},
          "signatories": sigs
        }
      })
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/student/clearance', methods=['GET'])
  def api_student_clearance_with_status():
    """Get student clearance requests with status filter"""
    try:
      student_email = session.get('student_email')
      if not student_email:
        return jsonify({"ok": False, "message": "No student session found"}), 401
      
      status = request.args.get('status', '').strip().lower()
      cur, conn = mysql.cursor()
      
      # Find student
      cur.execute("SELECT id FROM students WHERE email = %s", (student_email,))
      stu = cur.fetchone()
      if not stu:
        cur.close()
        conn.close()
        return jsonify({"ok": True, "data": []})
      
      student_id = stu['id']
      
      # Build query based on status
      if status == 'pending':
        cur.execute("""
          SELECT cr.id, cr.student_id, cr.status, cr.fulfillment_status, cr.document_type, cr.documents, cr.purposes, 
                 cr.created_at, cr.updated_at, cr.pickup_date, cr.payment_receipt, cr.payment_method, 
                 cr.payment_amount, cr.reference_number, cr.receipt_status,
                 s.first_name, s.last_name, s.student_no
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE cr.student_id = %s AND (cr.fulfillment_status = 'Pending' OR cr.fulfillment_status IS NULL)
          ORDER BY cr.created_at DESC
        """, (student_id,))
      elif status == 'approved':
        # Show processing documents from document_requests table (hybrid approach)
        cur.execute("""
          SELECT dr.id, dr.student_id, dr.status, 'Processing' as fulfillment_status, dr.document_type, dr.purpose as documents, dr.purpose as purposes, 
                 dr.created_at, dr.updated_at, dr.pickup_date, NULL as payment_receipt, NULL as payment_method, 
                 NULL as payment_amount, NULL as reference_number, NULL as receipt_status,
                 s.first_name, s.last_name, s.student_no, dr.clearance_request_id
          FROM document_requests dr
          JOIN students s ON s.id = dr.student_id
          WHERE dr.student_id = %s AND dr.status = 'Processing'
          
          UNION ALL
          
          SELECT cr.id, cr.student_id, cr.status, cr.fulfillment_status, cr.document_type, cr.documents, cr.purposes, 
                 cr.created_at, cr.updated_at, cr.pickup_date, cr.payment_receipt, cr.payment_method, 
                 cr.payment_amount, cr.reference_number, cr.receipt_status,
                 s.first_name, s.last_name, s.student_no, NULL as clearance_request_id
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE cr.student_id = %s AND cr.fulfillment_status = 'Approved' AND cr.id NOT IN (
            SELECT DISTINCT clearance_request_id FROM document_requests WHERE clearance_request_id IS NOT NULL AND student_id = %s
          )
          ORDER BY created_at DESC
        """, (student_id, student_id, student_id))
      elif status == 'rejected':
        cur.execute("""
          SELECT cr.id, cr.student_id, cr.status, cr.fulfillment_status, cr.document_type, cr.documents, cr.purposes, 
                 cr.created_at, cr.updated_at, cr.pickup_date, cr.payment_receipt, cr.payment_method, 
                 cr.payment_amount, cr.reference_number, cr.receipt_status,
                 s.first_name, s.last_name, s.student_no
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE cr.student_id = %s AND cr.fulfillment_status = 'Rejected'
          ORDER BY cr.created_at DESC
        """, (student_id,))
      elif status == 'completed':
        # Show completed documents from document_requests table (hybrid approach)
        cur.execute("""
          SELECT dr.id, dr.student_id, dr.status, 'Released' as fulfillment_status, dr.document_type, dr.purpose as documents, dr.purpose as purposes, 
                 dr.created_at, dr.updated_at, dr.pickup_date, NULL as payment_receipt, NULL as payment_method, 
                 NULL as payment_amount, NULL as reference_number, NULL as receipt_status,
                 s.first_name, s.last_name, s.student_no, dr.clearance_request_id
          FROM document_requests dr
          JOIN students s ON s.id = dr.student_id
          WHERE dr.student_id = %s AND (dr.status = 'Completed' OR dr.status = 'Released')
          
          UNION ALL
          
          SELECT cr.id, cr.student_id, cr.status, cr.fulfillment_status, cr.document_type, cr.documents, cr.purposes, 
                 cr.created_at, cr.updated_at, cr.pickup_date, cr.payment_receipt, cr.payment_method, 
                 cr.payment_amount, cr.reference_number, cr.receipt_status,
                 s.first_name, s.last_name, s.student_no, NULL as clearance_request_id
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE cr.student_id = %s AND cr.fulfillment_status = 'Released' AND cr.id NOT IN (
            SELECT DISTINCT clearance_request_id FROM document_requests WHERE clearance_request_id IS NOT NULL AND student_id = %s
          )
          ORDER BY created_at DESC
        """, (student_id, student_id, student_id))
      elif status == 'processing':
        # Show processing documents from document_requests table
        cur.execute("""
          SELECT dr.id, dr.student_id, dr.status, 'Processing' as fulfillment_status, dr.document_type, dr.purpose as documents, dr.purpose as purposes, 
                 dr.created_at, dr.updated_at, dr.pickup_date, NULL as payment_receipt, NULL as payment_method, 
                 NULL as payment_amount, NULL as reference_number, NULL as receipt_status,
                 s.first_name, s.last_name, s.student_no, dr.clearance_request_id
          FROM document_requests dr
          JOIN students s ON s.id = dr.student_id
          WHERE dr.student_id = %s AND dr.status = 'Processing'
          ORDER BY dr.created_at DESC
        """, (student_id,))
      else:
        # Return all requests if no status specified
        cur.execute("""
          SELECT cr.id, cr.student_id, cr.status, cr.fulfillment_status, cr.document_type, cr.documents, cr.purposes, 
                 cr.created_at, cr.updated_at, cr.pickup_date, cr.payment_receipt, cr.payment_method, 
                 cr.payment_amount, cr.reference_number, cr.receipt_status,
                 s.first_name, s.last_name, s.student_no
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE cr.student_id = %s
          ORDER BY cr.created_at DESC
        """, (student_id,))
      
      requests = cur.fetchall()
      cur.close()
      conn.close()
      
      # Format the data for the frontend
      formatted_requests = []
      for req in requests:
        formatted_requests.append({
          'id': req['id'],
          'request_id': req['id'],
          'student_id': req['student_id'],
          'student_name': f"{req['first_name']} {req['last_name']}",
          'status': req['status'],
          'fulfillment_status': req['fulfillment_status'],
          'document_type': req['document_type'],
          'documents': req['documents'],
          'purposes': req['purposes'],
          'created_at': req['created_at'].isoformat() if req['created_at'] else None,
          'updated_at': req['updated_at'].isoformat() if req['updated_at'] else None,
          'pickup_date': req['pickup_date'].isoformat() if req['pickup_date'] else None,
          'payment_receipt': req['payment_receipt'],
          'payment_method': req['payment_method'],
          'payment_amount': float(req['payment_amount']) if req['payment_amount'] else None,
          'reference_number': req['reference_number'],
          'receipt_status': req['receipt_status']
        })
      
      return jsonify({"ok": True, "data": formatted_requests})
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # List all requests for the current student (for status badges/UI)
  @app.route('/api/student/existing-requests')
  def api_student_existing_requests():
    """Get student's recent requests for duplicate prevention"""
    try:
      student_email = session.get('student_email')
      if not student_email:
        return jsonify({"ok": False, "message": "No student session found"}), 401
      
      cur, conn = mysql.cursor()
      cur.execute("SELECT id FROM students WHERE email = %s", (student_email,))
      stu = cur.fetchone()
      if not stu:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Student not found"}), 404
      
      # Get recent requests (last 30 days)
      cur.execute("""
        SELECT id, status, document_type, documents, purposes, created_at
        FROM clearance_requests 
        WHERE student_id = %s 
          AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        ORDER BY created_at DESC
        LIMIT 10
      """, (stu['id'],))
      
      requests = cur.fetchall()
      cur.close()
      conn.close()
      
      # Format the data
      formatted_requests = []
      for req in requests:
        formatted_requests.append({
          'id': req['id'],
          'status': req['status'],
          'document_type': req['document_type'],
          'documents': json.loads(req['documents'] or '[]'),
          'purposes': json.loads(req['purposes'] or '[]'),
          'created_at': req['created_at'].isoformat() if req['created_at'] else None
        })
      
      return jsonify({"ok": True, "requests": formatted_requests})
      
    except Exception as e:
      return jsonify({"ok": False, "message": f"Error getting existing requests: {str(e)}"}), 500

  @app.route('/api/student/requests')
  def api_student_requests():
    try:
      # Collect results here so we can still return partial/empty data if something fails
      requests_payload = []
      # Helper to safely serialize datetime values returned from MySQL
      def _dt(v):
        try:
          from datetime import datetime
          if isinstance(v, datetime):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
          pass
        return v
      # Helper to safely serialize Decimal and other numeric types
      def _num(v):
        try:
          from decimal import Decimal
          if isinstance(v, Decimal):
            return float(v)
        except Exception:
          pass
        return v
      # Recursive normalizer for nested JSON-able structures
      def _normalize_json(value):
        try:
          from datetime import datetime
          from decimal import Decimal
          import json as _json
          if isinstance(value, dict):
            return {k: _normalize_json(v) for k, v in value.items()}
          if isinstance(value, list):
            return [_normalize_json(v) for v in value]
          if isinstance(value, tuple):
            return tuple(_normalize_json(v) for v in value)
          if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
          if isinstance(value, Decimal):
            return float(value)
          # Decode bytes-like into string and parse JSON if applicable
          if isinstance(value, (bytes, bytearray, memoryview)):
            try:
              decoded = bytes(value).decode('utf-8', errors='ignore')
              # Try to parse as JSON; if fails, return decoded string
              try:
                return _normalize_json(_json.loads(decoded))
              except Exception:
                return decoded
            except Exception:
              return str(value)
          return value
        except Exception:
          return value
      student_email = session.get('student_email')
      if not student_email:
        return jsonify({"ok": False, "message": "No student session found (HTTP 401)"}), 401
      cur, conn = mysql.cursor()
      cur.execute("SELECT id FROM students WHERE email=%s", (student_email,))
      stu = cur.fetchone()
      if not stu:
        cur.close()
        conn.close()
        return jsonify({"ok": True, "requests": []})
      student_id = stu['id']
      # --- Fetch clearance requests (pre-registrar) ---
      # If we have a student_id, use it; otherwise fall back to joining by email
      if student_id:
        cur.execute(
          """
          SELECT cr.id, cr.status, cr.fulfillment_status, cr.registrar_status, cr.document_type, cr.documents, cr.purposes, cr.reason,
                 cr.created_at AS date_requested, cr.updated_at, cr.payment_method, cr.payment_amount,
                 cr.pickup_date, cr.payment_receipt, cr.payment_receipt_s3_url, cr.payment_receipt_s3_key,
                 CASE WHEN cr.payment_receipt IS NOT NULL OR cr.payment_receipt_s3_url IS NOT NULL THEN 'has_receipt' ELSE NULL END as receipt_status,
                 s.first_name, s.last_name, s.middle_name, s.course_name, s.course_code, s.year_level, s.year_level_name,
                 CASE WHEN cf.id IS NOT NULL THEN 'has_files' ELSE NULL END as file_status,
                 COUNT(cf.id) as file_count
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          LEFT JOIN clearance_files cf ON cf.clearance_request_id = cr.id
          WHERE cr.student_id = %s
          GROUP BY cr.id, cr.status, cr.fulfillment_status, cr.registrar_status, cr.document_type, cr.documents, cr.purposes, cr.reason,
                   cr.created_at, cr.updated_at, cr.payment_method, cr.payment_amount, cr.pickup_date, cr.payment_receipt, 
                   cr.payment_receipt_s3_url, cr.payment_receipt_s3_key, s.first_name, s.last_name, s.middle_name, 
                   s.course_name, s.course_code, s.year_level, s.year_level_name
          ORDER BY cr.created_at DESC
          """,
          (student_id,)
        )
      else:
        cur.execute(
          """
          SELECT cr.id, cr.status, cr.fulfillment_status, cr.registrar_status, cr.document_type, cr.documents, cr.purposes, cr.reason,
                 cr.created_at AS date_requested, cr.updated_at, cr.payment_method, cr.payment_amount,
                 cr.pickup_date, cr.payment_receipt, cr.payment_receipt_s3_url, cr.payment_receipt_s3_key,
                 CASE WHEN cr.payment_receipt IS NOT NULL OR cr.payment_receipt_s3_url IS NOT NULL THEN 'has_receipt' ELSE NULL END as receipt_status,
                 s.first_name, s.last_name, s.middle_name, s.course_name, s.course_code, s.year_level, s.year_level_name,
                 CASE WHEN cf.id IS NOT NULL THEN 'has_files' ELSE NULL END as file_status,
                 COUNT(cf.id) as file_count
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          LEFT JOIN clearance_files cf ON cf.clearance_request_id = cr.id
          WHERE s.email = %s
          GROUP BY cr.id, cr.status, cr.fulfillment_status, cr.registrar_status, cr.document_type, cr.documents, cr.purposes, cr.reason,
                   cr.created_at, cr.updated_at, cr.payment_method, cr.payment_amount, cr.pickup_date, cr.payment_receipt, 
                   cr.payment_receipt_s3_url, cr.payment_receipt_s3_key, s.first_name, s.last_name, s.middle_name, 
                   s.course_name, s.course_code, s.year_level, s.year_level_name
          ORDER BY cr.created_at DESC
          """,
          (student_email,)
        )
      clearance_rows = cur.fetchall() or []

      # --- Fetch document requests (post-auto-transfer/registrar processing) ---
      if student_id:
        cur.execute(
          """
          SELECT dr.id, dr.status, dr.document_type, dr.purpose, dr.created_at AS date_requested, dr.updated_at,
                 dr.reference_number, dr.completed_at, dr.pickup_date,
                 s.first_name, s.last_name, s.middle_name, s.course_name, s.course_code, s.year_level, s.year_level_name
          FROM document_requests dr
          JOIN students s ON s.id = dr.student_id
          WHERE dr.student_id = %s
          ORDER BY dr.created_at DESC
          """,
          (student_id,)
        )
      else:
        cur.execute(
          """
          SELECT dr.id, dr.status, dr.document_type, dr.purpose, dr.created_at AS date_requested, dr.updated_at,
                 dr.reference_number, dr.completed_at, dr.pickup_date,
                 s.first_name, s.last_name, s.middle_name, s.course_name, s.course_code, s.year_level, s.year_level_name
          FROM document_requests dr
          JOIN students s ON s.id = dr.student_id
          WHERE s.email = %s
          ORDER BY dr.created_at DESC
          """,
          (student_email,)
        )
      document_rows = cur.fetchall() or []
      # Prepare payload list we will return
      # requests_payload initialized above

      # Attach signatories for newest clearance request (if any) for convenience
      sigs = []
      if clearance_rows:
        latest_id = clearance_rows[0]['id']
        cur.execute(
          """
          SELECT office, status, signed_by, signed_at, rejection_reason
          FROM clearance_signatories
          WHERE request_id = %s
          ORDER BY id ASC
          """,
          (latest_id,)
        )
        sigs = cur.fetchall() or []
        # Normalize nested signatory rows for JSON (e.g., datetime fields)
        try:
          normalized_sigs = []
          for s in sigs:
            normalized = dict(s)
            if 'signed_at' in normalized:
              normalized['signed_at'] = _dt(normalized.get('signed_at'))
            normalized_sigs.append(normalized)
          sigs = normalized_sigs
        except Exception:
          pass

        # Convert rows to plain dicts – clearance side
        for r in clearance_rows:
          # Parse JSON text fields to Python lists/strings where applicable
          try:
            import json as _json
            parsed_documents = None
            if r.get('documents') is not None:
              parsed_documents = _json.loads(r['documents']) if isinstance(r['documents'], (str, bytes)) else r['documents']
            parsed_purposes = None
            if r.get('purposes') is not None:
              parsed_purposes = _json.loads(r['purposes']) if isinstance(r['purposes'], (str, bytes)) else r['purposes']
            
          except Exception:
            parsed_documents = r.get('documents')
            parsed_purposes = r.get('purposes')
          payload = {
            "id": r['id'],
            "status": 'Completed' if r.get('file_status') == 'has_files' and r.get('file_count', 0) > 0 else r.get('registrar_status', r.get('fulfillment_status', r['status'])),  # Use file presence to determine completion
            "clearance_status": 'Completed' if r.get('file_status') == 'has_files' and r.get('file_count', 0) > 0 else r.get('registrar_status', r.get('fulfillment_status', r['status'])),  # Use file presence for clearance status display
            "document_type": r.get('document_type'),
            "documents": parsed_documents,
            "purpose": parsed_purposes,
            "reason": r.get('reason'),
            "date_requested": _dt(r.get('date_requested')),
            "updated_at": _dt(r.get('updated_at')),
            "pickup_date": _dt(r.get('pickup_date')),
            "request_type": "clearance",  # Mark this as a clearance request
            # Payment details
            "payment_method": r.get('payment_method'),
            "payment_amount": _num(r.get('payment_amount')),
            "payment_verified": r.get('payment_verified'),
            "payment_details": _normalize_json(r.get('payment_details')),
            "reference_number": r.get('reference_number'),
            "payment_receipt": r.get('payment_receipt'),  # Include the actual receipt image data
            "payment_receipt_s3_url": r.get('payment_receipt_s3_url'),  # S3 URL for receipt image
            "payment_receipt_s3_key": r.get('payment_receipt_s3_key'),  # S3 key for receipt image
            "receipt_status": r.get('receipt_status'),  # Indicates if receipt exists without loading the actual data
            "file_status": r.get('file_status'),  # Indicates if registrar has uploaded files
            "file_count": r.get('file_count', 0),  # Number of files uploaded by registrar
            # Student details
            "student_name": f"{r.get('first_name', '')} {r.get('last_name', '')}".strip(),
            "first_name": r.get('first_name'),
            "last_name": r.get('last_name'),
            "middle_name": r.get('middle_name'),
            "course": r.get('course_name') or r.get('course_code'),
            "year_level": r.get('year_level_name') or (f"Year {r.get('year_level')}" if r.get('year_level') else ''),
          }
          if r['id'] == latest_id:
            payload['signatories'] = sigs
          # Ensure entire payload is JSON-safe
          requests_payload.append(_normalize_json(payload))

      # Always append normalized document requests so student sees items even without clearance rows
      for d in document_rows:
        # Normalize possible legacy fields for student details
        course_value = d.get('course_name') or d.get('course_code') or d.get('program') or d.get('course')
        year_level_name = d.get('year_level_name')
        if not year_level_name:
          yl = d.get('year_level')
          if yl:
            try:
              num = int(str(yl).strip().split()[0])
              year_level_name = f"Year {num}"
            except Exception:
              year_level_name = str(yl)
          else:
            year_level_name = ''
        payload = {
          "id": d['id'],
          "status": d.get('status'),  # Already represents Pending/Processing/Completed
          "clearance_status": None,
          "document_type": d.get('document_type'),
          "documents": d.get('document_type'),
          "purpose": d.get('purpose'),
          "reason": None,
          "date_requested": _dt(d.get('date_requested')),
          "updated_at": _dt(d.get('updated_at')),
          "completed_at": _dt(d.get('completed_at')),
          "pickup_date": _dt(d.get('pickup_date')),
          "request_type": "document",  # Mark this as a document request
          "clearance_request_id": d.get('clearance_request_id'),  # Link to original clearance request
          "reference_number": d.get('reference_number'),
          # Student details
          "student_name": f"{d.get('first_name', '')} {d.get('last_name', '')}".strip(),
          "first_name": d.get('first_name'),
          "last_name": d.get('last_name'),
          "middle_name": d.get('middle_name'),
          "course": course_value,
          "year_level": year_level_name,
        }
        # Ensure entire payload is JSON-safe
        requests_payload.append(_normalize_json(payload))

      # Group requests by student and document type to merge related requests
      consolidated_requests = []
      processed_clearance_ids = set()
      
      # First, process document requests (these take priority as they represent the final state)
      for req in requests_payload:
        if req.get('request_type') == 'document':
          # For document requests, try to find and merge with corresponding clearance request
          document_type = req.get('document_type', '').lower()
          student_name = req.get('student_name', '').lower()
          
          # Look for matching clearance request
          matching_clearance = None
          for clearance_req in requests_payload:
            if (clearance_req.get('request_type') == 'clearance' and 
                clearance_req.get('id') not in processed_clearance_ids and
                clearance_req.get('student_name', '').lower() == student_name):
              # Check if document types match or if clearance has the document type
              clearance_docs = clearance_req.get('documents', '')
              if isinstance(clearance_docs, list):
                clearance_docs = ' '.join(clearance_docs).lower()
              elif isinstance(clearance_docs, str):
                clearance_docs = clearance_docs.lower()
              
              if (document_type in clearance_docs or 
                  clearance_docs in document_type or
                  'clearance' in document_type or
                  'clearance' in clearance_docs):
                matching_clearance = clearance_req
                break
          
          # Merge document request with clearance request if found
          if matching_clearance:
            print(f"🔍 Consolidation: Merging document request {req.get('id')} with clearance request {matching_clearance.get('id')}")
            print(f"🔍 Consolidation: Clearance has payment_receipt: {bool(matching_clearance.get('payment_receipt'))}")
            print(f"🔍 Consolidation: Clearance has receipt_status: {matching_clearance.get('receipt_status')}")
            
            # Create consolidated request with both clearance and document info
            consolidated_req = {
              **req,  # Start with document request as base
              'clearance_status': 'Completed' if matching_clearance.get('file_status') == 'has_files' and matching_clearance.get('file_count', 0) > 0 else matching_clearance.get('clearance_status'),
              'clearance_id': matching_clearance.get('id'),
              'clearance_request_id': matching_clearance.get('id'),  # Add this for receipt viewing
              # Prioritize clearance request's documents and purposes over document request fields
              'documents': matching_clearance.get('documents', req.get('documents')),
              'purpose': matching_clearance.get('purpose', req.get('purpose')),
              'document_type': matching_clearance.get('document_type', req.get('document_type')),
              'payment_method': matching_clearance.get('payment_method'),
              'payment_amount': matching_clearance.get('payment_amount'),
              'payment_verified': matching_clearance.get('payment_verified'),
              'payment_details': matching_clearance.get('payment_details'),
              'reference_number': req.get('reference_number') or matching_clearance.get('reference_number'),
              'payment_receipt': matching_clearance.get('payment_receipt'),  # Include the actual receipt image data
              'receipt_status': matching_clearance.get('receipt_status'),
              'file_status': matching_clearance.get('file_status'),  # Include file status from clearance
              'file_count': matching_clearance.get('file_count', 0),  # Include file count from clearance
              'signatories': matching_clearance.get('signatories', []),
              'request_type': 'consolidated'  # Mark as consolidated
            }
            print(f"🔍 Consolidation: Final consolidated request clearance_request_id: {consolidated_req.get('clearance_request_id')}")
            consolidated_requests.append(consolidated_req)
            processed_clearance_ids.add(matching_clearance.get('id'))
          else:
            # No matching clearance found, add document request as-is
            consolidated_requests.append(req)
      
      # Then, add clearance requests that weren't matched with document requests
      for req in requests_payload:
        if (req.get('request_type') == 'clearance' and 
            req.get('id') not in processed_clearance_ids):
          consolidated_requests.append(req)
      
      requests_payload = consolidated_requests

      # Sort combined list by date_requested DESC so UI remains consistent
      try:
        from datetime import datetime
        def _to_ts(v):
          if not v:
            return 0
          if isinstance(v, (int, float)):
            return v
          try:
            # Expecting string from _dt helper: '%Y-%m-%d %H:%M:%S'
            return int(datetime.strptime(v, '%Y-%m-%d %H:%M:%S').timestamp())
          except Exception:
            return 0
        requests_payload.sort(key=lambda x: _to_ts(x.get('date_requested')), reverse=True)
      except Exception:
        pass
      cur.close()
      conn.close()
      return jsonify({"ok": True, "requests": requests_payload})
    except Exception as err:
      # Log full traceback for debugging
      try:
        import traceback
        traceback.print_exc()
      except Exception:
        pass
      # Be defensive: don't break the dashboard. Return empty list with a warning.
      try:
        _payload = requests_payload  # may or may not exist if failure was early
      except Exception:
        _payload = []
      return jsonify({
        "ok": True,
        "requests": _payload,
        "warning": "Some data could not be loaded. " + str(err)
      })

  @app.route('/api/fix-status-inconsistencies', methods=['POST'])
  def api_fix_status_inconsistencies():
    """Fix existing status inconsistencies between clearance_requests and document_requests tables.
    This is a one-time migration to fix records that were created before the status sync fix.
    """
    try:
      cur, conn = mysql.cursor()
      
      # Find all document requests that have a corresponding clearance request with mismatched status
      cur.execute("""
        SELECT 
          dr.id as document_id,
          dr.status as document_status,
          cr.id as clearance_id,
          cr.fulfillment_status as clearance_fulfillment_status
        FROM document_requests dr
        JOIN clearance_requests cr ON dr.clearance_request_id = cr.id
        WHERE dr.status IN ('Completed', 'Released', 'Unclaimed')
        AND cr.fulfillment_status != dr.status
      """)
      
      inconsistencies = cur.fetchall()
      
      if not inconsistencies:
        return jsonify({
          "ok": True, 
          "message": "No status inconsistencies found. All records are already in sync!",
          "records_fixed": 0
        })
      
      # Update clearance_requests.fulfillment_status to match document_requests.status
      cur.execute("""
        UPDATE clearance_requests cr
        JOIN document_requests dr ON dr.clearance_request_id = cr.id
        SET cr.fulfillment_status = dr.status, cr.updated_at = NOW()
        WHERE dr.status IN ('Completed', 'Released', 'Unclaimed')
        AND cr.fulfillment_status != dr.status
      """)
      
      rows_affected = cur.rowcount
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      
      return jsonify({
        "ok": True,
        "message": f"Successfully updated {rows_affected} records with status inconsistencies!",
        "records_fixed": rows_affected
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/logout', methods=['POST'])
  def api_logout():
    try:
      session.clear()
      return jsonify({"ok": True})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/dean/me')
  def api_dean_me():
    try:
      cur, conn = mysql.cursor()
      dean_email = session.get('dean_email')
      if not dean_email:
        return jsonify({"ok": False, "message": "No dean session found"}), 401
      
      cur.execute("""
        SELECT id, department, first_name, middle_name, last_name, suffix, 
               email, contact_no, gender, address, created_at
        FROM staff 
        WHERE email = %s AND status = 'Approved'
      """, (dean_email,))
      
      dean_info = cur.fetchone()
      cur.close()
      conn.close()
      
      if dean_info:
        full_name = f"{dean_info['first_name']}"
        if dean_info['middle_name']:
          full_name += f" {dean_info['middle_name']}"
        full_name += f" {dean_info['last_name']}"
        if dean_info['suffix'] and dean_info['suffix'] != 'None':
          full_name += f" {dean_info['suffix']}"
        
        return jsonify({
          "ok": True, 
          "dean_info": {
            "id": dean_info['id'],
            "full_name": full_name,
            "first_name": dean_info['first_name'],
            "middle_name": dean_info['middle_name'],
            "last_name": dean_info['last_name'],
            "suffix": dean_info['suffix'],
            "department": dean_info['department'],
            "email": dean_info['email'],
            "contact_no": dean_info['contact_no'],
            "gender": dean_info['gender'],
            "address": dean_info['address'],
            "created_at": dean_info['created_at'].strftime('%Y-%m-%d') if dean_info['created_at'] else None
          }
        })
      else:
        return jsonify({"ok": False, "message": "Dean not found"}), 404
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/dean/change-password', methods=['POST'])
  def api_dean_change_password():
    try:
      data = request.get_json()
      current_password = data.get('current_password', '').strip()
      new_password = data.get('new_password', '').strip()
      confirm_password = data.get('confirm_password', '').strip()
      
      if not all([current_password, new_password, confirm_password]):
        return jsonify({"ok": False, "message": "All fields are required"}), 400
      
      if new_password != confirm_password:
        return jsonify({"ok": False, "message": "New password and confirm password do not match"}), 400
      
      if len(new_password) < 6:
        return jsonify({"ok": False, "message": "New password must be at least 6 characters long"}), 400
      
      # Get dean email from session
      dean_email = session.get('dean_email')
      if not dean_email:
        return jsonify({"ok": False, "message": "No dean session found"}), 401
      
      cur, conn = mysql.cursor()
      
      # Verify current password
      cur.execute("SELECT password_hash FROM staff WHERE email = %s AND status = 'Approved'", (dean_email,))
      dean = cur.fetchone()
      
      if not dean or not check_password_hash(dean['password_hash'], current_password):
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Current password is incorrect"}), 400
      
      # Update password
      new_password_hash = generate_password_hash(new_password)
      cur.execute("UPDATE staff SET password_hash = %s WHERE email = %s", (new_password_hash, dean_email))
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      
      return jsonify({"ok": True, "message": "Password updated successfully"})
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/staff/change-password', methods=['POST'])
  def api_staff_change_password():
    try:
      data = request.get_json()
      current_password = (data.get('current_password', '') or '').strip()
      new_password = (data.get('new_password', '') or '').strip()
      confirm_password = (data.get('confirm_password', '') or '').strip()
      
      if not all([current_password, new_password, confirm_password]):
        return jsonify({"ok": False, "message": "All fields are required"}), 400
      
      if new_password != confirm_password:
        return jsonify({"ok": False, "message": "New password and confirm password do not match"}), 400
      
      if len(new_password) < 6:
        return jsonify({"ok": False, "message": "New password must be at least 6 characters long"}), 400
      
      staff_email = session.get('dean_email') or session.get('staff_email')
      if not staff_email:
        return jsonify({"ok": False, "message": "No staff session found"}), 401
      
      cur, conn = mysql.cursor()
      cur.execute("SELECT password_hash FROM staff WHERE email = %s AND status = 'Approved'", (staff_email,))
      staff = cur.fetchone()
      if not staff or not check_password_hash(staff['password_hash'], current_password):
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Current password is incorrect"}), 400
      
      new_password_hash = generate_password_hash(new_password)
      cur.execute("UPDATE staff SET password_hash = %s WHERE email = %s", (new_password_hash, staff_email))
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      
      return jsonify({"ok": True, "message": "Password updated successfully"})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Clearance APIs for Deans
  @app.route('/api/clearances/pending')
  def api_clearances_pending():
    dean = request.args.get('dean', '').strip().lower()
    dean_office_map = {
      'coed': 'Dean of CoEd',
      'hm': 'Dean of HM',
      'cs': 'Dean of CS',
    }
    office = dean_office_map.get(dean)
    try:
      cur, conn = mysql.cursor()
      if office:
        cur.execute(
          """
          SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name,
                 s.year_level, s.year_level_name, cr.id AS request_id, cs.id AS signatory_id, cs.status, cr.created_at,
                 cr.documents, cr.purposes
          FROM students s
          JOIN clearance_requests cr ON cr.student_id = s.id
          JOIN clearance_signatories cs ON cs.request_id = cr.id AND cs.office = %s
          WHERE cs.status = 'Pending'
          ORDER BY cr.created_at DESC
          """,
          (office,)
        )
      else:
        cur.execute(
          """
          SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name,
                 s.year_level, s.year_level_name, cr.id AS request_id, cr.status, cr.created_at
          FROM students s
          JOIN clearance_requests cr ON cr.student_id = s.id
          WHERE cr.status = 'Pending'
          ORDER BY cr.created_at DESC
          """)
      rows = cur.fetchall()
      cur.close()
      conn.close()
      for r in rows or []:
        try:
          docs = json.loads(r.get('documents') or '[]')
        except Exception:
          docs = []
        r['document'] = ", ".join(docs) if docs else '—'
        r['document_name'] = r['document']
        
        try:
          purposes = json.loads(r.get('purposes') or '[]')
        except Exception:
          purposes = []
        r['purpose'] = ", ".join(purposes) if purposes else '—'
      return jsonify({"ok": True, "data": rows})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/clearances/approved')
  def api_clearances_approved():
    dean = request.args.get('dean', '').strip().lower()
    dean_office_map = {
      'coed': 'Dean of CoEd',
      'hm': 'Dean of HM',
      'cs': 'Dean of CS',
    }
    office = dean_office_map.get(dean)
    try:
      cur, conn = mysql.cursor()
      if office:
        cur.execute(
          """
          SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name,
                 s.year_level, s.year_level_name, cr.id AS request_id, cs.id AS signatory_id, cr.status, cr.created_at, 
                 COALESCE(s.signature, '') AS signature
          FROM students s
          JOIN clearance_requests cr ON cr.student_id = s.id
          JOIN clearance_signatories cs ON cs.request_id = cr.id AND cs.office = %s
          WHERE cs.status = 'Approved'
          ORDER BY cs.signed_at DESC
          """,
          (office,)
        )
      else:
        cur.execute(
          """
          SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name,
                 s.year_level, s.year_level_name, cr.id AS request_id, cr.status, cr.created_at
          FROM students s
          JOIN clearance_requests cr ON cr.student_id = s.id
          WHERE cr.status = 'Approved'
          ORDER BY cr.updated_at DESC
          """
        )
      rows = cur.fetchall()
      cur.close()
      conn.close()
      return jsonify({"ok": True, "data": rows})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/clearances/rejected')
  def api_clearances_rejected():
    dean = request.args.get('dean', '').strip().lower()
    dean_office_map = {
      'coed': 'Dean of CoEd',
      'hm': 'Dean of HM',
      'cs': 'Dean of CS',
    }
    office = dean_office_map.get(dean)
    try:
      cur, conn = mysql.cursor()
      if office:
        cur.execute(
          """
          SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name,
                 s.year_level, s.year_level_name, cr.id AS request_id, cs.status, cs.rejection_reason, cr.created_at
          FROM students s
          JOIN clearance_requests cr ON cr.student_id = s.id
          JOIN clearance_signatories cs ON cs.request_id = cr.id AND cs.office = %s
          WHERE cs.status = 'Rejected'
          ORDER BY cs.updated_at DESC
          """,
          (office,)
        )
      else:
        cur.execute(
          """
          SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name,
                 s.year_level, s.year_level_name, cr.id AS request_id, cr.status, cr.created_at
          FROM students s
          JOIN clearance_requests cr ON cr.student_id = s.id
          WHERE cr.status = 'Rejected'
          ORDER BY cr.updated_at DESC
          """
        )
      rows = cur.fetchall()
      cur.close()
      conn.close()
      return jsonify({"ok": True, "data": rows})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  def _derive_dean_office(course_code: str) -> str:
    code = (course_code or '').upper()
    if code in ('BEED','BSED'):
      return 'Dean of CoEd'
    if code == 'BSHM':
      return 'Dean of HM'
    if code in ('BSCS','ACT'):
      return 'Dean of CS'
    return 'Dean of CS'

  @app.route('/api/clearance/check-duplicate', methods=['POST'])
  def api_check_duplicate_request():
    """Check if student has duplicate requests before submission"""
    try:
      student_email = session.get('student_email')
      if not student_email:
        return jsonify({"ok": False, "message": "No student session found"}), 401
      
      cur, conn = mysql.cursor()
      cur.execute("SELECT id FROM students WHERE email = %s", (student_email,))
      stu = cur.fetchone()
      if not stu:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Student not found"}), 404
      
      data = request.get_json()
      if not data:
        return jsonify({"ok": False, "message": "No data provided"}), 400
      
      documents = data.get('documents', [])
      purposes = data.get('purposes', [])
      document_type = data.get('document_type', 'Registrar Documents')
      
      is_duplicate, existing_request = _check_duplicate_request(cur, stu['id'], documents, purposes, document_type)
      
      cur.close()
      conn.close()
      
      if is_duplicate:
        existing_info = existing_request
        status_text = "pending" if existing_info['status'] == 'Pending' else "approved"
        created_date = existing_info['created_at'].strftime('%B %d, %Y at %I:%M %p') if existing_info['created_at'] else "recently"
        
        return jsonify({
          "ok": False,
          "is_duplicate": True,
          "message": f"You already have a {status_text} request for the same documents and purposes (Request #{existing_info['id']}, submitted {created_date}).",
          "existing_request": existing_info
        })
      
      return jsonify({"ok": True, "is_duplicate": False, "message": "No duplicate requests found"})
      
    except Exception as e:
      return jsonify({"ok": False, "message": f"Error checking duplicates: {str(e)}"}), 500

  @app.route('/api/clearance/request', methods=['POST'])
  def api_student_submit_clearance_request():
    try:
      print(f"🔍 CLEARANCE REQUEST: Starting clearance request submission")
      print(f"🔍 CLEARANCE REQUEST: Request method: {request.method}")
      print(f"🔍 CLEARANCE REQUEST: Content type: {request.content_type}")
      print(f"🔍 CLEARANCE REQUEST: Is JSON: {request.is_json}")
      print(f"🔍 CLEARANCE REQUEST: Files in request: {list(request.files.keys())}")
      print(f"🔍 CLEARANCE REQUEST: Form data keys: {list(request.form.keys())}")
      
      student_email = session.get('student_email')
      if not student_email:
        return jsonify({"ok": False, "message": "No student session found (HTTP 401)"}), 401
      cur, conn = mysql.cursor()
      # Get student id and course
      cur.execute("SELECT id, course_code FROM students WHERE email = %s", (student_email,))
      stu = cur.fetchone()
      if not stu:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Student not found"}), 404
      student_id = stu['id']
      dean_office = _derive_dean_office(stu.get('course_code'))
      
      if request.is_json:
        print(f"🔍 CLEARANCE REQUEST: Processing JSON request")
        try:
          payload = request.get_json(silent=True) or {}
        except Exception:
          payload = {}
        documents = payload.get('documents') or []
        purposes = payload.get('purposes') or []
        reason = (payload.get('reason') or '').strip() or None
        document_type = (payload.get('document_type') or 'Registrar Documents')
        payment_method = payload.get('payment_method', 'cash')
        payment_amount = payload.get('payment_amount', '50.00')
        receipt_data = None
        valid_id_data = None
        print(f"🔍 CLEARANCE REQUEST: JSON payload - documents: {documents}, purposes: {purposes}, payment_method: {payment_method}")
      else:
        print(f"🔍 CLEARANCE REQUEST: Processing form data request")
        documents = json.loads(request.form.get('documents', '[]'))
        purposes = json.loads(request.form.get('purposes', '[]'))
        reason = (request.form.get('reason') or '').strip() or None
        document_type = (request.form.get('document_type') or 'Registrar Documents')
        payment_method = request.form.get('payment_method', 'cash')
        payment_amount = request.form.get('payment_amount', '50.00')
        reference_number = request.form.get('reference_number', '').strip() or None
        print(f"🔍 CLEARANCE REQUEST: Form data - documents: {documents}, purposes: {purposes}, payment_method: {payment_method}")
        
        # Validate reference number format and check for duplicates if provided
        if reference_number:
          # Validate reference number format (7-16 digits)
          import re
          if not re.fullmatch(r'\d{7,16}', reference_number):
            return jsonify({"ok": False, "message": "Reference number must be 7-16 digits only"}), 400
          
          # Check for duplicate reference number
          cur.execute("SELECT id FROM clearance_requests WHERE reference_number = %s", (reference_number,))
          existing_request = cur.fetchone()
          if existing_request:
            return jsonify({"ok": False, "message": f"Reference number '{reference_number}' has already been used. Please use a different reference number."}), 400
        
        # Handle valid ID upload
        valid_id_data = None
        if 'valid_id' in request.files:
          valid_id_file = request.files['valid_id']
          if valid_id_file and valid_id_file.filename:
            # Validate the image first
            is_valid, validation_message = _validate_image(valid_id_file)
            if not is_valid:
              return jsonify({"ok": False, "message": f"Invalid valid ID image: {validation_message}"}), 400
            
            # Compress the image
            compressed_data = _compress_image(valid_id_file)
            valid_id_data = base64.b64encode(compressed_data).decode('utf-8')
        
        # Handle payment receipt upload
        receipt_data = None
        receipt_s3_url = None
        receipt_s3_key = None
        print(f"🔍 DEBUG: Checking for payment_receipt in files: {list(request.files.keys())}")
        if 'payment_receipt' in request.files:
          receipt_file = request.files['payment_receipt']
          print(f"🔍 DEBUG: Receipt file found: {receipt_file.filename if receipt_file else 'None'}")
          if receipt_file and receipt_file.filename:
            # Validate the image first
            is_valid, validation_message = _validate_image(receipt_file)
            if not is_valid:
              return jsonify({"ok": False, "message": f"Invalid receipt image: {validation_message}"}), 400
            
            # Compress the image
            compressed_data = _compress_image(receipt_file)
            print(f"🔍 DEBUG: Image compressed, size: {len(compressed_data)} bytes")
            
            # Try to upload to S3 first
            bucket_name = os.getenv('AWS_S3_BUCKET', 'irequest-receipts')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"receipts/request_{student_id}_{timestamp}.jpg"
            
            print(f"🔍 DEBUG: Attempting S3 upload for student_id={student_id}, bucket={bucket_name}, key={s3_key}")
            s3_url, s3_error = _upload_to_s3(compressed_data, bucket_name, s3_key)
            print(f"🔍 DEBUG: S3 upload result - URL: {s3_url}, Error: {s3_error}")
            if s3_url and not s3_error:
              # S3 upload successful
              receipt_s3_url = s3_url
              receipt_s3_key = s3_key
              receipt_data = None  # Don't store in database when S3 succeeds
              print(f"✅ Receipt uploaded to S3: {s3_url}")
            else:
              # Fallback to database storage
              print(f"⚠️ S3 upload failed: {s3_error}, falling back to database storage")
              receipt_data = base64.b64encode(compressed_data).decode('utf-8')
              receipt_s3_url = None
              receipt_s3_key = None
      
      # Check for duplicate requests before creating new one (TEMPORARILY DISABLED FOR TESTING)
      # is_duplicate, existing_request = _check_duplicate_request(cur, student_id, documents, purposes, document_type)
      # if is_duplicate:
      #   existing_info = existing_request
      #   status_text = "pending" if existing_info['status'] == 'Pending' else "approved"
      #   created_date = existing_info['created_at'].strftime('%B %d, %Y at %I:%M %p') if existing_info['created_at'] else "recently"
      #   
      #   return jsonify({
      #     "ok": False, 
      #     "message": f"You already have a {status_text} request for the same documents and purposes (Request #{existing_info['id']}, submitted {created_date}). Please wait for it to be processed or contact the registrar if you need to make changes."
      #   }), 400

      # Always create a NEW pending request (do not reuse existing)
      print(f"🔍 DEBUG: Storing in database - receipt_data: {'Yes' if receipt_data else 'No'}, receipt_s3_url: {receipt_s3_url}, receipt_s3_key: {receipt_s3_key}")
      cur.execute(
        """
        INSERT INTO clearance_requests (student_id, status, document_type, documents, purposes, reason, payment_method, payment_amount, payment_receipt, payment_receipt_s3_url, payment_receipt_s3_key, reference_number)
        VALUES (%s, 'Pending', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (student_id, document_type, json.dumps(documents), json.dumps(purposes), reason, payment_method, payment_amount, receipt_data, receipt_s3_url, receipt_s3_key, reference_number)
      )
      request_id = cur.lastrowid
      # Create signatory sequence for this request
      offices = [
        'Computer Laboratory',
        'Guidance Office',
        'Student Affairs',
        'Library',
        dean_office,
        'Accounting',
        'Property Custodian',
        'Registrar',
      ]
      for off in offices:
        # Auto-approve Computer Laboratory for non-CS courses
        if off == 'Computer Laboratory' and stu.get('course_code') != 'BSCS':
          cur.execute(
            "INSERT INTO clearance_signatories (request_id, office, status, signed_by, signed_at) VALUES (%s, %s, 'Approved', 'System Auto-Approval', NOW())",
            (request_id, off),
          )
        else:
          cur.execute(
            "INSERT INTO clearance_signatories (request_id, office, status) VALUES (%s, %s, 'Pending')",
            (request_id, off),
          )
      # Mark student flag
      cur.execute("UPDATE students SET has_clearance_request = 1, status = 'Pending' WHERE id = %s", (student_id,))
      
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({
        "ok": True, 
        "request_id": request_id
      })
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Fetch a specific clearance request with selected documents/purposes and signatories
  @app.route('/api/clearance/request/<int:req_id>')
  def api_get_clearance_request(req_id: int):
    try:
      student_email = session.get('student_email') or session.get('dean_email') or session.get('staff_email')
      if not student_email:
        # Allow viewing if logged in as any user type for simplicity
        pass
      
      # Use a single optimized query with JOINs to reduce database round trips
      cur, conn = mysql.cursor()
      cur.execute(
        """
        SELECT 
          cr.id, cr.student_id, cr.status, cr.document_type, cr.documents, cr.purposes, cr.reason,
          cr.created_at AS date_requested, cr.updated_at, cr.payment_method, cr.payment_amount,
          cr.payment_verified, cr.payment_details, cr.reference_number, cr.payment_receipt,
          cr.payment_receipt_s3_url, cr.payment_receipt_s3_key,
          s.first_name, s.middle_name, s.last_name, s.student_no, s.course_name, s.course_code,
          s.year_level, s.year_level_name
        FROM clearance_requests cr
        LEFT JOIN students s ON s.id = cr.student_id
        WHERE cr.id = %s
        """,
        (req_id,)
      )
      req = cur.fetchone()
      if not req:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Request not found"}), 404

      # Get signatories in a separate query (can't be easily joined due to multiple rows)
      cur.execute(
        """
        SELECT office, status, signed_by, signed_at, rejection_reason
        FROM clearance_signatories
        WHERE request_id = %s
        ORDER BY id ASC
        """,
        (req_id,)
      )
      sigs = cur.fetchall() or []
      cur.close()
      conn.close()

      # Decode JSON fields
      def _parse_json(val):
        try:
          return json.loads(val) if val else []
        except Exception:
          return []

      payload = {
        "id": req['id'],
        "student_id": req['student_id'],
        "status": req['status'],
        "document_type": req.get('document_type') or 'Registrar Documents',
        "documents": _parse_json(req.get('documents')),
        "purpose": _parse_json(req.get('purposes')),
        "reason": req.get('reason'),
        "date_requested": req['date_requested'],
        "updated_at": req['updated_at'],
        "payment_method": req.get('payment_method'),
        "payment_amount": req.get('payment_amount'),
        "payment_verified": req.get('payment_verified'),
        "payment_details": req.get('payment_details'),
        "reference_number": req.get('reference_number'),
        "payment_receipt": req.get('payment_receipt'),
        "payment_receipt_s3_url": req.get('payment_receipt_s3_url'),
        "payment_receipt_s3_key": req.get('payment_receipt_s3_key'),
        "student_name": (
          f"{(req.get('first_name') or '').strip()} "
          f"{((req.get('middle_name') or '').strip() + ' ') if (req.get('middle_name') or '').strip() else ''}"
          f"{(req.get('last_name') or '').strip()}"
        ).strip() or None,
        "course": req.get('course_name') or req.get('course_code'),
        "course_code": req.get('course_code'),
        "year_level": req.get('year_level_name') or req.get('year_level'),
        "student_no": req.get('student_no'),
      }
      return jsonify({"ok": True, "request": payload, "signatories": sigs})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Registrar-facing endpoints using signatory tables, including selected documents
  @app.route('/api/registrar/pending')
  def api_registrar_pending():
    try:
      cur, conn = mysql.cursor()
      cur.execute(
        """
        SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name, s.year_level, s.year_level_name,
               cr.id AS request_id, cr.documents, cr.purposes, cr.document_type, cr.created_at
        FROM clearance_requests cr
        JOIN students s ON s.id = cr.student_id
        WHERE cr.fulfillment_status = 'Pending'
          AND cr.status = 'Approved'
        ORDER BY cr.created_at ASC
        """
      )
      rows = cur.fetchall() or []
      cur.close()
      conn.close()
      data = []
      for r in rows:
        try:
          docs = json.loads(r.get('documents') or '[]')
        except Exception:
          docs = []
        data.append({
          "id": r['student_id'],
          "student_id": r['student_id'],
          "first_name": r['first_name'],
          "last_name": r['last_name'],
          "course_code": r.get('course_code'),
          "course_name": r.get('course_name'),
          "year_level": r.get('year_level'),
          "year_level_name": r.get('year_level_name'),
          "document_name": ", ".join(docs) if docs else '—',
          "document": ", ".join(docs) if docs else '—',
          "purposes": json.loads(r.get('purposes') or '[]') if r.get('purposes') else [],
          "document_type": r.get('document_type') or 'Registrar Documents',
          "request_id": r.get('request_id'),
          "payment_method": r.get('payment_method'),
          "payment_amount": r.get('payment_amount'),
          "payment_verified": r.get('payment_verified'),
          "payment_details": r.get('payment_details'),
          "reference_number": r.get('reference_number'),
        })
      return jsonify({"ok": True, "data": data})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/released')
  def api_registrar_released():
    try:
      cur, conn = mysql.cursor()
      cur.execute(
        """
        SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name, s.year_level, s.year_level_name,
               cr.id AS request_id, cr.documents, cr.purposes, cr.document_type, cr.updated_at,
               s.signature
        FROM clearance_requests cr
        JOIN students s ON s.id = cr.student_id
        WHERE cr.fulfillment_status = 'Released'
          AND cr.status = 'Approved'
        ORDER BY cr.updated_at DESC
        """
      )
      rows = cur.fetchall() or []
      cur.close()
      conn.close()
      data = []
      for r in rows:
        try:
          docs = json.loads(r.get('documents') or '[]')
        except Exception:
          docs = []
        data.append({
          "id": r['student_id'],
          "student_id": r['student_id'],
          "first_name": r['first_name'],
          "last_name": r['last_name'],
          "course_code": r.get('course_code'),
          "course_name": r.get('course_name'),
          "year_level": r.get('year_level'),
          "year_level_name": r.get('year_level_name'),
          "document_name": ", ".join(docs) if docs else '—',
          "document": ", ".join(docs) if docs else '—',
          "signature": r.get('signature'),
          "purposes": json.loads(r.get('purposes') or '[]') if r.get('purposes') else [],
          "document_type": r.get('document_type') or 'Registrar Documents',
          "released_at": r.get('updated_at'),
        })
      return jsonify({"ok": True, "data": data})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/rejected')
  def api_registrar_rejected():
    try:
      cur, conn = mysql.cursor()
      cur.execute(
        """
        SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name, s.year_level, s.year_level_name,
               cr.id AS request_id, cr.documents, cr.purposes, cr.document_type, cr.updated_at
        FROM clearance_requests cr
        JOIN students s ON s.id = cr.student_id
        WHERE cr.fulfillment_status = 'Rejected'
          AND cr.status = 'Rejected'
        ORDER BY cr.updated_at DESC
        """
      )
      rows = cur.fetchall() or []
      cur.close()
      conn.close()
      data = []
      for r in rows:
        try:
          docs = json.loads(r.get('documents') or '[]')
        except Exception:
          docs = []
        data.append({
          "id": r['student_id'],
          "student_id": r['student_id'],
          "first_name": r['first_name'],
          "last_name": r['last_name'],
          "course_code": r.get('course_code'),
          "course_name": r.get('course_name'),
          "year_level": r.get('year_level'),
          "year_level_name": r.get('year_level_name'),
          "document_name": ", ".join(docs) if docs else '—',
          "document": ", ".join(docs) if docs else '—',
          "rejection_reason": "Rejected by Registrar",
          "purposes": json.loads(r.get('purposes') or '[]') if r.get('purposes') else [],
          "document_type": r.get('document_type') or 'Registrar Documents',
        })
      return jsonify({"ok": True, "data": data})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Alias for clarity in UI (Approved == Released for Registrar)
  @app.route('/api/registrar/approved')
  def api_registrar_approved():
    return api_registrar_released()

  # Generic signatory pending list by office (from session or query)
  @app.route('/api/signatories/pending')
  def api_signatories_pending():
    office = (request.args.get('office') or '').strip()
    if not office:
      dept = (session.get('staff_department') or '').strip().lower()
      office = {
        'computer laboratory': 'Computer Laboratory',
        'guidance office': 'Guidance Office',
        'student affairs': 'Student Affairs',
        'library': 'Library',
        'accounting': 'Accounting',
        'property custodian': 'Property Custodian',
        'registrar': 'Registrar',
      }.get(dept) or ''
      if not office and 'dean' in dept:
        office = {
          'dean of coed': 'Dean of CoEd',
          'dean of hm': 'Dean of HM',
          'dean of cs': 'Dean of CS',
        }.get(dept, '')
    try:
      cur, conn = mysql.cursor()
      cur.execute(
        """
        SELECT cs.id AS signatory_id,
               cr.id AS request_id,
               s.id AS student_id,
               s.first_name,
               s.last_name,
               s.course_code,
               s.course_name,
               s.year_level,
               s.year_level_name,
               cr.documents,
               cr.purposes,
               cr.payment_method,
               cr.payment_amount,
               cr.payment_verified,
               cr.payment_details,
               cr.payment_receipt,
               cr.reference_number,
               cs.office,
               cs.status,
               cr.created_at
        FROM clearance_signatories cs
        JOIN clearance_requests cr ON cr.id = cs.request_id
        JOIN students s ON s.id = cr.student_id
        WHERE cs.office = %s AND cs.status = 'Pending'
        ORDER BY cr.created_at ASC
        """,
        (office,)
      )
      rows = cur.fetchall()
      cur.close()
      conn.close()
      # Ensure documents and purposes are parsed to readable fields
      for r in rows or []:
        try:
          docs = json.loads(r.get('documents') or '[]')
        except Exception:
          docs = []
        r['document'] = ", ".join(docs) if docs else '—'
        r['document_name'] = r['document']
        
        try:
          purposes = json.loads(r.get('purposes') or '[]')
        except Exception:
          purposes = []
        r['purpose'] = ", ".join(purposes) if purposes else '—'
      return jsonify({"ok": True, "data": rows})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Generic signatory approved list by office (from session or query)
  @app.route('/api/signatories/approved')
  def api_signatories_approved():
    office = (request.args.get('office') or '').strip()
    if not office:
      dept = (session.get('staff_department') or '').strip().lower()
      office = {
        'computer laboratory': 'Computer Laboratory',
        'guidance office': 'Guidance Office',
        'student affairs': 'Student Affairs',
        'library': 'Library',
        'accounting': 'Accounting',
        'property custodian': 'Property Custodian',
        'registrar': 'Registrar',
      }.get(dept) or ''
      if not office and 'dean' in dept:
        office = {
          'dean of coed': 'Dean of CoEd',
          'dean of hm': 'Dean of HM',
          'dean of cs': 'Dean of CS',
        }.get(dept, '')
    try:
      cur, conn = mysql.cursor()
      cur.execute(
        """
        SELECT cs.id AS signatory_id, cr.id AS request_id, s.id AS student_id,
               s.first_name, s.last_name, s.course_code, s.course_name, s.year_level, s.year_level_name,
               cr.purposes, cr.payment_method, cr.payment_amount, cr.payment_details, cr.payment_receipt,
               s.signature AS signature, cs.signed_at
        FROM clearance_signatories cs
        JOIN clearance_requests cr ON cr.id = cs.request_id
        JOIN students s ON s.id = cr.student_id
        WHERE cs.office = %s AND cs.status = 'Approved' 
        AND cr.status != 'Converted to Document Request'
        ORDER BY cs.signed_at DESC
        """,
        (office,)
      )
      rows = cur.fetchall()
      cur.close()
      conn.close()
      for r in rows or []:
        try:
          purposes = json.loads(r.get('purposes') or '[]')
        except Exception:
          purposes = []
        r['purpose'] = ", ".join(purposes) if purposes else '—'
      return jsonify({"ok": True, "data": rows})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Generic signatory rejected list by office (from session or query)
  @app.route('/api/signatories/rejected')
  def api_signatories_rejected():
    office = (request.args.get('office') or '').strip()
    if not office:
      dept = (session.get('staff_department') or '').strip().lower()
      office = {
        'computer laboratory': 'Computer Laboratory',
        'guidance office': 'Guidance Office',
        'student affairs': 'Student Affairs',
        'library': 'Library',
        'accounting': 'Accounting',
        'property custodian': 'Property Custodian',
        'registrar': 'Registrar',
      }.get(dept) or ''
      if not office and 'dean' in dept:
        office = {
          'dean of coed': 'Dean of CoEd',
          'dean of hm': 'Dean of HM',
          'dean of cs': 'Dean of CS',
        }.get(dept, '')
    try:
      cur, conn = mysql.cursor()
      cur.execute(
        """
        SELECT cs.id AS signatory_id, cr.id AS request_id, s.id AS student_id,
               s.first_name, s.last_name, s.course_code, s.course_name, s.year_level, s.year_level_name,
               cr.purposes, cr.payment_method, cr.payment_amount, cr.payment_details, cr.payment_receipt,
               cs.rejection_reason, cs.updated_at
        FROM clearance_signatories cs
        JOIN clearance_requests cr ON cr.id = cs.request_id
        JOIN students s ON s.id = cr.student_id
        WHERE cs.office = %s AND cs.status = 'Rejected'
        ORDER BY cs.updated_at DESC
        """,
        (office,)
      )
      rows = cur.fetchall()
      cur.close()
      conn.close()
      for r in rows or []:
        try:
          purposes = json.loads(r.get('purposes') or '[]')
        except Exception:
          purposes = []
        r['purpose'] = ", ".join(purposes) if purposes else '—'
      return jsonify({"ok": True, "data": rows})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Duplicate legacy approve endpoint removed (using unified implementation below)

  # Duplicate legacy reject endpoint removed (using unified implementation below)

  # Staff profile
  @app.route('/api/staff/me')
  def api_staff_me():
    try:
      staff_dept = (session.get('staff_department') or '').strip()
      staff_email = (session.get('dean_email') or session.get('staff_email'))
      if not staff_email:
        # Return 200 with ok:false to avoid browser console red 401 noise on static dashboard loads
        return jsonify({"ok": False, "message": "No staff session found"})
      cur, conn = mysql.cursor()
      cur.execute(
        """
        SELECT id, department, first_name, middle_name, last_name, suffix,
               email, contact_no, gender, address, created_at
        FROM staff
        WHERE email = %s AND status = 'Approved'
        """,
        (staff_email,)
      )
      info = cur.fetchone()
      cur.close()
      conn.close()
      if not info:
        return jsonify({"ok": False, "message": "Staff not found"})
      full_name = f"{info['first_name']}" + (f" {info['middle_name']}" if info['middle_name'] else '') + f" {info['last_name']}" + (f" {info['suffix']}" if info['suffix'] and info['suffix'] != 'None' else '')
      return jsonify({
        "ok": True,
        "staff_info": {
          "id": info['id'],
          "full_name": full_name,
          "first_name": info['first_name'],
          "middle_name": info['middle_name'],
          "last_name": info['last_name'],
          "suffix": info['suffix'],
          "department": info['department'],
          "email": info['email'],
          "contact_no": info['contact_no'],
          "gender": info['gender'],
          "address": info['address'],
          "created_at": info['created_at'].strftime('%Y-%m-%d') if info['created_at'] else None
        }
      })
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  def _update_request_status_after_sign( cur, request_id: int ) -> None:
    # If any signatory rejected, request is Rejected
    cur.execute("SELECT COUNT(*) AS c FROM clearance_signatories WHERE request_id = %s AND status = 'Rejected'", (request_id,))
    if (cur.fetchone() or {}).get('c', 0) > 0:
      cur.execute("UPDATE clearance_requests SET status = 'Rejected', fulfillment_status = 'Rejected', registrar_status = 'Pending' WHERE id = %s", (request_id,))
      return
    
    # Check if all signatories are approved
    cur.execute("SELECT COUNT(*) AS c FROM clearance_signatories WHERE request_id = %s AND status != 'Approved'", (request_id,))
    if (cur.fetchone() or {}).get('c', 0) == 0:
      # All signatories approved - update request status to Approved
      cur.execute("UPDATE clearance_requests SET status = 'Approved', fulfillment_status = 'Approved', registrar_status = 'Pending' WHERE id = %s", (request_id,))
      # Auto-transfer to pending documents
      _auto_transfer_to_pending_documents(cur, request_id)

  def _auto_transfer_to_pending_documents(cur, request_id: int) -> None:
    """Auto-transfer approved clearance to pending documents when all offices are approved"""
    try:
      # Get clearance request details
      cur.execute("""
        SELECT cr.student_id, cr.documents, cr.purpose, cr.payment_method, cr.payment_amount, 
               cr.payment_details, cr.payment_verified, cr.created_at, cr.pickup_date
        FROM clearance_requests cr 
        WHERE cr.id = %s
      """, (request_id,))
      
      clearance_data = cur.fetchone()
      if not clearance_data:
        return
      
      student_id = clearance_data['student_id']
      
      # Check if document request already exists for this clearance
      cur.execute("""
        SELECT id FROM document_requests 
        WHERE student_id = %s AND clearance_request_id = %s
      """, (student_id, request_id))
      
      if cur.fetchone():
        return  # Already exists, don't create duplicate
      
      # Create document request from clearance
      documents = clearance_data['documents'] or 'Clearance Documents'
      if isinstance(documents, list):
        documents = ', '.join(documents)
      
      purpose = clearance_data['purpose'] or 'Clearance Processing'
      if isinstance(purpose, list):
        purpose = ', '.join(purpose)
      
      # Create the document request with proper linkage
      cur.execute("""
        INSERT INTO document_requests 
        (student_id, document_type, purpose, status, clearance_request_id, pickup_date, created_at, updated_at)
        VALUES (%s, %s, %s, 'Pending', %s, %s, NOW(), NOW())
      """, (student_id, documents, purpose, request_id, clearance_data.get('pickup_date')))
      
      # Log the auto-transfer event
      cur.execute("""
        INSERT INTO auto_transfer_logs 
        (clearance_request_id, document_request_id, student_id, transferred_at, reason)
        VALUES (%s, LAST_INSERT_ID(), %s, NOW(), 'All office clearances approved')
      """, (request_id, student_id))
      
    except Exception as e:
      print(f"Error in auto-transfer: {e}")
      # Don't raise exception to avoid breaking the main flow

  @app.route('/api/registrar/check-auto-transfers', methods=['GET'])
  def api_check_auto_transfers():
    """Check for recent auto-transfers to show notifications"""
    try:
      cur, conn = mysql.cursor()
      
      cur.execute("""
        SELECT atl.clearance_request_id, atl.document_request_id, atl.student_id, 
               atl.transferred_at, atl.reason,
               CONCAT(s.first_name, ' ', s.last_name) as student_name,
               cr.documents, cr.purposes
        FROM auto_transfer_logs atl
        JOIN students s ON s.id = atl.student_id
        JOIN clearance_requests cr ON cr.id = atl.clearance_request_id
        WHERE atl.transferred_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        ORDER BY atl.transferred_at DESC
        LIMIT 10
      """)
      
      transfers = cur.fetchall() or []
      cur.close()
      conn.close()
      
      return jsonify({
        "ok": True,
        "transfers": transfers,
        "count": len(transfers)
      })
      
    except Exception:
      return jsonify({"ok": True, "transfers": [], "count": 0})

  @app.route('/api/registrar/fix-missing-transfers', methods=['POST'])
  def api_fix_missing_transfers():
    """Fix any approved clearances that haven't been transferred to pending documents"""
    try:
      cur, conn = mysql.cursor()
      
      # Find approved clearances that don't have corresponding document requests
      cur.execute("""
        SELECT cr.id, cr.student_id, cr.documents, cr.purposes, cr.created_at
        FROM clearance_requests cr
        WHERE cr.status = 'Approved' 
          AND cr.fulfillment_status = 'Pending'
          AND NOT EXISTS (
            SELECT 1 FROM document_requests dr 
            WHERE dr.clearance_request_id = cr.id
          )
        ORDER BY cr.created_at ASC
      """)
      
      missing_transfers = cur.fetchall() or []
      
      fixed_count = 0
      for clearance in missing_transfers:
        try:
          _auto_transfer_to_pending_documents(cur, clearance['id'])
          fixed_count += 1
        except Exception as e:
          print(f"Error transferring clearance {clearance['id']}: {e}")
          continue
      
      cur.close()
      conn.close()
      
      return jsonify({
        "ok": True,
        "message": f"Fixed {fixed_count} missing transfers",
        "fixed_count": fixed_count,
        "total_found": len(missing_transfers)
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/documents')
  def api_registrar_documents():
    status = request.args.get('status', 'pending')
    try:
      cur, conn = mysql.cursor()
      
      if status == 'pending':
        # Return only document requests that are pending (simplify to avoid schema mismatches)
        try:
          cur.execute(
            """
            SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name, s.year_level, s.year_level_name,
                   dr.id AS request_id, dr.document_type AS documents, dr.purpose AS purposes, dr.document_type, dr.created_at
            FROM document_requests dr
            JOIN students s ON s.id = dr.student_id
            WHERE dr.status = 'Pending'
            ORDER BY dr.created_at DESC
            """
          )
        except Exception as err:
          # If pending query fails due to schema differences, respond gracefully
          try:
            cur.close()
            conn.close()
          except Exception:
            pass
          return jsonify({"ok": True, "data": [], "message": f"pending_list_disabled: {err}"})
      elif status == 'processing':
        cur.execute(
          """
          SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name, s.year_level, s.year_level_name,
                 dr.id AS request_id, dr.document_type AS documents, dr.purpose AS purposes, dr.document_type, dr.updated_at
          FROM document_requests dr
          JOIN students s ON s.id = dr.student_id
          WHERE dr.status = 'Processing'
          ORDER BY dr.updated_at DESC
          """
        )
      elif status == 'released':
        # Get documents that have been released
        cur.execute(
          """
          SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name, s.year_level, s.year_level_name,
                 cr.id AS request_id, cr.documents, cr.purposes, cr.document_type, cr.updated_at
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE cr.fulfillment_status = 'Released'
          ORDER BY cr.updated_at DESC
          """
        )
      elif status == 'unclaimed':
        # Optional: unclaimed documents list (if table/column not present, return empty)
        try:
          cur.execute(
            """
            SELECT dr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name,
                   s.course_code, s.course_name, s.year_level, s.year_level_name,
                   dr.document_type, dr.purpose, dr.updated_at AS released_at
            FROM document_requests dr
            JOIN students s ON s.id = dr.student_id
            WHERE dr.status = 'Unclaimed'
            ORDER BY dr.updated_at DESC
            """
          )
        except Exception:
          # If schema doesn't have Unclaimed, just return empty list
          cur.close()
          conn.close()
          return jsonify({"ok": True, "data": []})
      else:
        return jsonify({"ok": False, "message": "Invalid status parameter"}), 400
      
      rows = cur.fetchall() or []
      cur.close()
      conn.close()
      data = []
      for r in rows:
        try:
          docs = json.loads(r.get('documents') or '[]')
        except Exception:
          docs = []
        data.append({
          "id": r['student_id'],
          "student_id": r['student_id'],
          "request_id": r['request_id'],
          "first_name": r['first_name'],
          "last_name": r['last_name'],
          "student_name": f"{r['first_name']} {r['last_name']}",
          "course_code": r.get('course_code'),
          "course_name": r.get('course_name'),
          "year_level": r.get('year_level'),
          "year_level_name": r.get('year_level_name'),
          "document_name": ", ".join(docs) if docs else '—',
          "document": ", ".join(docs) if docs else '—',
          "document_type": r.get('document_type') or 'Registrar Documents',
          "purposes": json.loads(r.get('purposes') or '[]') if r.get('purposes') else [],
          "created_at": r.get('created_at'),
          "updated_at": r.get('updated_at'),
          "request_type": r.get('request_type'),
          "auto_transferred_at": r.get('auto_transferred_at'),
          "clearance_request_id": r.get('clearance_request_id'),
          "clearance_status": r.get('clearance_status')
        })
      return jsonify({"ok": True, "data": data})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/processing')
  def api_registrar_processing():
    try:
      cur, conn = mysql.cursor()
      cur.execute(
        """
        SELECT s.id AS student_id, s.student_no, s.first_name, s.last_name, s.course_code, s.course_name, s.year_level, s.year_level_name,
               cr.id AS request_id, cr.documents, cr.purposes, cr.document_type, cr.updated_at
        FROM clearance_requests cr
        JOIN students s ON s.id = cr.student_id
        WHERE cr.fulfillment_status = 'Processing'
        ORDER BY cr.updated_at DESC
        """
      )
      rows = cur.fetchall() or []
      cur.close()
      conn.close()
      data = []
      for r in rows:
        try:
          docs = json.loads(r.get('documents') or '[]')
        except Exception:
          docs = []
        data.append({
          "id": r['student_id'],
          "student_id": r['student_id'],
          "first_name": r['first_name'],
          "last_name": r['last_name'],
          "course_code": r.get('course_code'),
          "course_name": r.get('course_name'),
          "year_level": r.get('year_level'),
          "year_level_name": r.get('year_level_name'),
          "document_name": ", ".join(docs) if docs else '—',
          "document": ", ".join(docs) if docs else '—',
          "purposes": json.loads(r.get('purposes') or '[]') if r.get('purposes') else [],
          "document_type": r.get('document_type') or 'Registrar Documents',
        })
      return jsonify({"ok": True, "data": data})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/mark-processing', methods=['POST'])
  def api_registrar_mark_processing():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    try:
      if not request_id:
        return jsonify({"ok": False, "message": "Missing request_id"}), 400
      cur, conn = mysql.cursor()
      # Update both status and fulfillment_status to 'Processing' for proper flow
      # Also update registrar_status to 'Processing' for student dashboard sync
      cur.execute("UPDATE clearance_requests SET status='Processing', fulfillment_status='Processing', registrar_status='Processing' WHERE id=%s", (request_id,))
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/mark-released', methods=['POST'])
  def api_registrar_mark_released():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    try:
      if not request_id:
        return jsonify({"ok": False, "message": "Missing request_id"}), 400
      cur, conn = mysql.cursor()
      # Update both status and fulfillment_status to 'Released' for proper flow
      # Also update registrar_status to 'Complete' for student dashboard sync
      cur.execute("UPDATE clearance_requests SET status='Released', fulfillment_status='Released', registrar_status='Complete' WHERE id=%s", (request_id,))
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/mark-unclaimed', methods=['POST'])
  def api_registrar_mark_unclaimed():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    try:
      if not request_id:
        return jsonify({"ok": False, "message": "Missing request_id"}), 400
      cur, conn = mysql.cursor()
      # Update both status and fulfillment_status to 'Unclaimed' for proper flow
      # Also update registrar_status to 'Complete' for student dashboard sync
      cur.execute("UPDATE clearance_requests SET status='Unclaimed', fulfillment_status='Unclaimed', registrar_status='Complete' WHERE id=%s", (request_id,))
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/release', methods=['POST'])
  def api_registrar_release():
    data = request.get_json(silent=True) or {}
    student_id = data.get('student_id')
    signature = data.get('signature')
    registrar = data.get('registrar') or (session.get('admin_name') or 'Registrar')
    
    print(f"🔍 Registrar Release Debug: student_id={student_id}, registrar={registrar}")
    
    try:
      if not student_id:
        print("❌ Registrar Release Error: Missing student_id")
        return jsonify({"ok": False, "message": "Missing student_id"}), 400
      
      cur, conn = mysql.cursor()
      print(f"🔍 Database connection established for student_id: {student_id}")
      
      # Find the latest registrar signatory for the student's latest request
      cur.execute("""
        SELECT cs.id AS signatory_id, cs.request_id
        FROM clearance_signatories cs
        JOIN clearance_requests cr ON cr.id = cs.request_id
        WHERE cr.student_id = %s AND cs.office = 'Registrar'
        ORDER BY cs.id DESC LIMIT 1
      """, (student_id,))
      row = cur.fetchone()
      
      print(f"🔍 Found registrar signatory: {row}")
      
      if not row:
        cur.close()
        conn.close()
        print(f"❌ Registrar Release Error: No registrar signatory found for student_id: {student_id}")
        return jsonify({"ok": False, "message": "Registrar signatory not found"}), 404
      
      signatory_id = row['signatory_id']
      request_id = row['request_id']
      
      print(f"🔍 Updating signatory {signatory_id} for request {request_id}")
      
      # Approve registrar signatory
      cur.execute("UPDATE clearance_signatories SET status='Approved', signed_by=%s, signed_at=NOW() WHERE id=%s", (registrar, signatory_id))
      
      if signature:
        print(f"🔍 Updating student signature for student_id: {student_id}")
        cur.execute("UPDATE students SET signature=%s WHERE id=%s", (signature, student_id))
      
      # Don't mark as Released yet - just update the signatory status
      # The fulfillment_status will be updated when registrar actually processes the document
      # If all signatories approved, update overall request status
      print(f"🔍 Updating request status for request_id: {request_id}")
      _update_request_status_after_sign(cur, request_id)
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      
      print(f"✅ Registrar Release Success: student_id={student_id}, signatory_id={signatory_id}")
      return jsonify({"ok": True})
      
    except Exception as err:
      print(f"❌ Registrar Release Error: {err}")
      print(f"❌ Error type: {type(err).__name__}")
      import traceback
      print(f"❌ Traceback: {traceback.format_exc()}")
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/reject', methods=['POST'])
  def api_registrar_reject():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    reason = (data.get('reason') or '').strip()
    if not request_id or not reason:
      return jsonify({"ok": False, "message": "Missing request_id or reason"}), 400
    try:
      cur, conn = mysql.cursor()
      # Find registrar signatory for request
      cur.execute("SELECT id FROM clearance_signatories WHERE request_id=%s AND office='Registrar' ORDER BY id DESC LIMIT 1", (request_id,))
      row = cur.fetchone()
      if not row:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Registrar signatory not found"}), 404
      signatory_id = row['id']
      cur.execute("UPDATE clearance_signatories SET status='Rejected', rejection_reason=%s, updated_at=NOW() WHERE id=%s", (reason, signatory_id))
      cur.execute("UPDATE clearance_requests SET status='Rejected', fulfillment_status='Rejected', registrar_status='Pending' WHERE id=%s", (request_id,))
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/move-to-pending', methods=['POST'])
  def api_registrar_move_to_pending():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    student_id = data.get('student_id')
    
    if not request_id:
      return jsonify({"ok": False, "message": "Missing request_id"}), 400
    
    try:
      cur, conn = mysql.cursor()
      
      # Check if the request exists and is currently approved
      cur.execute("SELECT status FROM clearance_requests WHERE id=%s", (request_id,))
      request_row = cur.fetchone()
      if not request_row:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Request not found"}), 404
      
      if request_row['status'] != 'Approved':
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Request is not in approved status"}), 400
      
      # Find registrar signatory for this request
      cur.execute("SELECT id FROM clearance_signatories WHERE request_id=%s AND office='Registrar' ORDER BY id DESC LIMIT 1", (request_id,))
      signatory_row = cur.fetchone()
      if not signatory_row:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Registrar signatory not found"}), 404
      
      signatory_id = signatory_row['id']
      
      # Update registrar signatory status back to pending
      cur.execute("UPDATE clearance_signatories SET status='Pending', signed_by=NULL, rejection_reason=NULL, updated_at=NOW() WHERE id=%s", (signatory_id,))
      
      # Update the main request status back to pending
      cur.execute("UPDATE clearance_requests SET status='Pending', fulfillment_status='Pending', registrar_status='Pending' WHERE id=%s", (request_id,))
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True, "message": "Clearance moved to pending successfully"})
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/document-requests/move-to-pending', methods=['POST'])
  def api_registrar_document_requests_move_to_pending():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    student_id = data.get('student_id')
    
    if not request_id:
      return jsonify({"ok": False, "message": "Missing request_id"}), 400
    
    try:
      cur, conn = mysql.cursor()
      
      # Check if the document request exists and is currently completed/released
      cur.execute("SELECT status FROM document_requests WHERE id=%s", (request_id,))
      request_row = cur.fetchone()
      if not request_row:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Document request not found"}), 404
      
      if request_row['status'] not in ['completed', 'released']:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Document request is not in completed/released status"}), 400
      
      # Update the document request status back to pending
      cur.execute("UPDATE document_requests SET status='pending', updated_at=NOW() WHERE id=%s", (request_id,))
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True, "message": "Document request moved to pending successfully"})
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/clearance-to-document-request', methods=['POST'])
  def api_registrar_clearance_to_document_request():
    data = request.get_json(silent=True) or {}
    clearance_request_id = data.get('clearance_request_id')
    student_id = data.get('student_id')
    
    if not clearance_request_id:
      return jsonify({"ok": False, "message": "Missing clearance_request_id"}), 400
    
    try:
      cur, conn = mysql.cursor()
      
      # Get the clearance request details
      cur.execute("""
        SELECT cr.*, s.first_name, s.last_name, s.student_no 
        FROM clearance_requests cr 
        JOIN students s ON cr.student_id = s.id 
        WHERE cr.id = %s
      """, (clearance_request_id,))
      clearance_row = cur.fetchone()
      
      if not clearance_row:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Clearance request not found"}), 404
      
      # Prevent duplicate conversions: if a recent pending/processing doc request exists for this clearance, reuse it
      cur.execute(
        """
        SELECT id FROM document_requests
        WHERE student_id=%s AND clearance_request_id=%s
          AND (status='Pending' OR status='Processing')
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (clearance_row['student_id'], clearance_request_id)
      )
      existing = cur.fetchone()
      if existing:
        # Mark clearance as converted so it disappears from Approved
        cur.execute("""
          UPDATE clearance_requests 
          SET status = 'Converted to Document Request', updated_at = NOW() 
          WHERE id = %s
        """, (clearance_request_id,))
        # No need to commit with autocommit=True
        cur.close()
        conn.close()
        return jsonify({
          "ok": True,
          "message": "Already in Pending Documents",
          "document_request_id": existing.get('id') if isinstance(existing, dict) else existing[0]
        })
      
      # Create a new document request based on the clearance request
      # Use the actual documents from the clearance request
      documents = clearance_row.get('documents', 'Clearance Documents')
      if isinstance(documents, list):
        documents = ', '.join(documents)
      elif documents and documents.startswith('[') and documents.endswith(']'):
        # Handle JSON string format
        try:
          import json
          doc_list = json.loads(documents)
          if isinstance(doc_list, list):
            documents = ', '.join(doc_list)
        except:
          pass  # Keep original value if parsing fails
      
      purpose = clearance_row.get('purposes', 'Clearance Processing')
      if isinstance(purpose, list):
        purpose = ', '.join(purpose)
      elif purpose and purpose.startswith('[') and purpose.endswith(']'):
        # Handle JSON string format
        try:
          import json
          purpose_list = json.loads(purpose)
          if isinstance(purpose_list, list):
            purpose = ', '.join(purpose_list)
        except:
          pass  # Keep original value if parsing fails
      
      cur.execute("""
        INSERT INTO document_requests 
        (student_id, document_type, purpose, status, created_at, updated_at, clearance_request_id) 
        VALUES (%s, %s, %s, 'Pending', NOW(), NOW(), %s)
      """, (
        clearance_row['student_id'],
        documents,
        purpose,
        clearance_request_id
      ))
      
      document_request_id = cur.lastrowid
      
      # Update the clearance request status to indicate it's been converted
      cur.execute("""
        UPDATE clearance_requests 
        SET status = 'Converted to Document Request', updated_at = NOW() 
        WHERE id = %s
      """, (clearance_request_id,))
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      
      return jsonify({
        "ok": True, 
        "message": "Clearance converted to document request successfully",
        "document_request_id": document_request_id
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/check-pending-doc-request', methods=['GET'])
  def api_registrar_check_pending_doc_request():
    """Check if the student already has a pending/processing document request.

    Query param: student_id (required)
    Query param: clearance_request_id (optional) - if provided, check for this specific clearance
    """
    try:
      student_id = request.args.get('student_id', type=int)
      clearance_request_id = request.args.get('clearance_request_id', type=int)
      
      if not student_id:
        return jsonify({"ok": False, "message": "Missing student_id"}), 400

      cur, conn = mysql.cursor()
      
      if clearance_request_id:
        # Check for specific clearance request - only check document_requests (not clearance_requests)
        cur.execute(
          """
          SELECT id FROM document_requests
          WHERE student_id=%s AND clearance_request_id=%s AND (status='Pending' OR status='Processing')
          ORDER BY id DESC
          LIMIT 1
          """,
          (student_id, clearance_request_id)
        )
      else:
        # Check for any pending document request - only check document_requests (not clearance_requests)
        cur.execute(
          """
          SELECT id FROM document_requests
          WHERE student_id=%s AND (status='Pending' OR status='Processing')
          ORDER BY id DESC
          LIMIT 1
          """,
          (student_id,)
        )
      
      row = cur.fetchone()
      cur.close()
      conn.close()
      return jsonify({
        "ok": True,
        "in_pending": bool(row),
        "document_request_id": (row or {}).get('id') if isinstance(row, dict) else (row[0] if row else None)
      })
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/check-all-clearances-approved', methods=['GET'])
  def api_registrar_check_all_clearances_approved():
    """Check if ALL clearances are approved for a specific request.
    
    Query params: request_id (required)
    """
    try:
      request_id = request.args.get('request_id', type=int)
      if not request_id:
        return jsonify({"ok": False, "message": "Missing request_id"}), 400

      cur, conn = mysql.cursor()
      
      # Get all signatories for this request
      cur.execute("""
        SELECT office, status, signed_by, signed_at, rejection_reason
        FROM clearance_signatories 
        WHERE request_id = %s
        ORDER BY office
      """, (request_id,))
      
      signatories = cur.fetchall()
      cur.close()
      conn.close()
      
      if not signatories:
        return jsonify({
          "ok": False,
          "message": "No clearance signatories found"
        })
      
      # Check status
      total_offices = len(signatories)
      approved_count = sum(1 for s in signatories if s['status'] == 'Approved')
      rejected_count = sum(1 for s in signatories if s['status'] == 'Rejected')
      pending_count = sum(1 for s in signatories if s['status'] == 'Pending')
      
      all_approved = (approved_count == total_offices and rejected_count == 0)
      
      # Get pending offices for detailed message
      pending_offices = [s['office'] for s in signatories if s['status'] == 'Pending']
      rejected_offices = [s['office'] for s in signatories if s['status'] == 'Rejected']
      
      return jsonify({
        "ok": True,
        "all_approved": all_approved,
        "total_offices": total_offices,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "pending_offices": pending_offices,
        "rejected_offices": rejected_offices,
        "signatories": signatories,
        "message": "All clearances approved" if all_approved else 
                  f"Waiting for {len(pending_offices)} office(s): {', '.join(pending_offices)}" if pending_offices else
                  f"Rejected by: {', '.join(rejected_offices)}"
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/signatories/approve', methods=['POST'])
  def api_signatories_approve():
    try:
      data = request.get_json(silent=True) or {}
      signatory_id = data.get('signatory_id')
      signature = data.get('signature')
      
      print(f"🔍 Approval Debug: Received data: {data}")
      print(f"🔍 Approval Debug: signatory_id: {signatory_id}")
      print(f"🔍 Approval Debug: signature present: {bool(signature)}")
      
      if not signatory_id:
        print("🔍 Approval Debug: Missing signatory_id")
        return jsonify({"ok": False, "message": "Missing signatory_id"}), 400
      
      # Get the actual staff name from database
      staff_email = session.get('dean_email') or session.get('staff_email')
      approver = session.get('admin_name') or 'Staff'  # Default fallback
      
      print(f"🔍 Approval Debug: staff_email: {staff_email}")
      print(f"🔍 Approval Debug: approver: {approver}")
      
      if staff_email and not session.get('admin_name'):
        try:
          print("🔍 Approval Debug: Looking up staff name...")
          cur_temp = mysql.cursor()
          cur_temp.execute("SELECT CONCAT(first_name, ' ', last_name) as full_name FROM staff WHERE email = %s", (staff_email,))
          staff_info = cur_temp.fetchone()
          cur_temp.close()
          if staff_info and staff_info.get('full_name'):
            approver = staff_info['full_name'].strip()
            print(f"🔍 Approval Debug: Found staff name: {approver}")
        except Exception as e:
          print(f"🔍 Approval Debug: Error looking up staff name: {e}")
          pass  # Keep default approver if database lookup fails
      
      try:
        cur, conn = mysql.cursor()
        cur.execute("SELECT request_id FROM clearance_signatories WHERE id = %s", (signatory_id,))
        row = cur.fetchone()
        if not row:
          cur.close()
          conn.close()
          return jsonify({"ok": False, "message": "Signatory not found"}), 404
        request_id = row['request_id']
        # Update signatory status
        cur.execute("UPDATE clearance_signatories SET status='Approved', signed_by=%s, signed_at=NOW(), rejection_reason=NULL WHERE id=%s", (approver, signatory_id))
        
        # Store signature image on the student record if provided
        cur.execute("SELECT student_id, status FROM clearance_requests WHERE id=%s", (request_id,))
        r = cur.fetchone() or {}
        student_id = r.get('student_id')
        if signature and student_id:
          cur.execute("UPDATE students SET signature=%s WHERE id=%s", (signature, student_id))
        
        # Check if all signatories are now approved
        cur.execute("SELECT COUNT(*) AS c FROM clearance_signatories WHERE request_id = %s AND status != 'Approved'", (request_id,))
        non_approved_count = (cur.fetchone() or {}).get('c', 0)
        
        if non_approved_count == 0:
          # All signatories approved - update request status
          cur.execute("UPDATE clearance_requests SET status = 'Approved', fulfillment_status = 'Pending', registrar_status = 'Pending' WHERE id = %s", (request_id,))
          # Update student status
          if student_id:
            cur.execute("UPDATE students SET status = 'Approved' WHERE id = %s", (student_id,))
          # Note: Auto-transfer disabled - Registrar will manually move to pending documents
        
        
        # No need to commit with autocommit=True
        cur.close()
        conn.close()
        return jsonify({"ok": True})
      except Exception as err:
        return jsonify({"ok": False, "message": f"Error: {err}"}), 500
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/signatories/reject', methods=['POST'])
  def api_signatories_reject():
    data = request.get_json(silent=True) or {}
    signatory_id = data.get('signatory_id')
    reason = (data.get('reason') or '').strip()
    if not signatory_id or not reason:
      return jsonify({"ok": False, "message": "Missing signatory_id or reason"}), 400
    
    # Get the actual staff name from database
    staff_email = session.get('dean_email') or session.get('staff_email')
    approver = session.get('admin_name') or 'Staff'  # Default fallback
    
    if staff_email and not session.get('admin_name'):
      try:
        cur_temp = mysql.cursor()
        cur_temp.execute("SELECT CONCAT(first_name, ' ', last_name) as full_name FROM staff WHERE email = %s", (staff_email,))
        staff_info = cur_temp.fetchone()
        cur_temp.close()
        if staff_info and staff_info.get('full_name'):
          approver = staff_info['full_name'].strip()
      except Exception:
        pass  # Keep default approver if database lookup fails
    try:
      cur, conn = mysql.cursor()
      cur.execute("SELECT request_id FROM clearance_signatories WHERE id = %s", (signatory_id,))
      row = cur.fetchone()
      if not row:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Signatory not found"}), 404
      request_id = row['request_id']
      cur.execute("UPDATE clearance_signatories SET status='Rejected', signed_by=%s, signed_at=NOW(), rejection_reason=%s WHERE id=%s", (approver, reason, signatory_id))
      cur.execute("UPDATE clearance_requests SET status='Rejected', fulfillment_status='Rejected', registrar_status='Pending' WHERE id=%s", (request_id,))
      # Sync student status
      cur.execute("SELECT student_id FROM clearance_requests WHERE id=%s", (request_id,))
      r = cur.fetchone() or {}
      if r.get('student_id'):
        cur.execute("UPDATE students SET status='Rejected', rejection_reason=%s, approved_by=%s WHERE id=%s", (reason, approver, r.get('student_id')))
        
        # Create notification for student
        create_notification(
          r.get('student_id'),
          approver,
          'rejected',
          'Rejected',
          f"{approver} rejected your clearance due to: {reason}"
        )
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Users list for login suggestions
  @app.route('/api/users')
  def api_users():
    try:
      cur, conn = mysql.cursor()
      cur.execute("SELECT email AS email, CONCAT(first_name,' ',last_name) AS full_name FROM students ORDER BY created_at DESC LIMIT 100")
      stu = list(cur.fetchall()) or []
      cur.execute("SELECT email AS email, CONCAT(first_name,' ',last_name) AS full_name FROM staff ORDER BY created_at DESC LIMIT 100")
      stf = list(cur.fetchall()) or []
      cur.close()
      conn.close()
      return jsonify({"ok": True, "users": stu + stf})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # ============================================================
  # Document Requests API Endpoints (separate from clearance requests)
  # ============================================================
  
  @app.route('/api/registrar/document-requests')
  def api_registrar_document_requests():
    status = request.args.get('status', 'pending')
    try:
      cur, conn = mysql.cursor()
      
      if status == 'pending':
        # Get pending documents from both clearance_requests and document_requests tables
        try:
          cur.execute(
            """
            SELECT dr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name, 
                   s.course_code, s.course_name, s.year_level, s.year_level_name,
                   dr.document_type, dr.purpose as documents, dr.purpose as purposes, dr.status, 
                   'Pending' as fulfillment_status,
                   dr.created_at, dr.updated_at, dr.pickup_date,
                   'document' as request_type, dr.clearance_request_id, 'Approved' as clearance_status
            FROM document_requests dr
            JOIN students s ON s.id = dr.student_id
            WHERE dr.status = 'Pending'
            
            UNION ALL
            
            SELECT cr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name, 
                   s.course_code, s.course_name, s.year_level, s.year_level_name,
                   cr.document_type, cr.documents, cr.purposes, cr.status, 
                   COALESCE(cr.fulfillment_status, 'Pending') as fulfillment_status,
                   cr.created_at, cr.updated_at, cr.pickup_date,
                   'clearance' as request_type, NULL as clearance_request_id, NULL as clearance_status
            FROM clearance_requests cr
            JOIN students s ON s.id = cr.student_id
            WHERE (cr.status = 'Approved' OR cr.status IS NULL OR cr.status = '') 
              AND (cr.fulfillment_status = 'Pending' OR cr.fulfillment_status IS NULL)
            
            ORDER BY created_at DESC
            """
          )
        except Exception as e:
          # If fulfillment_status column doesn't exist, fallback to status only
          print(f"fulfillment_status column not found, using status only: {e}")
          cur.execute(
            """
            SELECT dr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name, 
                   s.course_code, s.course_name, s.year_level, s.year_level_name,
                   dr.document_type, dr.purpose as documents, dr.purpose as purposes, dr.status, 
                   'Pending' as fulfillment_status,
                   dr.created_at, dr.updated_at, dr.pickup_date,
                   'document' as request_type, dr.clearance_request_id, 'Approved' as clearance_status
            FROM document_requests dr
            JOIN students s ON s.id = dr.student_id
            WHERE dr.status = 'Pending'
            
            UNION ALL
            
            SELECT cr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name, 
                   s.course_code, s.course_name, s.year_level, s.year_level_name,
                   cr.document_type, cr.documents, cr.purposes, cr.status, 
                   'Pending' as fulfillment_status,
                   cr.created_at, cr.updated_at, cr.pickup_date,
                   'clearance' as request_type, NULL as clearance_request_id, NULL as clearance_status
            FROM clearance_requests cr
            JOIN students s ON s.id = cr.student_id
            WHERE (cr.status = 'Approved' OR cr.status IS NULL OR cr.status = '')
            
            ORDER BY created_at DESC
            """
          )
      elif status == 'processing':
        cur.execute(
          """
          SELECT cr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name, 
                 s.course_code, s.course_name, s.year_level, s.year_level_name,
                 cr.document_type, cr.documents, cr.purposes, cr.status, cr.fulfillment_status,
                 cr.created_at, cr.updated_at, cr.pickup_date
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE (cr.status = 'Approved' OR cr.status IS NULL OR cr.status = '') AND (cr.fulfillment_status = 'Processing' OR cr.fulfillment_status = 'Approved')
          ORDER BY cr.updated_at DESC
          """
        )
      elif status == 'completed':
        cur.execute(
          """
          SELECT cr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name, 
                 s.course_code, s.course_name, s.year_level, s.year_level_name,
                 cr.document_type, cr.documents, cr.purposes, cr.status, cr.fulfillment_status,
                 cr.created_at, cr.updated_at, cr.pickup_date
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE (cr.status = 'Approved' OR cr.status IS NULL OR cr.status = '') AND cr.fulfillment_status = 'Completed'
          ORDER BY cr.updated_at DESC
          """
        )
      elif status == 'released':
        cur.execute(
          """
          SELECT cr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name,
                 s.course_code, s.course_name, s.year_level, s.year_level_name,
                 cr.document_type, cr.documents, cr.purposes, cr.status, cr.fulfillment_status,
                 cr.created_at, cr.updated_at, cr.pickup_date
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE (cr.status = 'Approved' OR cr.status IS NULL OR cr.status = '') AND cr.fulfillment_status = 'Released'
          ORDER BY cr.updated_at DESC
          """
        )
      elif status == 'rejected':
        cur.execute(
          """
          SELECT cr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name, 
                 s.course_code, s.course_name, s.year_level, s.year_level_name,
                 cr.document_type, cr.documents, cr.purposes, cr.status, cr.fulfillment_status,
                 cr.reason AS rejection_reason, cr.created_at, cr.updated_at, cr.pickup_date
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE cr.status = 'Rejected'
          ORDER BY cr.updated_at DESC
          """
        )
      elif status == 'unclaimed':
        cur.execute(
          """
          SELECT cr.id AS request_id, s.id AS student_id, s.student_no, s.first_name, s.last_name,
                 s.course_code, s.course_name, s.year_level, s.year_level_name,
                 cr.document_type, cr.documents, cr.purposes, cr.status, cr.fulfillment_status,
                 cr.created_at, cr.updated_at, cr.pickup_date
          FROM clearance_requests cr
          JOIN students s ON s.id = cr.student_id
          WHERE (cr.status = 'Approved' OR cr.status IS NULL OR cr.status = '') AND cr.fulfillment_status = 'Released'
          AND cr.updated_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
          ORDER BY cr.updated_at DESC
          """
        )
      else:
        return jsonify({"ok": False, "message": "Invalid status parameter"}), 400
      
      rows = cur.fetchall() or []
      cur.close()
      conn.close()
      
      data = []
      for row in rows:
        # Parse documents JSON from clearance_requests
        documents = []
        if row.get('documents'):
          try:
            documents = json.loads(row['documents']) if row['documents'] else []
          except:
            documents = []
        
        # Parse purposes JSON from clearance_requests
        purposes = []
        if row.get('purposes'):
          try:
            purposes = json.loads(row['purposes']) if row['purposes'] else []
          except:
            purposes = []
        
        # For completed documents, use the pickup_date if available, otherwise completed_at
        display_timestamp = row.get('pickup_date') or row.get('completed_at') or row.get('updated_at') or row.get('created_at')
        
        data.append({
          "request_id": row['request_id'],
          "student_id": row['student_id'],
          "student_name": f"{row['first_name']} {row['last_name']}",
          "first_name": row['first_name'],
          "last_name": row['last_name'],
          "course_code": row['course_code'],
          "course_name": row['course_name'],
          "year_level": row['year_level'],
          "year_level_name": row['year_level_name'],
          "document_type": row['document_type'],
          "document": ", ".join(documents) if documents else row['document_type'],
          "documents": documents,
          "purposes": purposes,
          "purpose": ", ".join(purposes) if purposes else (row.get('purpose') or 'Document Processing'),
          "status": row['status'],
          "fulfillment_status": row.get('fulfillment_status'),
          "created_at": row['created_at'],
          "updated_at": row['updated_at'],
          "completed_at": row.get('completed_at'),
          "pickup_date": row.get('pickup_date'),
          "released_at": display_timestamp,  # Use pickup_date or updated_at for display
          "rejection_reason": row.get('rejection_reason'),
          "request_type": row.get('request_type', 'clearance')
        })
      
      return jsonify({"ok": True, "data": data})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/document-requests/mark-processing', methods=['POST'])
  def api_registrar_document_mark_processing():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    try:
      if not request_id:
        return jsonify({"ok": False, "message": "Missing request_id"}), 400
      
      cur, conn = mysql.cursor()
      
      # Check if this document request is linked to a clearance request
      cur.execute("""
        SELECT clearance_request_id FROM document_requests 
        WHERE id = %s AND clearance_request_id IS NOT NULL
      """, (request_id,))
      
      clearance_result = cur.fetchone()
      
      if clearance_result:
        # This is a document request from a clearance - check if all offices are approved
        clearance_request_id = clearance_result['clearance_request_id']
        
        # Check if all clearance signatories are approved
        cur.execute("""
          SELECT COUNT(*) AS total_signatories,
                 SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) AS approved_count,
                 SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) AS rejected_count,
                 SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending_count
          FROM clearance_signatories 
          WHERE request_id = %s
        """, (clearance_request_id,))
        
        clearance_stats = cur.fetchone()
        
        if clearance_stats['rejected_count'] > 0:
          return jsonify({
            "ok": False, 
            "message": "Cannot process — some clearances have been rejected.",
            "clearance_status": "rejected"
          }), 400
        
        if clearance_stats['pending_count'] > 0:
          return jsonify({
            "ok": False, 
            "message": "Cannot process yet — some clearances are still pending.",
            "clearance_status": "pending"
          }), 400
        
        if clearance_stats['approved_count'] != clearance_stats['total_signatories']:
          return jsonify({
            "ok": False, 
            "message": "Cannot process — not all clearances are approved.",
            "clearance_status": "incomplete"
          }), 400
        
        # All clearances are approved - proceed with processing
        cur.execute("UPDATE document_requests SET status='Processing', updated_at=NOW() WHERE id=%s", (request_id,))
        
        # Get student_id for notification
        cur.execute("SELECT student_id FROM document_requests WHERE id=%s", (request_id,))
        doc_result = cur.fetchone()
        
        # No need to commit with autocommit=True
        cur.close()
        conn.close()
        
        # Create notification after main transaction is committed
        if doc_result and doc_result.get('student_id'):
          create_notification(
            doc_result.get('student_id'),
            'Registrar',
            'processing',
            'Processing',
            'Your request is now in the Processing Phase.'
          )
        
        return jsonify({
          "ok": True, 
          "message": "All clearances approved — document is now in processing.",
          "clearance_status": "approved"
        })
      else:
        # This is a regular document request (not from clearance) - allow processing
        cur.execute("UPDATE document_requests SET status='Processing', updated_at=NOW() WHERE id=%s", (request_id,))
        
        # Get student_id for notification
        cur.execute("SELECT student_id FROM document_requests WHERE id=%s", (request_id,))
        doc_result = cur.fetchone()
        
        # No need to commit with autocommit=True
        cur.close()
        conn.close()
        
        # Create notification after main transaction is committed
        if doc_result and doc_result.get('student_id'):
          create_notification(
            doc_result.get('student_id'),
            'Registrar',
            'processing',
            'Processing',
            'Your request is now in the Processing Phase.'
          )
        
        return jsonify({"ok": True, "message": "Document moved to processing."})
        
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/document-requests/complete', methods=['POST'])
  def api_registrar_document_complete():
    """Complete a document request and save uploaded files.
    Expects multipart/form-data with fields:
    - request_id: int
    - files[]: one or more files
    For backward compatibility, also accepts JSON body with only request_id.
    """
    request_id = None
    files = []
    # Support multipart and JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
      request_id = request.form.get('request_id')
      files = request.files.getlist('files[]') or request.files.getlist('files')
    else:
      data = request.get_json(silent=True) or {}
      request_id = data.get('request_id')
    try:
      if not request_id:
        return jsonify({"ok": False, "message": "Missing request_id"}), 400
      cur, conn = mysql.cursor()

      # If files provided, persist to disk and record metadata
      saved_files = []
      if files:
        print(f"[UPLOAD DEBUG] Processing {len(files)} files for request {request_id}")
        # Ensure upload dir per request exists
        base_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(request_id))
        os.makedirs(base_dir, exist_ok=True)
        print(f"[UPLOAD DEBUG] Upload directory: {base_dir}")
        for f in files:
          if not f or not getattr(f, 'filename', ''):
            print(f"[UPLOAD DEBUG] Skipping invalid file: {f}")
            continue
          filename = f.filename
          # create unique filename to avoid collisions
          ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
          safe_name = f"{ts}_{filename}"
          file_path = os.path.join(base_dir, safe_name)
          print(f"[UPLOAD DEBUG] Saving file: {filename} -> {file_path}")
          f.save(file_path)
          rel_path = os.path.relpath(file_path, app.root_path)
          size = None
          try:
            size = os.path.getsize(file_path)
            print(f"[UPLOAD DEBUG] File saved successfully, size: {size} bytes")
          except Exception as e:
            print(f"[UPLOAD DEBUG] Error getting file size: {e}")
            size = None
          cur.execute(
            """
            INSERT INTO document_files (document_request_id, original_name, file_path, mime_type, file_size)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (request_id, filename, rel_path.replace('\\', '/'), f.mimetype, size)
          )
          saved_files.append({"name": filename})
          print(f"[UPLOAD DEBUG] File metadata saved to database")

      # Update document_requests status to Completed (not Released) so registrar can choose next state
      cur.execute("UPDATE document_requests SET status='Completed', completed_at=NOW(), updated_at=NOW() WHERE id=%s", (request_id,))
      
      # Also update the corresponding clearance_requests fulfillment_status to Completed
      # This ensures the consolidation logic in /api/student/requests works correctly
      cur.execute("""
        UPDATE clearance_requests cr 
        JOIN document_requests dr ON dr.clearance_request_id = cr.id 
        SET cr.fulfillment_status = 'Completed', cr.registrar_status = 'Complete', cr.updated_at = NOW() 
        WHERE dr.id = %s
      """, (request_id,))
      
      # Create notification for student
      cur.execute("SELECT student_id FROM document_requests WHERE id=%s", (request_id,))
      doc_result = cur.fetchone()
      if doc_result and doc_result.get('student_id'):
        create_notification(
          doc_result.get('student_id'),
          'Registrar',
          'completed',
          'Completed',
          'Your document moved to Completed Phase.'
        )
      
      # Note: We don't update clearance_requests to 'Released' here
      # because the document is only 'Completed' - not yet released to student
      # The 'Released' status will be set when the registrar clicks "Released Documents"
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True, "files": saved_files})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/document-requests/mark-released', methods=['POST'])
  def api_registrar_document_mark_released():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    if not request_id:
      return jsonify({"ok": False, "message": "Missing request_id"}), 400
    try:
      cur, conn = mysql.cursor()
      cur.execute("UPDATE document_requests SET status='Released', updated_at=NOW() WHERE id=%s", (request_id,))
      
      # Also update the corresponding clearance_requests fulfillment_status to Released
      # This ensures the consolidation logic in /api/student/requests works correctly
      cur.execute("""
        UPDATE clearance_requests cr 
        JOIN document_requests dr ON dr.clearance_request_id = cr.id 
        SET cr.fulfillment_status = 'Released', cr.registrar_status = 'Complete', cr.updated_at = NOW() 
        WHERE dr.id = %s
      """, (request_id,))
      
      # Create notification for student
      cur.execute("SELECT student_id FROM document_requests WHERE id=%s", (request_id,))
      doc_result = cur.fetchone()
      if doc_result and doc_result.get('student_id'):
        create_notification(
          doc_result.get('student_id'),
          'Registrar',
          'released',
          'Released',
          'Your document has been released.'
        )
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/document-requests/mark-unclaimed', methods=['POST'])
  def api_registrar_document_mark_unclaimed():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    if not request_id:
      return jsonify({"ok": False, "message": "Missing request_id"}), 400
    try:
      cur, conn = mysql.cursor()
      cur.execute("UPDATE document_requests SET status='Unclaimed', updated_at=NOW() WHERE id=%s", (request_id,))
      
      # Also update the corresponding clearance_requests fulfillment_status to Unclaimed
      # This ensures the consolidation logic in /api/student/requests works correctly
      cur.execute("""
        UPDATE clearance_requests cr 
        JOIN document_requests dr ON dr.clearance_request_id = cr.id 
        SET cr.fulfillment_status = 'Unclaimed', cr.registrar_status = 'Complete', cr.updated_at = NOW() 
        WHERE dr.id = %s
      """, (request_id,))
      
      # Create notification for student
      cur.execute("SELECT student_id FROM document_requests WHERE id=%s", (request_id,))
      doc_result = cur.fetchone()
      if doc_result and doc_result.get('student_id'):
        create_notification(
          doc_result.get('student_id'),
          'Registrar',
          'unclaimed',
          'Unclaimed',
          'Your document is unclaimed.'
        )
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/test-ai-connectivity', methods=['GET'])
  def api_test_ai_connectivity():
    """Test AI service connectivity"""
    try:
      is_reachable, message = _test_ai_connectivity()
      return jsonify({
        "ok": is_reachable,
        "message": message,
        "timestamp": datetime.now().isoformat()
      })
    except Exception as e:
      return jsonify({
        "ok": False,
        "message": f"Connectivity test failed: {str(e)}",
        "timestamp": datetime.now().isoformat()
      })

  @app.route('/api/check-reference-duplicate', methods=['POST'])
  def api_check_reference_duplicate():
    """Check if a reference number has already been used."""
    try:
      data = request.get_json(silent=True) or {}
      reference_number = data.get('reference_number')
      
      if not reference_number:
        return jsonify({"ok": False, "message": "Reference number is required"})
      
      cur, conn = mysql.cursor()
      cur.execute("SELECT id FROM clearance_requests WHERE reference_number = %s", (reference_number,))
      existing_request = cur.fetchone()
      
      if existing_request:
        return jsonify({
          "ok": False, 
          "is_duplicate": True,
          "message": f"Reference number '{reference_number}' has already been used"
        })
      else:
        return jsonify({
          "ok": True, 
          "is_duplicate": False,
          "message": "Reference number is available"
        })
        
    except Exception as e:
      return jsonify({"ok": False, "message": f"Error checking reference number: {str(e)}"})

  @app.route('/api/validate-receipt-reference', methods=['POST'])
  def api_validate_receipt_reference():
    """Validate if the reference number matches the receipt using Gemini AI."""
    try:
      data = request.get_json(silent=True) or {}
      receipt_image = data.get('receipt_image')
      reference_number = data.get('reference_number')
      
      if not receipt_image or not reference_number:
        return jsonify({"ok": False, "message": "Missing receipt image or reference number"})
      
      # Use Gemini AI to extract reference number from receipt
      result = _gemini_extract(receipt_image)
      
      if not result.get('ok'):
        return jsonify({"ok": False, "message": f"AI processing failed: {result.get('message', 'Unknown error')}"})
      
      # Compare extracted reference number with provided one
      extracted_ref = result.get('reference_number', '').strip()
      provided_ref = reference_number.strip()
      
      # Check if they match (case insensitive, remove any non-digit characters for comparison)
      import re
      extracted_digits = re.sub(r'\D', '', extracted_ref)
      provided_digits = re.sub(r'\D', '', provided_ref)
      
      # Normalize both numbers (remove leading zeros, spaces, and standardize)
      extracted_clean = extracted_digits.lstrip('0') or '0'  # Keep at least one digit
      provided_clean = provided_digits.lstrip('0') or '0'     # Keep at least one digit
      
      confidence = result.get('confidence', 0.0)
      
      # Enhanced debug logging
      print(f"DEBUG: Raw extracted: '{extracted_ref}' -> digits: '{extracted_digits}' -> clean: '{extracted_clean}'")
      print(f"DEBUG: Raw provided: '{provided_ref}' -> digits: '{provided_digits}' -> clean: '{provided_clean}'")
      print(f"DEBUG: AI confidence: {confidence}")
      print(f"DEBUG: Raw text from AI: {result.get('raw_text', '')[:200]}...")
      print(f"DEBUG: Full AI response: {result}")
      
      # Calculate length difference for flexible matching
      length_diff = abs(len(extracted_clean) - len(provided_clean))
      print(f"DEBUG: Length difference: {length_diff}")
      
      # SECURITY: Pre-validation checks before determining match
      if not extracted_clean or extracted_clean == '0':
        print(f"DEBUG: NO VALID REFERENCE NUMBER EXTRACTED FROM RECEIPT")
        matches = False
      elif len(extracted_clean) < 5:  # Minimum 5 digits for security
        print(f"DEBUG: SECURITY CHECK - Extracted reference too short ({len(extracted_clean)} digits) - REJECTING")
        matches = False
      elif len(extracted_clean) > 16:  # Maximum 16 digits
        print(f"DEBUG: SECURITY CHECK - Extracted reference too long ({len(extracted_clean)} digits) - REJECTING")
        matches = False
      elif length_diff > 2:  # Allow small length differences (leading zeros, formatting)
        print(f"DEBUG: LENGTH MISMATCH - extracted: {len(extracted_clean)}, provided: {len(provided_clean)}, diff: {length_diff} - REJECTING")
        matches = False
      else:
        # All security checks passed, now check if numbers actually match
        matches = extracted_clean == provided_clean
        if matches:
          print(f"DEBUG: SECURITY CHECK - EXACT MATCH CONFIRMED - '{extracted_clean}' == '{provided_clean}'")
          print(f"DEBUG: CONFIDENCE: {confidence:.2f} - PROCEEDING WITH MATCH (exact match overrides confidence)")
        else:
          print(f"DEBUG: SECURITY CHECK - EXACT MATCH REQUIRED - extracted: '{extracted_clean}', provided: '{provided_clean}' - REJECTING")
          # Only reject due to low confidence if numbers don't match
          if confidence < 0.3:  # Very low confidence threshold only for non-matches
            print(f"DEBUG: VERY LOW CONFIDENCE ({confidence:.2f}) FOR NON-MATCH - REJECTING")
            matches = False
      
      # Additional validation - check if extracted reference is reasonable
      if not matches and extracted_digits:
        print(f"DEBUG: MISMATCH DETECTED!")
        print(f"DEBUG: Extracted digits: '{extracted_digits}' (length: {len(extracted_digits)})")
        print(f"DEBUG: Provided digits: '{provided_digits}' (length: {len(provided_digits)})")
        print(f"DEBUG: Are they equal? {extracted_digits == provided_digits}")
        
        # Check if it's a partial match or completely different
        if extracted_digits in provided_digits or provided_digits in extracted_digits:
          print(f"DEBUG: PARTIAL MATCH DETECTED - one contains the other")
        else:
          print(f"DEBUG: COMPLETELY DIFFERENT NUMBERS")
      
      print(f"DEBUG: Final match result: {matches}")
      
      # Enhanced error reporting for debugging
      if not extracted_digits:
        print(f"DEBUG: NO REFERENCE NUMBER EXTRACTED - AI FAILED TO READ RECEIPT")
        print(f"DEBUG: Raw AI response: {result}")
        print(f"DEBUG: Confidence: {confidence}")
        print(f"DEBUG: Raw text: {result.get('raw_text', '')[:500]}")
      
      return jsonify({
        "ok": True,
        "matches": matches,
        "extracted_reference": extracted_ref if extracted_ref else "Not found",
        "provided_reference": provided_ref,
        "extracted_digits": extracted_digits,
        "provided_digits": provided_digits,
        "confidence": confidence,
        "amount": result.get('amount'),
        "raw_text": result.get('raw_text', ''),
        "ai_success": bool(extracted_digits),
        "debug_info": {
          "ai_processed": True,
          "extraction_successful": bool(extracted_digits),
          "confidence_level": confidence
        }
      })
      
    except Exception as e:
      return jsonify({"ok": False, "message": f"Validation error: {str(e)}"})

  @app.route('/api/student/document-files/<int:request_id>')
  def api_student_document_files(request_id: int):
    """List downloadable files for a completed document request."""
    try:
      cur, conn = mysql.cursor()
      cur.execute("SELECT id, original_name, file_path FROM document_files WHERE document_request_id=%s ORDER BY uploaded_at ASC", (request_id,))
      rows = cur.fetchall() or []
      cur.close()
      conn.close()
      return jsonify({"ok": True, "files": [{"id": r['id'], "name": r['original_name'], "url": f"/download/document-file/{r['id']}"} for r in rows]})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/student/clearance-files/<int:request_id>')
  def api_student_clearance_files(request_id: int):
    """List downloadable files for a completed clearance request."""
    try:
      cur, conn = mysql.cursor()
      cur.execute("SELECT id, original_name, file_path FROM clearance_files WHERE clearance_request_id=%s ORDER BY uploaded_at ASC", (request_id,))
      rows = cur.fetchall() or []
      cur.close()
      conn.close()
      return jsonify({"ok": True, "files": [{"id": r['id'], "name": r['original_name'], "url": f"/download/clearance-file/{r['id']}"} for r in rows]})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/download/document-file/<int:file_id>')
  def download_document_file(file_id: int):
    """Serve a specific uploaded file to the student for download."""
    try:
      cur, conn = mysql.cursor()
      cur.execute("SELECT original_name, file_path FROM document_files WHERE id=%s", (file_id,))
      row = cur.fetchone()
      cur.close()
      conn.close()
      if not row:
        return jsonify({"ok": False, "message": "File not found"}), 404
      path = row['file_path']
      abs_path = os.path.join(app.root_path, path)
      
      # Check if file exists
      if not os.path.exists(abs_path):
        print(f"[DOWNLOAD ERROR] File not found: {abs_path}")
        return jsonify({"ok": False, "message": "File not found on disk"}), 404
      
      dir_path = os.path.dirname(abs_path)
      file_name = os.path.basename(abs_path)
      return send_from_directory(directory=dir_path, path=file_name, as_attachment=True, download_name=row['original_name'])
    except Exception as err:
      print(f"[DOWNLOAD ERROR] {err}")
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/download/clearance-file/<int:file_id>')
  def download_clearance_file(file_id: int):
    """Serve a specific uploaded clearance file to the student for download."""
    try:
      cur, conn = mysql.cursor()
      cur.execute("SELECT original_name, file_path FROM clearance_files WHERE id=%s", (file_id,))
      row = cur.fetchone()
      cur.close()
      conn.close()
      if not row:
        return jsonify({"ok": False, "message": "File not found"}), 404
      path = row['file_path']
      abs_path = os.path.join(app.root_path, path)
      
      # Check if file exists
      if not os.path.exists(abs_path):
        print(f"[DOWNLOAD ERROR] File not found: {abs_path}")
        return jsonify({"ok": False, "message": "File not found on disk"}), 404
      
      dir_path = os.path.dirname(abs_path)
      file_name = os.path.basename(abs_path)
      return send_from_directory(directory=dir_path, path=file_name, as_attachment=True, download_name=row['original_name'])
    except Exception as err:
      print(f"[DOWNLOAD ERROR] {err}")
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/document-requests/reject', methods=['POST'])
  def api_registrar_document_reject():
    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    reason = data.get('reason')
    if not request_id or not reason:
      return jsonify({"ok": False, "message": "Missing request_id or reason"}), 400
    try:
      cur, conn = mysql.cursor()
      cur.execute("UPDATE document_requests SET status='Rejected', rejection_reason=%s, updated_at=NOW() WHERE id=%s", (reason, request_id))
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True})
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/document/request', methods=['POST'])
  def api_student_submit_document_request():
    try:
      student_email = session.get('student_email')
      if not student_email:
        return jsonify({"ok": False, "message": "No student session found (HTTP 401)"}), 401
      
      cur, conn = mysql.cursor()
      # Get student id
      cur.execute("SELECT id FROM students WHERE email = %s", (student_email,))
      stu = cur.fetchone()
      if not stu:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Student not found"}), 404
      
      student_id = stu['id']
      
      # Read request details from JSON body
      try:
        payload = request.get_json(silent=True) or {}
      except Exception:
        payload = {}
      
      document_type = (payload.get('document_type') or '').strip()
      purpose = (payload.get('purpose') or '').strip()
      
      if not document_type:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Document type is required"}), 400
      
      # Create new document request
      cur.execute(
        "INSERT INTO document_requests (student_id, document_type, purpose, status) VALUES (%s, %s, %s, 'Pending')",
        (student_id, document_type, purpose)
      )
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      return jsonify({"ok": True, "message": "Document request submitted successfully"})
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/set-pickup-date', methods=['POST'])
  def api_set_pickup_date():
    """Set pickup date for a clearance request"""
    try:
      data = request.get_json()
      request_id = data.get('request_id')
      pickup_date = data.get('pickup_date')
      
      if not request_id or not pickup_date:
        return jsonify({"ok": False, "message": "Missing request_id or pickup_date"}), 400
      
      cur, conn = mysql.cursor()
      
      # Update the pickup_date in clearance_requests table
      cur.execute("""
          UPDATE clearance_requests 
          SET pickup_date = %s 
          WHERE id = %s
      """, (pickup_date, request_id))
      
      if cur.rowcount == 0:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Request not found"}), 404
      
      # Also update pickup_date in document_requests table if it exists
      cur.execute("""
          UPDATE document_requests 
          SET pickup_date = %s 
          WHERE clearance_request_id = %s
      """, (pickup_date, request_id))
      
      cur.close()
      conn.close()
      
      return jsonify({
          "ok": True, 
          "message": "Pickup date set successfully",
          "pickup_date": pickup_date
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/upload-document', methods=['POST'])
  def api_upload_document():
    """Upload document for a clearance request and mark as completed"""
    try:
      request_id = request.form.get('request_id')
      files = request.files.getlist('files[]') or request.files.getlist('file')
      
      if not request_id:
        return jsonify({"ok": False, "message": "Missing request_id"}), 400
      
      if not files or not any(f.filename for f in files):
        return jsonify({"ok": False, "message": "No files provided"}), 400
      
      cur, conn = mysql.cursor()
      
      # Save uploaded files
      saved_files = []
      for file in files:
        if not file or not file.filename:
          continue
          
        # Create upload directory
        base_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"clearance_{request_id}")
        os.makedirs(base_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        safe_name = f"{timestamp}_{file.filename}"
        file_path = os.path.join(base_dir, safe_name)
        
        # Save file
        file.save(file_path)
        rel_path = os.path.relpath(file_path, app.root_path).replace('\\', '/')
        file_size = os.path.getsize(file_path)
        
        # Save file metadata to database
        cur.execute("""
            INSERT INTO clearance_files (clearance_request_id, original_name, file_path, mime_type, file_size)
            VALUES (%s, %s, %s, %s, %s)
        """, (request_id, file.filename, rel_path, file.mimetype, file_size))
        
        saved_files.append({"name": file.filename})
      
      # Update clearance_requests fulfillment_status to Completed
      cur.execute("""
          UPDATE clearance_requests 
          SET fulfillment_status = 'Completed', registrar_status = 'Complete', updated_at = NOW() 
          WHERE id = %s
      """, (request_id,))
      
      if cur.rowcount == 0:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Request not found"}), 404
      
      # Create notification for student
      cur.execute("SELECT student_id FROM clearance_requests WHERE id = %s", (request_id,))
      result = cur.fetchone()
      if result and result.get('student_id'):
        create_notification(
          result.get('student_id'),
          'Registrar',
          'completed',
          'Completed',
          'Your document has been processed and is ready for review.'
        )
      
      cur.close()
      conn.close()
      
      return jsonify({
          "ok": True, 
          "message": "Document uploaded successfully",
          "files": saved_files
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/release-document', methods=['POST'])
  def api_release_document():
    """Release a completed document to the student"""
    try:
      data = request.get_json()
      request_id = data.get('request_id')
      
      if not request_id:
        return jsonify({"ok": False, "message": "Missing request_id"}), 400
      
      cur, conn = mysql.cursor()
      
      # Update clearance_requests fulfillment_status to Released
      cur.execute("""
          UPDATE clearance_requests 
          SET fulfillment_status = 'Released', registrar_status = 'Complete', updated_at = NOW() 
          WHERE id = %s AND fulfillment_status = 'Completed'
      """, (request_id,))
      
      if cur.rowcount == 0:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "message": "Request not found or not in Completed status"}), 404
      
      # Create notification for student
      cur.execute("SELECT student_id FROM clearance_requests WHERE id = %s", (request_id,))
      result = cur.fetchone()
      if result and result.get('student_id'):
        create_notification(
          result.get('student_id'),
          'Registrar',
          'released',
          'Released',
          'Your document is ready for pickup!'
        )
      
      cur.close()
      conn.close()
      
      return jsonify({
          "ok": True, 
          "message": "Document released successfully"
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  @app.route('/api/registrar/update-clearance-documents', methods=['POST'])
  def api_update_clearance_documents():
    """Update existing document requests that have 'Clearance Documents' to show actual documents"""
    try:
      cur, conn = mysql.cursor()
      
      # Find all document requests with 'Clearance Documents' that have a clearance_request_id
      cur.execute("""
        SELECT dr.id, dr.clearance_request_id, cr.documents, cr.purposes
        FROM document_requests dr
        LEFT JOIN clearance_requests cr ON cr.id = dr.clearance_request_id
        WHERE dr.document_type = 'Clearance Documents' 
          AND dr.clearance_request_id IS NOT NULL
          AND cr.documents IS NOT NULL
      """)
      
      requests_to_update = cur.fetchall()
      updated_count = 0
      
      for request in requests_to_update:
        documents = request['documents']
        purposes = request['purposes']
        
        # Parse documents if it's a JSON string
        if documents and documents.startswith('[') and documents.endswith(']'):
          try:
            import json
            doc_list = json.loads(documents)
            if isinstance(doc_list, list):
              documents = ', '.join(doc_list)
          except:
            pass  # Keep original value if parsing fails
        
        # Parse purposes if it's a JSON string
        if purposes and purposes.startswith('[') and purposes.endswith(']'):
          try:
            import json
            purpose_list = json.loads(purposes)
            if isinstance(purpose_list, list):
              purposes = ', '.join(purpose_list)
          except:
            pass  # Keep original value if parsing fails
        
        # Update the document request
        cur.execute("""
          UPDATE document_requests 
          SET document_type = %s, purpose = %s, updated_at = NOW()
          WHERE id = %s
        """, (documents, purposes, request['id']))
        
        updated_count += 1
      
      cur.close()
      conn.close()
      
      return jsonify({
        "ok": True, 
        "message": f"Updated {updated_count} document requests with actual documents",
        "updated_count": updated_count
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Add sample payment data to existing requests (for testing)
  @app.route('/api/admin/add-sample-payment', methods=['POST'])
  def api_add_sample_payment():
    try:
      cur, conn = mysql.cursor()
      
      # Get all requests without payment data
      cur.execute("""
        SELECT id FROM clearance_requests 
        WHERE payment_method IS NULL OR payment_method = ''
        LIMIT 5
      """)
      requests = cur.fetchall()
      
      if not requests:
        return jsonify({"ok": False, "message": "No requests found without payment data"})
      
      # Add sample payment data to each request
      for req in requests:
        sample_payment_details = {
          "amount_verified": 50.00,
          "reference_number": f"GC{req['id']:06d}",
          "verification_status": "verified"
        }
        
        cur.execute("""
          UPDATE clearance_requests 
          SET payment_method = 'gcash', 
              payment_amount = 50.00, 
              payment_verified = TRUE, 
              payment_details = %s
          WHERE id = %s
        """, (json.dumps(sample_payment_details), req['id']))
      
      # No need to commit with autocommit=True
      cur.close()
      conn.close()
      
      return jsonify({
        "ok": True, 
        "message": f"Added sample payment data to {len(requests)} requests",
        "updated_count": len(requests)
      })
      
    except Exception as err:
      return jsonify({"ok": False, "message": f"Error: {err}"}), 500

  # Temporary route to fix payment_receipt column issue
  @app.route('/fix-payment-receipt-column', methods=['GET'])
  def fix_payment_receipt_column():
    """Temporary route to fix the missing payment_receipt column"""
    try:
      cur, conn = mysql.cursor()
      
      # Check if payment_receipt column exists
      cur.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'clearance_requests' 
        AND COLUMN_NAME = 'payment_receipt'
      """)
      
      if cur.fetchone():
        return jsonify({
          "ok": True, 
          "message": "payment_receipt column already exists",
          "status": "already_exists"
        })
      else:
        # Add the missing column
        cur.execute("""
          ALTER TABLE clearance_requests 
          ADD COLUMN payment_receipt LONGTEXT NULL
        """)
        
        # No need to commit with autocommit=True
        cur.close()
        conn.close()
        
        return jsonify({
          "ok": True, 
          "message": "payment_receipt column added successfully",
          "status": "added"
        })
        
    except Exception as err:
      return jsonify({
        "ok": False, 
        "message": f"Error fixing payment_receipt column: {err}",
        "status": "error"
      }), 500

  # Initialize database structures at startup
  with app.app_context():
    try:
      init_db()
      print("✅ Database initialization completed successfully")
    except Exception as e:
      print(f"❌ Database initialization failed: {e}")
      print("⚠️ Application will continue but database operations may fail")

  return app


app = create_app()


def test_database_connection():
  """Test database connection and provide helpful error messages"""
  if pymysql is None:
    print("⚠️ PyMySQL not available - database features will be disabled")
    return False
  try:
    # Test connection to the database server
    test_conn = pymysql.connect(
      host=app.config['MYSQL_HOST'], 
      user=app.config['MYSQL_USER'], 
      password=app.config['MYSQL_PASSWORD'],
      connect_timeout=10
    )
    test_conn.close()
    print("✓ Database server connection successful")
    return True
  except pymysql.Error as e:
    print(f"✗ Database connection failed: {e}")
    print(f"  Host: {app.config['MYSQL_HOST']}")
    print(f"  User: {app.config['MYSQL_USER']}")
    print("  Please check:")
    print("  1. Database server is running")
    print("  2. Network connectivity to the database")
    print("  3. Database credentials are correct")
    print("  4. Firewall/security group settings")
    return False
  except Exception as e:
    print(f"✗ Unexpected error: {e}")
    return False

if __name__ == '__main__':
  # For local development with proper error handling
  print("=" * 50)
  print("Starting iRequest Flask Application")
  print("=" * 50)
  
  # Test database connection first
  db_available = test_database_connection()
  if not db_available:
    print("\n⚠️ Database not available - running in limited mode")
    print("Some features may not work properly without database connection.")
  
  try:
    print("\n🚀 Starting Flask server...")
    print(f"📊 Database: {app.config['MYSQL_HOST']}")
    print("🌐 Server will be available at: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
  except Exception as e:
    print(f"\n❌ Error starting Flask application: {e}")
    print("Please check your configuration and try again.")








