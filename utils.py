"""
Utility functions and helpers
সব helper function এখানে থাকবে
"""

import random
import string
import hashlib
import time
import logging
from typing import Optional, List
from datetime import datetime, timedelta
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for user actions
    User কতবার command দিতে পারবে সেটা control করা
    """
    
    def __init__(self):
        self.user_last_request = {}
        self.user_request_count = {}
    
    def is_rate_limited(self, user_id: str, cooldown_seconds: int = 30) -> tuple[bool, int]:
        """
        Check if user is rate limited
        Returns: (is_limited, seconds_remaining)
        """
        now = time.time()
        
        if user_id in self.user_last_request:
            time_passed = now - self.user_last_request[user_id]
            
            if time_passed < cooldown_seconds:
                remaining = int(cooldown_seconds - time_passed)
                return True, remaining
        
        self.user_last_request[user_id] = now
        return False, 0
    
    def increment_request_count(self, user_id: str):
        """Increment user request count"""
        if user_id not in self.user_request_count:
            self.user_request_count[user_id] = 0
        
        self.user_request_count[user_id] += 1
    
    def get_request_count(self, user_id: str) -> int:
        """Get user's total request count"""
        return self.user_request_count.get(user_id, 0)
    
    def reset_count(self, user_id: str):
        """Reset user's request count"""
        if user_id in self.user_request_count:
            del self.user_request_count[user_id]


class NameGenerator:
    """
    Generate realistic names for Instagram accounts
    Random realistic name generate করা
    """
    
    FIRST_NAMES = [
        'Alex', 'Sam', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery',
        'Jamie', 'Drew', 'Quinn', 'Blake', 'Reese', 'Cameron', 'Skyler', 'River',
        'Charlie', 'Rowan', 'Sage', 'Phoenix', 'Dakota', 'Emerson', 'Hayden', 'Finley'
    ]
    
    LAST_NAMES = [
        'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
        'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
        'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Thompson', 'White', 'Harris'
    ]
    
    @staticmethod
    def generate_full_name() -> str:
        """Generate random full name"""
        first = random.choice(NameGenerator.FIRST_NAMES)
        last = random.choice(NameGenerator.LAST_NAMES)
        return f"{first} {last}"
    
    @staticmethod
    def generate_username_from_name(full_name: str) -> str:
        """Generate username from name"""
        parts = full_name.lower().split()
        
        # Different username patterns
        patterns = [
            f"{parts[0]}{parts[1]}",
            f"{parts[0]}_{parts[1]}",
            f"{parts[0]}.{parts[1]}",
            f"{parts[0]}{parts[1]}{random.randint(10, 99)}",
            f"{parts[0][0]}{parts[1]}",
            f"{parts[1]}{parts[0][0]}",
        ]
        
        return random.choice(patterns)


class PasswordGenerator:
    """
    Generate secure passwords
    Strong password generate করা
    """
    
    @staticmethod
    def generate_strong_password(length: int = 12) -> str:
        """Generate cryptographically strong password"""
        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # Ensure at least one from each set
        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(special)
        ]
        
        # Fill the rest
        all_chars = lowercase + uppercase + digits + special
        password.extend(random.choices(all_chars, k=length - 4))
        
        # Shuffle
        random.shuffle(password)
        
        return ''.join(password)
    
    @staticmethod
    def generate_memorable_password() -> str:
        """Generate memorable but secure password"""
        words = ['Sky', 'Moon', 'Star', 'Sun', 'Fire', 'Water', 'Wind', 'Earth']
        word = random.choice(words)
        
        # Add numbers and special char
        return f"{word}{random.randint(100, 999)}!{random.choice(string.ascii_uppercase)}"


class HashHelper:
    """
    Hashing utilities
    Data hashing এর জন্য
    """
    
    @staticmethod
    def hash_string(text: str) -> str:
        """Generate SHA256 hash"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate random token"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))


class TimeHelper:
    """
    Time and date utilities
    Time related helper functions
    """
    
    @staticmethod
    def get_timestamp() -> str:
        """Get current timestamp"""
        return datetime.utcnow().isoformat()
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds} seconds"
        
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        
        if minutes < 60:
            return f"{minutes}m {remaining_seconds}s"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        return f"{hours}h {remaining_minutes}m"
    
    @staticmethod
    def is_expired(timestamp: str, duration_hours: int = 24) -> bool:
        """Check if timestamp is expired"""
        try:
            created = datetime.fromisoformat(timestamp)
            now = datetime.utcnow()
            
            return (now - created) > timedelta(hours=duration_hours)
        except:
            return True


class TextFormatter:
    """
    Text formatting utilities
    Text formatting এর জন্য
    """
    
    @staticmethod
    def format_account_info(account_data: dict) -> str:
        """Format account information for display"""
        text = f" **Account Details:** \n\n"
        text += f"👤 **Username:** `{account_data['username']}`\n"
        text += f"🔑 **Password:** `{account_data['password']}`\n"
        text += f"📧 **Email:** `{account_data['email']}`\n"
        text += f"📮 **Provider:** {account_data['email_provider']}\n\n"
        
        if account_data.get('two_fa_secret'):
            text += f"🔐 **2FA Secret:** `{account_data['two_fa_secret']}`\n"
        
        if account_data.get('backup_codes'):
            text += f"\n **Backup Codes:** \n"
            for code in account_data['backup_codes'][:5]:  # Show first 5
                text += f"• `{code}`\n"
        
        text += f"\n⏱ **Created:** {account_data.get('created_at', 'Just now')}"
        
        return text
    
    @staticmethod
    def format_account_list(accounts: list) -> str:
        """Format account list for display"""
        if not accounts:
            return "No accounts found."
        
        text = f" **Your Accounts ({len(accounts)}):** \n\n"
        
        for idx, account in enumerate(accounts, 1):
            text += f"{idx}. `{account.username}` - {account.email}\n"
            text += f"   📅 Created: {account.created_at.strftime('%Y-%m-%d')}\n\n"
        
        return text
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape markdown special characters"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text


class ValidationHelper:
    """
    Input validation utilities
    User input validate করা
    """
    
    @staticmethod
    def is_valid_username(username: str) -> bool:
        """Validate Instagram username format"""
        if not username:
            return False
        
        # Instagram username rules
        if len(username) < 1 or len(username) > 30:
            return False
        
        # Only letters, numbers, periods, and underscores
        import re
        pattern = r'^[a-zA-Z0-9._]+$'
        
        if not re.match(pattern, username):
            return False
        
        # Can't start or end with period
        if username.startswith('.') or username.endswith('.'):
            return False
        
        # Can't have consecutive periods
        if '..' in username:
            return False
        
        return True
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 100) -> str:
        """Sanitize user input"""
        # Remove special characters and limit length
        text = text.strip()
        text = text[:max_length]
        
        return text


class ErrorHandler:
    """
    Error handling and logging
    Error handling করা
    """
    
    @staticmethod
    def log_error(error: Exception, context: str = ""):
        """Log error with context"""
        logger.error(f"Error in {context}: {type(error).__name__}: {str(error)}")
    
    @staticmethod
    def get_user_friendly_error(error: Exception) -> str:
        """Convert exception to user-friendly message"""
        error_messages = {
            'ConnectionError': 'Network connection error. Please try again.',
            'Timeout': 'Request timed out. Please try again.',
            'ValueError': 'Invalid input provided.',
            'KeyError': 'Missing required information.',
            'Exception': 'An unexpected error occurred.'
        }
        
        error_type = type(error).__name__
        return error_messages.get(error_type, 'An error occurred. Please try again.')


def retry_on_failure(max_retries: int = 3, delay: int = 2):
    """
    Decorator to retry function on failure
    Function fail হলে automatically retry করবে
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                    else:
                        raise
            
            return None
        
        return wrapper
    
    return decorator


def log_execution_time(func):
    """
    Decorator to log function execution time
    Function কত সময় নিচ্ছে সেটা log করা
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        logger.info(f"{func.__name__} executed in {duration:.2f} seconds")
        
        return result
    
    return wrapper


# Initialize utilities
rate_limiter = RateLimiter()
name_generator = NameGenerator()
password_generator = PasswordGenerator()
hash_helper = HashHelper()
time_helper = TimeHelper()
text_formatter = TextFormatter()
validation_helper = ValidationHelper()
error_handler = ErrorHandler()