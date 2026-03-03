"""
Multiple temporary email providers with intelligent rotation
৫টি email provider যেখানে automatic failover system আছে
"""

import requests
import random
import string
import time
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from config import config
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailProvider:
    """Base class for email providers"""
    
    def __init__(self, name: str):
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def generate_random_username(self, length=10):
        """Generate random email username"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def create_email(self) -> Optional[Dict]:
        """Create temporary email - প্রতিটা provider এ override করতে হবে"""
        raise NotImplementedError
    
    def fetch_messages(self, email_data: Dict) -> List[Dict]:
        """Fetch email messages"""
        raise NotImplementedError
    
    def get_verification_code(self, email_data: Dict, timeout=120) -> Optional[str]:
        """Wait for and extract Instagram verification code"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                messages = self.fetch_messages(email_data)
                
                for msg in messages:
                    # Instagram verification email check
                    subject = msg.get('subject', '').lower()
                    body = msg.get('body', '')
                    
                    if 'instagram' in subject or 'verification' in subject:
                        # Extract code (usually 6 digits)
                        import re
                        code_match = re.search(r'\b(\d{6})\b', body)
                        if code_match:
                            logger.info(f"Verification code found: {code_match.group(1)}")
                            return code_match.group(1)
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                time.sleep(5)
        
        return None


class TempMailProvider(EmailProvider):
    """TempMail.lol - Most reliable provider (Priority 1)"""
    
    def __init__(self):
        super().__init__("tempmail")
        self.base_url = "https://api.tempmail.lol"
    
    def create_email(self) -> Optional[Dict]:
        """Create email on TempMail"""
        try:
            start_time = time.time()
            
            # Generate random email
            response = self.session.get(
                f"{self.base_url}/generate",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            duration_ms = int((time.time() - start_time) * 1000)
            
            if data.get('address'):
                result = {
                    'email': data['address'],
                    'token': data.get('token', data['address']),
                    'provider': self.name
                }
                
                db.update_provider_stats(self.name, True, duration_ms)
                logger.info(f"✅ TempMail created: {result['email']}")
                return result
            
        except Exception as e:
            logger.error(f"❌ TempMail error: {e}")
            db.update_provider_stats(self.name, False, 0)
        
        return None
    
    def fetch_messages(self, email_data: Dict) -> List[Dict]:
        """Fetch messages from TempMail"""
        try:
            token = email_data['token']
            response = self.session.get(
                f"{self.base_url}/auth/{token}",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('email', [])
            
        except Exception as e:
            logger.error(f"Error fetching TempMail messages: {e}")
            return []


class GuerrillaMailProvider(EmailProvider):
    """GuerrillaMail - Reliable backup (Priority 2)"""
    
    def __init__(self):
        super().__init__("guerrillamail")
        self.base_url = "https://api.guerrillamail.com/ajax.php"
        self.sid_token = None
    
    def create_email(self) -> Optional[Dict]:
        """Create email on GuerrillaMail"""
        try:
            start_time = time.time()
            
            # Get email address
            response = self.session.get(
                self.base_url,
                params={'f': 'get_email_address', 'ip': '127.0.0.1'},
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            duration_ms = int((time.time() - start_time) * 1000)
            
            if data.get('email_addr'):
                self.sid_token = data.get('sid_token')
                result = {
                    'email': data['email_addr'],
                    'token': self.sid_token,
                    'provider': self.name
                }
                
                db.update_provider_stats(self.name, True, duration_ms)
                logger.info(f"✅ GuerrillaMail created: {result['email']}")
                return result
            
        except Exception as e:
            logger.error(f"❌ GuerrillaMail error: {e}")
            db.update_provider_stats(self.name, False, 0)
        
        return None
    
    def fetch_messages(self, email_data: Dict) -> List[Dict]:
        """Fetch messages from GuerrillaMail"""
        try:
            response = self.session.get(
                self.base_url,
                params={
                    'f': 'get_email_list',
                    'sid_token': email_data['token'],
                    'offset': 0
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            messages = []
            
            for msg in data.get('list', []):
                # Get full message body
                body_response = self.session.get(
                    self.base_url,
                    params={
                        'f': 'fetch_email',
                        'sid_token': email_data['token'],
                        'email_id': msg['mail_id']
                    }
                )
                body_data = body_response.json()
                
                messages.append({
                    'subject': msg.get('mail_subject', ''),
                    'body': body_data.get('mail_body', '')
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching GuerrillaMail messages: {e}")
            return []


class MailinatorProvider(EmailProvider):
    """Mailinator - Simple and reliable (Priority 3)"""
    
    def __init__(self):
        super().__init__("mailinator")
        self.base_url = "https://www.mailinator.com/api/v2"
        self.domain = "mailinator.com"
    
    def create_email(self) -> Optional[Dict]:
        """Create email on Mailinator (no API needed, just generate)"""
        try:
            start_time = time.time()
            
            # Generate random inbox name
            inbox_name = self.generate_random_username()
            email = f"{inbox_name}@{self.domain}"
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            result = {
                'email': email,
                'token': inbox_name,
                'provider': self.name
            }
            
            db.update_provider_stats(self.name, True, duration_ms)
            logger.info(f"✅ Mailinator created: {result['email']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Mailinator error: {e}")
            db.update_provider_stats(self.name, False, 0)
        
        return None
    
    def fetch_messages(self, email_data: Dict) -> List[Dict]:
        """Fetch messages from Mailinator (web scraping)"""
        try:
            inbox = email_data['token']
            
            # Use public inbox endpoint
            url = f"https://www.mailinator.com/v4/public/inboxes.jsp?to={inbox}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML for messages (simplified)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            messages = []
            # Note: This is simplified - you may need to adjust selectors
            for row in soup.select('tr.ng-scope'):
                subject_elem = row.select_one('.ng-binding')
                if subject_elem and 'instagram' in subject_elem.text.lower():
                    messages.append({
                        'subject': subject_elem.text,
                        'body': row.text
                    })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching Mailinator messages: {e}")
            return []


class TenMinuteMailProvider(EmailProvider):
    """10MinuteMail - Fast alternative (Priority 4)"""
    
    def __init__(self):
        super().__init__("tenminutemail")
        self.base_url = "https://10minutemail.com"
    
    def create_email(self) -> Optional[Dict]:
        """Create email on 10MinuteMail"""
        try:
            start_time = time.time()
            
            # Get session and email
            response = self.session.get(
                f"{self.base_url}/session/address",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            duration_ms = int((time.time() - start_time) * 1000)
            
            if data.get('address'):
                result = {
                    'email': data['address'],
                    'token': self.session.cookies.get('JSESSIONID', ''),
                    'provider': self.name
                }
                
                db.update_provider_stats(self.name, True, duration_ms)
                logger.info(f"✅ 10MinuteMail created: {result['email']}")
                return result
            
        except Exception as e:
            logger.error(f"❌ 10MinuteMail error: {e}")
            db.update_provider_stats(self.name, False, 0)
        
        return None
    
    def fetch_messages(self, email_data: Dict) -> List[Dict]:
        """Fetch messages from 10MinuteMail"""
        try:
            response = self.session.get(
                f"{self.base_url}/messages/messagesAfter/0",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            messages = []
            
            for msg in data:
                messages.append({
                    'subject': msg.get('subject', ''),
                    'body': msg.get('bodyPreview', '')
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching 10MinuteMail messages: {e}")
            return []


class TempEmailAddressProvider(EmailProvider):
    """Temp-Mail.org - Last resort (Priority 5)"""
    
    def __init__(self):
        super().__init__("tempemailaddress")
        self.base_url = "https://temp-mail.org"
    
    def create_email(self) -> Optional[Dict]:
        """Create email on Temp-Mail.org"""
        try:
            start_time = time.time()
            
            # Get available domains
            response = self.session.get(
                f"{self.base_url}/en/option/change/",
                timeout=15
            )
            
            # Generate email
            username = self.generate_random_username()
            email = f"{username}@exelica.com"  # Common domain
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            result = {
                'email': email,
                'token': email,
                'provider': self.name
            }
            
            db.update_provider_stats(self.name, True, duration_ms)
            logger.info(f"✅ TempEmailAddress created: {result['email']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ TempEmailAddress error: {e}")
            db.update_provider_stats(self.name, False, 0)
        
        return None
    
    def fetch_messages(self, email_data: Dict) -> List[Dict]:
        """Fetch messages from Temp-Mail.org"""
        try:
            # This would require more complex web scraping
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Error fetching TempEmailAddress messages: {e}")
            return []


class EmailServiceRotator:
    """
    Intelligent email service rotation with failover
    স্মার্ট rotation system যেখানে automatic failover আছে
    """
    
    def __init__(self):
        self.providers = [
            TempMailProvider(),
            GuerrillaMailProvider(),
            MailinatorProvider(),
            TenMinuteMailProvider(),
            TempEmailAddressProvider()
        ]
        
        self.current_index = 0
        self.failed_providers = set()
    
    def get_next_provider(self) -> EmailProvider:
        """Get next available email provider with intelligent selection"""
        
        # First, try to get best provider from database stats
        best_provider_name = db.get_best_email_provider()
        
        if best_provider_name:
            for provider in self.providers:
                if provider.name == best_provider_name and provider.name not in self.failed_providers:
                    logger.info(f"🎯 Using best provider: {provider.name}")
                    return provider
        
        # Otherwise, rotate through providers
        attempts = 0
        while attempts < len(self.providers):
            provider = self.providers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.providers)
            
            if provider.name not in self.failed_providers:
                logger.info(f"🔄 Rotating to provider: {provider.name}")
                return provider
            
            attempts += 1
        
        # If all providers failed, reset and try again
        logger.warning("⚠️ All providers failed, resetting...")
        self.failed_providers.clear()
        return self.providers[0]
    
    def mark_provider_failed(self, provider_name: str):
        """Mark provider as failed temporarily"""
        self.failed_providers.add(provider_name)
        logger.warning(f"❌ Marked {provider_name} as failed")
    
    def create_email_with_rotation(self, max_attempts=5) -> Optional[Dict]:
        """
        Create email with automatic provider rotation
        যদি একটা provider fail করে তাহলে automatically next এ যাবে
        """
        
        for attempt in range(max_attempts):
            provider = self.get_next_provider()
            
            logger.info(f"🔧 Attempt {attempt + 1}/{max_attempts} with {provider.name}")
            
            email_data = provider.create_email()
            
            if email_data:
                logger.info(f"✅ Successfully created email with {provider.name}")
                return email_data
            else:
                self.mark_provider_failed(provider.name)
                logger.warning(f"❌ Failed with {provider.name}, trying next...")
                time.sleep(2)  # Wait before trying next provider
        
        logger.error("❌ All email providers failed!")
        return None
    
    def get_provider_by_name(self, name: str) -> Optional[EmailProvider]:
        """Get specific provider by name"""
        for provider in self.providers:
            if provider.name == name:
                return provider