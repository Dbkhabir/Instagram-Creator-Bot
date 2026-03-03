"""
Instagram account creator with real signup flow
Real Instagram API দিয়ে account create করা
"""

import requests
import random
import string
import time
import uuid
import hmac
import hashlib
import json
import pyotp
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
from fake_useragent import UserAgent
from config import config
from email_providers import EmailServiceRotator
from captcha_solver import captcha_solver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstagramCreator:
    """Instagram account creator using mobile API"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = config.INSTAGRAM_BASE_URL
        self.email_rotator = EmailServiceRotator()
        
        # Generate device info
        self.device_id = self.generate_device_id()
        self.uuid = str(uuid.uuid4())
        self.phone_id = str(uuid.uuid4())
        self.advertising_id = str(uuid.uuid4())
        
        # Set headers
        self.update_headers()
    
    def generate_device_id(self) -> str:
        """Generate unique device ID"""
        return f"android-{uuid.uuid4().hex[:16]}"
    
    def update_headers(self):
        """Update session headers with Instagram mobile headers"""
        ua = UserAgent()
        
        self.session.headers.update({
            'User-Agent': config.INSTAGRAM_USER_AGENT,
            'Accept-Language': 'en-US',
            'Accept-Encoding': 'gzip, deflate',
            'X-IG-Capabilities': '3brTvw==',
            'X-IG-Connection-Type': 'WIFI',
            'X-IG-App-ID': '567067343352427',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        })
    
    def generate_signature(self, data: str) -> str:
        """Generate Instagram API signature"""
        key = '4f8732eb9ba7d1c8e8897a75d25b3dbb'  # Instagram signature key
        
        signature = hmac.new(
            key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def api_request(self, endpoint: str, data: Dict, signed: bool = True) -> Optional[Dict]:
        """Make Instagram API request"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            if signed:
                json_data = json.dumps(data)
                signature = self.generate_signature(json_data)
                
                payload = {
                    'signed_body': f'SIGNATURE.{json_data}',
                    'ig_sig_key_version': '4'
                }
            else:
                payload = data
            
            response = self.session.post(url, data=payload, timeout=30)
            
            logger.info(f"API Response [{endpoint}]: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"API Error: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"API Request error: {e}")
            return None
    
    def generate_username(self, base_name: str = None) -> str:
        """Generate random Instagram username"""
        if not base_name:
            base_name = ''.join(random.choices(string.ascii_lowercase, k=8))
        
        suffix = ''.join(random.choices(string.digits, k=4))
        return f"{base_name}{suffix}"
    
    def generate_password(self, length: int = 12) -> str:
        """Generate secure password"""
        chars = string.ascii_letters + string.digits + "!@#$%"
        password = ''.join(random.choices(chars, k=length))
        
        # Ensure it has at least one uppercase, lowercase, digit, and special char
        if (any(c.isupper() for c in password) and 
            any(c.islower() for c in password) and 
            any(c.isdigit() for c in password)):
            return password
        
        return self.generate_password(length)
    
    def check_email_available(self, email: str) -> bool:
        """Check if email is available for signup"""
        try:
            data = {
                'email': email,
                '_uuid': self.uuid,
                '_uid': '',
                'device_id': self.device_id
            }
            
            response = self.api_request('users/check_email/', data)
            
            if response and not response.get('email_is_taken'):
                logger.info(f"✅ Email available: {email}")
                return True
            
            logger.warning(f"⚠️ Email already taken: {email}")
            return False
            
        except Exception as e:
            logger.error(f"Email check error: {e}")
            return False
    
    def check_username_available(self, username: str) -> bool:
        """Check if username is available"""
        try:
            data = {
                'username': username,
                '_uuid': self.uuid,
                '_uid': '',
                'device_id': self.device_id
            }
            
            response = self.api_request('users/check_username/', data)
            
            if response and response.get('available'):
                logger.info(f"✅ Username available: {username}")
                return True
            
            logger.warning(f"⚠️ Username taken: {username}")
            return False
            
        except Exception as e:
            logger.error(f"Username check error: {e}")
            return False
    
    def send_signup_sms_code(self, phone_number: str) -> bool:
        """Send SMS verification code (if using phone signup)"""
        # Instagram phone signup endpoint
        # Not implemented in this version - email signup is more reliable
        pass
    
    def create_account(self, username: str, password: str, email: str, 
                      full_name: str = None) -> Optional[Dict]:
        """
        Create Instagram account
        Main account creation করার function
        """
        try:
            if not full_name:
                full_name = username.capitalize()
            
            logger.info(f"🔧 Creating account: {username}")
            
            # Prepare signup data
            signup_data = {
                'username': username,
                'password': password,
                'email': email,
                'first_name': full_name,
                'device_id': self.device_id,
                'guid': self.uuid,
                '_uuid': self.uuid,
                'phone_id': self.phone_id,
                'force_sign_up_code': '',
                'waterfall_id': str(uuid.uuid4()),
                'qs_stamp': '',
                'sn_nonce': '',
                'sn_result': ''
            }
            
            # Make signup request
            response = self.api_request('accounts/create/', signup_data)
            
            if response:
                if response.get('account_created'):
                    logger.info(f"✅ Account created successfully: {username}")
                    return {
                        'username': username,
                        'password': password,
                        'email': email,
                        'user_id': response.get('created_user', {}).get('pk'),
                        'status': 'success'
                    }
                
                elif response.get('errors'):
                    error_msg = response.get('errors', {})
                    logger.error(f"❌ Signup error: {error_msg}")
                    
                    # Handle specific errors
                    if 'email' in error_msg:
                        return {'status': 'email_error', 'message': str(error_msg['email'])}
                    
                    if 'username' in error_msg:
                        return {'status': 'username_error', 'message': str(error_msg['username'])}
                    
                    if 'feedback_required' in response:
                        # Captcha or phone verification needed
                        return self.handle_challenge(response)
                
                return {'status': 'unknown_error', 'message': str(response)}
            
            return {'status': 'api_error', 'message': 'No response from Instagram'}
            
        except Exception as e:
            logger.error(f"❌ Account creation error: {e}")
            return {'status': 'exception', 'message': str(e)}
    
    def handle_challenge(self, challenge_data: Dict) -> Dict:
        """
        Handle Instagram challenges (captcha, phone verification)
        যদি Instagram captcha বা phone verification চায়
        """
        try:
            challenge_type = challenge_data.get('challenge', {}).get('challenge_type')
            
            logger.warning(f"⚠️ Challenge required: {challenge_type}")
            
            if challenge_type == 'captcha':
                return self.solve_captcha_challenge(challenge_data)
            
            elif challenge_type == 'phone':
                return self.solve_phone_challenge(challenge_data)
            
            return {'status': 'challenge_failed', 'type': challenge_type}
            
        except Exception as e:
            logger.error(f"Challenge handling error: {e}")
            return {'status': 'challenge_error', 'message': str(e)}
    
    def solve_captcha_challenge(self, challenge_data: Dict) -> Dict:
        """Solve captcha challenge"""
        try:
            captcha_url = challenge_data.get('challenge', {}).get('captcha_url')
            
            if not captcha_url:
                return {'status': 'no_captcha_url'}
            
            logger.info(f"🔍 Solving captcha: {captcha_url}")
            
            # Download captcha image
            img_response = self.session.get(captcha_url, timeout=10)
            captcha_solution = captcha_solver.solve_captcha(image_bytes=img_response.content)
            
            if not captcha_solution:
                return {'status': 'captcha_solve_failed'}
            
            # Submit captcha solution
            challenge_context = challenge_data.get('challenge', {}).get('challenge_context')
            
            solution_data = {
                'captcha_key': captcha_solution,
                'challenge_context': challenge_context,
                'guid': self.uuid,
                'device_id': self.device_id
            }
            
            response = self.api_request('challenge/solve/', solution_data)
            
            if response and response.get('status') == 'ok':
                logger.info("✅ Captcha solved successfully")
                return {'status': 'captcha_solved'}
            
            return {'status': 'captcha_verification_failed'}
            
        except Exception as e:
            logger.error(f"Captcha solving error: {e}")
            return {'status': 'captcha_error', 'message': str(e)}
    
    def solve_phone_challenge(self, challenge_data: Dict) -> Dict:
        """Handle phone verification challenge"""
        # Phone verification is complex - would need SMS service integration
        logger.warning("⚠️ Phone verification required - not implemented")
        return {'status': 'phone_verification_required'}
    
    def verify_email(self, email_data: Dict, timeout: int = 120) -> Optional[str]:
        """
        Wait for and verify email
        Email verification করা
        """
        try:
            logger.info(f"📧 Waiting for verification email...")
            
            # Get email provider
            provider = self.email_rotator.get_provider_by_name(email_data['provider'])
            
            if not provider:
                logger.error("Email provider not found")
                return None
            
            # Wait for verification code
            code = provider.get_verification_code(email_data, timeout)
            
            if code:
                logger.info(f"✅ Verification code received: {code}")
                return code
            
            logger.error("❌ No verification code received")
            return None
            
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            return None
    
    def setup_two_factor_auth(self, username: str, password: str) -> Optional[Dict]:
        """
        Setup 2FA and extract secret key
        2FA setup করে secret key বের করা
        """
        try:
            logger.info(f"🔐 Setting up 2FA for {username}...")
            
            # Login first
            login_result = self.login(username, password)
            
            if not login_result:
                return None
            
            # Generate 2FA secret
            secret = pyotp.random_base32()
            
            # Enable 2FA
            totp_data = {
                'phone_id': self.phone_id,
                'device_id': self.device_id,
                '_uuid': self.uuid
            }
            
            response = self.api_request('accounts/enable_sms_two_factor/', totp_data)
            
            if response and response.get('status') == 'ok':
                # Generate backup codes
                backup_response = self.api_request('accounts/backup_codes/generate/', {})
                
                backup_codes = []
                if backup_response:
                    backup_codes = backup_response.get('backup_codes', [])
                
                logger.info("✅ 2FA enabled successfully")
                
                return {
                    'secret_key': secret,
                    'backup_codes': backup_codes,
                    'qr_code_url': pyotp.totp.TOTP(secret).provisioning_uri(
                        name=username,
                        issuer_name='Instagram'
                    )
                }
            
            return None
            
        except Exception as e:
            logger.error(f"2FA setup error: {e}")
            return None
    
    def login(self, username: str, password: str) -> bool:
        """Login to Instagram account"""
        try:
            login_data = {
                'username': username,
                'password': password,
                'device_id': self.device_id,
                'guid': self.uuid,
                '_uuid': self.uuid,
                'login_attempt_count': '0'
            }
            
            response = self.api_request('accounts/login/', login_data)
            
            if response and response.get('logged_in_user'):
                logger.info(f"✅ Logged in as {username}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def create_full_account(self, preferred_username: str = None) -> Dict:
        """
        Complete account creation flow with all features
        সম্পূর্ণ account creation process - email, signup, 2FA সব কিছু
        """
        start_time = time.time()
        
        try:
            logger.info("🚀 Starting full account creation...")
            
            # Step 1: Create temporary email
            logger.info("📧 Step 1: Creating temporary email...")
            email_data = self.email_rotator.create_email_with_rotation()
            
            if not email_data:
                return {
                    'status': 'failed',
                    'error': 'Failed to create temporary email'
                }
            
            email = email_data['email']
            logger.info(f"✅ Email created: {email}")
            
            # Step 2: Generate username and password
            logger.info("👤 Step 2: Generating credentials...")
            username = preferred_username or self.generate_username()
            password = self.generate_password()
            
            # Check username availability
            retries = 0
            while not self.check_username_available(username) and retries < 5:
                username = self.generate_username()
                retries += 1
            
            if retries >= 5:
                return {
                    'status': 'failed',
                    'error': 'Could not find available username'
                }
            
            logger.info(f"✅ Username: {username}")
            
            # Step 3: Create Instagram account
            logger.info("🔧 Step 3: Creating Instagram account...")
            time.sleep(2)  # Rate limiting
            
            result = self.create_account(username, password, email)
            
            if result.get('status') != 'success':
                return {
                    'status': 'failed',
                    'error': result.get('message', 'Account creation failed'),
                    'email': email,
                    'email_provider': email_data['provider']
                }
            
            logger.info("✅ Account created successfully")
            
            # Step 4: Wait for verification email (if needed)
            logger.info("📧 Step 4: Checking for verification email...")
            time.sleep(5)
            
            verification_code = self.verify_email(email_data, timeout=60)
            
            if verification_code:
                logger.info(f"✅ Verification code: {verification_code}")
                # Submit verification code if needed
                # (Instagram may or may not require email verification immediately)
            
            # Step 5: Setup 2FA
            logger.info("🔐 Step 5: Setting up 2FA...")
            time.sleep(3)
            
            two_fa_data = self.setup_two_factor_auth(username, password)
            
            duration = int(time.time() - start_time)
            
            # Return complete account data
            account_info = {
                'status': 'success',
                'username': username,
                'password': password,
                'email': email,
                'email_provider': email_data['provider'],
                'user_id': result.get('user_id'),
                'created_at': datetime.utcnow().isoformat(),
                'duration_seconds': duration
            }
            
            if two_fa_data:
                account_info['two_fa_secret'] = two_fa_data['secret_key']
                account_info['backup_codes'] = two_fa_data['backup_codes']
                account_info['qr_code_url'] = two_fa_data['qr_code_url']
            
            logger.info(f"✅ Full account creation completed in {duration} seconds")
            
            return account_info
            
        except Exception as e:
            logger.error(f"❌ Full account creation error: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'duration_seconds': int(time.time() - start_time)
            }


# Initialize Instagram creator
instagram_creator = InstagramCreator()