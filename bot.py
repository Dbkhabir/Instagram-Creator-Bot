"""
Main Telegram Bot for Instagram account creation
Telegram bot এর main file - সব command এখানে handle হবে
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode

from config import config, messages
from database import db
from instagram_creator import instagram_creator
from utils import (
    rate_limiter,
    text_formatter,
    validation_helper,
    error_handler,
    log_execution_time
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)


class InstagramBot:
    """Main bot class"""
    
    def __init__(self):
        self.app = None
        self.creation_in_progress = {}  # Track ongoing creations
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /start command handler
        Bot start করার command
        """
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name
        
        logger.info(f"User {username} ({user_id}) started the bot")
        
        # Create welcome keyboard
        keyboard = [
            [InlineKeyboardButton("🚀 Create Account", callback_data='create_account')],
            [InlineKeyboardButton("📊 My Accounts", callback_data='view_accounts')],
            [InlineKeyboardButton("❓ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            messages.START,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /help command handler
        Help message show করা
        """
        await update.message.reply_text(
            messages.HELP,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def create_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /create command handler
        Instagram account create করার command
        """
        user_id = str(update.effective_user.id)
        
        # Check if user is authorized (if ALLOWED_USERS is set)
        if config.ALLOWED_USERS and config.ALLOWED_USERS[0]:
            if user_id not in config.ALLOWED_USERS:
                await update.message.reply_text(
                    "❌ **Access Denied** \n\nYou are not authorized to use this bot.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # Check rate limit
        is_limited, remaining = rate_limiter.is_rate_limited(
            user_id,
            config.COOLDOWN_BETWEEN_ACCOUNTS
        )
        
        if is_limited:
            await update.message.reply_text(
                messages.RATE_LIMIT.format(seconds=remaining),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Check account limit
        account_count = db.count_user_accounts(user_id)
        
        if account_count >= config.MAX_ACCOUNTS_PER_USER:
            await update.message.reply_text(
                messages.MAX_ACCOUNTS.format(max=config.MAX_ACCOUNTS_PER_USER),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Check if creation already in progress
        if user_id in self.creation_in_progress:
            await update.message.reply_text(
                "⚠️ **Creation In Progress** \n\nPlease wait for the current account creation to complete.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Start account creation
        await self.create_account(update, context)
    
    @log_execution_time
    async def create_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Main account creation function
        Account create করার main function
        """
        user_id = str(update.effective_user.id)
        
        try:
            # Mark creation as in progress
            self.creation_in_progress[user_id] = True
            
            # Send initial message
            status_msg = await update.message.reply_text(
                messages.CREATING,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log creation attempt
            db.log_creation_attempt(user_id, 'pending', 'unknown')
            
            # Update status: Creating email
            await status_msg.edit_text(
                "🔄 **Creating Instagram account...** \n\n"
                "📧 Step 1/5: Creating temporary email...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Create account using instagram_creator
            result = await asyncio.to_thread(
                instagram_creator.create_full_account
            )
            
            if result['status'] == 'success':
                # Save to database
                backup_codes_str = '\n'.join(result.get('backup_codes', []))
                
                account = db.add_account(
                    telegram_user_id=user_id,
                    username=result['username'],
                    password=result['password'],
                    email=result['email'],
                    email_provider=result['email_provider'],
                    two_fa_secret=result.get('two_fa_secret'),
                    backup_codes=backup_codes_str
                )
                
                # Log success
                db.log_creation_attempt(
                    user_id,
                    'success',
                    result['email_provider'],
                    duration_seconds=result.get('duration_seconds')
                )
                
                # Format success message
                success_text = messages.SUCCESS.format(
                    username=result['username'],
                    password=result['password'],
                    email=result['email'],
                    provider=result['email_provider'].title(),
                    secret_key=result.get('two_fa_secret', 'N/A'),
                    backup_codes='\n'.join([f"• `{code}`" for code in result.get('backup_codes', [])[:5]])
                )
                
                await status_msg.edit_text(
                    success_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                logger.info(f"✅ Account created for user {user_id}: {result['username']}")
                
            else:
                # Log failure
                db.log_creation_attempt(
                    user_id,
                    'failed',
                    result.get('email_provider', 'unknown'),
                    error_message=result.get('error')
                )
                
                error_text = messages.ERROR.format(
                    error=result.get('error', 'Unknown error occurred')
                )
                
                await status_msg.edit_text(
                    error_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                logger.error(f"❌ Account creation failed for user {user_id}: {result.get('error')}")
        
        except Exception as e:
            error_handler.log_error(e, "create_account")
            
            # Log exception
            db.log_creation_attempt(
                user_id,
                'failed',
                'unknown',
                error_message=str(e)
            )
            
            error_text = messages.ERROR.format(
                error=error_handler.get_user_friendly_error(e)
            )
            
            await update.message.reply_text(
                error_text,
                parse_mode=ParseMode.MARKDOWN
            )
        
        finally:
            # Remove from in-progress
            if user_id in self.creation_in_progress:
                del self.creation_in_progress[user_id]
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /history command handler
        User এর সব account দেখানো
        """
        user_id = str(update.effective_user.id)
        
        try:
            # Get user's accounts
            accounts = db.get_user_accounts(user_id)
            
            if not accounts:
                await update.message.reply_text(
                    "📭 **No Accounts** \n\nYou haven't created any accounts yet.\n\nUse /create to create your first account!",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Format account list
            account_text = text_formatter.format_account_list(accounts)
            
            await update.message.reply_text(
                account_text,
                parse_mode=ParseMode.MARKDOWN
            )
        
        except Exception as e:
            error_handler.log_error(e, "history_command")
            await update.message.reply_text(
                messages.ERROR.format(error="Failed to retrieve account history"),
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /status command handler
        Bot এর current status দেখানো
        """
        user_id = str(update.effective_user.id)
        
        # Get user stats
        account_count = db.count_user_accounts(user_id)
        is_creating = user_id in self.creation_in_progress
        
        # Check rate limit
        is_limited, remaining = rate_limiter.is_rate_limited(user_id, 0)
        
        status_text = "📊 **Your Status** \n\n"
        status_text += f"👤 **Accounts Created:** {account_count}/{config.MAX_ACCOUNTS_PER_USER}\n"
        status_text += f"🔄 **Currently Creating:** {'Yes ⏳' if is_creating else 'No ✅'}\n"
        
        if is_limited:
            status_text += f"⏳ **Cooldown:** {remaining} seconds remaining\n"
        else:
            status_text += f"✅ **Ready:** You can create a new account\n"
        
        status_text += f"\n **Commands:** \n"
        status_text += f"• /create - Create new account\n"
        status_text += f"• /history - View your accounts\n"
        status_text += f"• /help - Show help"
        
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle inline button callbacks
        Inline button এর callback handle করা
        """
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        
        if query.data == 'create_account':
            # Simulate /create command
            update.message = query.message
            await self.create_command(update, context)
        
        elif query.data == 'view_accounts':
            # Simulate /history command
            update.message = query.message
            await self.history_command(update, context)
        
        elif query.data == 'help':
            await query.edit_message_text(
                messages.HELP,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def error_handler_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Global error handler
        সব error এখানে handle হবে
        """
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ **An error occurred** \n\nPlease try again or contact the administrator.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    def run(self):
        """
        Start the bot
        Bot run করা
        """
        logger.info("🚀 Starting Instagram Account Creator Bot...")
        
        # Create application
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Add command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("create", self.create_command))
        self.app.add_handler(CommandHandler("history", self.history_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        
        # Add callback query handler
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Add error handler
        self.app.add_error_handler(self.error_handler_callback)
        
        # Start bot
        logger.info("✅ Bot is running...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point"""
    bot = InstagramBot()
    bot.run()


if __name__ == '__main__':
    main()