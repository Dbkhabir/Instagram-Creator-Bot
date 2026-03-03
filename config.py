"""
Configuration file for Instagram Bot
বট এর সব কনফিগারেশন এখানে থাকবে
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Main configuration class"""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7926814511:AAGd1h5ZHbCke6XThnZUKIeg5kHZcUnam18")
    ALLOWED_USERS = os.getenv("ALLOWED_USERS", "5340147496").split(",")  # Comma-separated user IDs
    
    # Render Deployment (Web service URL for webhook)
    RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")
    PORT = int(os.getenv("PORT", 8000))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///instagram_bot.db")
    
    # Email Providers Configuration
    EMAIL_PROVIDERS = {
        "tempmail": {
            "enabled": True,
            "priority": 1,
            "api_url": "https://api.tempmail.lol",
            "timeout": 10,
            "max_retries": 3
        },
        "guerrillamail": {
            "enabled": True,
            "priority": 2,
            "api_url": "https://api.guerrillamail.com",
            "timeout": 15,
            "max_retries": 3
        },
        "mailinator": {
            "enabled": True,
            "priority": 3,
            "api_url": "https://www.mailinator.com",
            "timeout": 10,
            "max_retries": 2
        },
        "tenminutemail": {
            "enabled": True,
            "priority": 4,
            "api_url": "https://10minutemail.com",
            "timeout": 10,
            "max_retries": 2
        },
        "tempemailaddress": {
            "enabled": True,
            "priority": 5,
            "api_url": "https://temp-mail.org",
            "timeout": 15,
            "max_retries": 2
        }
    }
    
    # Instagram Configuration
    INSTAGRAM_BASE_URL = "https://i.instagram.com/api/v1"
    INSTAGRAM_USER_AGENT = "Instagram 275.0.0.27.98 Android (28/9; 480dpi; 1080x2220; OnePlus; ONEPLUS A6003; OnePlus6; qcom; en_US; 458229237)"
    
    # Captcha Configuration
    USE_FREE_OCR = True  # Try free OCR first
    CAPTCHA_2CAPTCHA_KEY = os.getenv("CAPTCHA_2CAPTCHA_KEY", "")  # Optional fallback
    
    # Proxy Configuration (Optional)
    USE_PROXY = os.getenv("USE_PROXY", "false").lower() == "true"
    PROXY_LIST = os.getenv("PROXY_LIST", "").split(",")
    
    # Rate Limiting
    MAX_ACCOUNTS_PER_USER = 10
    COOLDOWN_BETWEEN_ACCOUNTS = 30  # seconds
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = "instagram_bot.log"


class Messages:
    """Bot messages - সব মেসেজ এখানে থাকবে"""
    
    START = """
🤖 **Welcome to Instagram Account Creator Bot** 
I can create Instagram accounts automatically with:
✅ Temporary email (5 providers with rotation)
✅ Captcha solving (free OCR + paid fallback)
✅ 2FA setup with secret key
✅ Complete credential delivery
 **Commands:** /create - Create new Instagram account
/status - Check creation status
/history - View your created accounts
/help - Show help message
 **Ready to start?** Click /create
"""
    
    HELP = """
📖 **Help & Instructions**  **How to create an account:** 1. Send /create command
2. Wait for the bot to process
3. Receive account credentials
 **What you'll get:** - Username
- Password
- Email address
- 2FA secret key
- Backup codes
 **Email Providers (Auto-rotation):** 1. TempMail (Primary)
2. GuerrillaMail (Backup)
3. Mailinator (Secondary)
4. 10MinuteMail (Alternative)
5. TempEmailAddress (Last resort)
 **Limitations:** - Maximum 10 accounts per user
- 30 seconds cooldown between creations
- Account creation takes 2-5 minutes

Need help? Contact admin.
"""
    
    CREATING = "🔄 **Creating Instagram account...** \n\nThis will take 2-5 minutes. Please wait..."
    
    SUCCESS = """
✅ **Account Created Successfully!**  **Username:** `{username}` **Password:** `{password}` **Email:** `{email}` **Email Provider:** {provider}
 **🔐 2FA Details:**  **Secret Key:** `{secret_key}` **Backup Codes:** {backup_codes}
 **⚠️ Important:** - Save this information securely
- Enable 2FA in Instagram app
- Keep backup codes safe
 **Next Steps:** 1. Login to Instagram app
2. Verify email if needed
3. Complete profile setup
"""
    
    ERROR = "❌ **Error:** {error}\n\nPlease try again or contact admin."
    
    RATE_LIMIT = "⏳ **Rate Limit:** Please wait {seconds} seconds before creating another account."
    
    MAX_ACCOUNTS = "⛔ **Limit Reached:** You've created maximum {max} accounts."


# Export configuration
config = Config()
messages = Messages()
