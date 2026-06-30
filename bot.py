"""
CutterPro1bot - A Telegram URL Shortener Bot
Shortens URLs instantly using TinyURL API
Ready for deployment on Railway using GitHub
"""

import os
import sys
import logging
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

if not BOT_TOKEN:
    print("❌ BOT_TOKEN is not set in environment variables")
    sys.exit(1)

# Logging setup
log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
BOT_NAME = "CutterPro1bot"
BOT_VERSION = "1.0.0"

# TinyURL API endpoint
TINYURL_API = "https://tinyurl.com/api-create.php"

# Alternative free APIs (fallback)
FALLBACK_APIS = [
    "https://is.gd/create.php",
    "https://v.gd/create.php"
]


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return re.match(url_pattern, url) is not None


def shorten_url_tinyurl(long_url: str) -> str:
    """Shorten a URL using TinyURL API."""
    try:
        response = requests.get(TINYURL_API, params={"url": long_url}, timeout=10)
        if response.status_code == 200:
            short_url = response.text.strip()
            if short_url.startswith("http"):
                return short_url
        return None
    except Exception as e:
        logger.error(f"TinyURL error: {e}")
        return None


def shorten_url_fallback(long_url: str) -> str:
    """Try alternative URL shorteners if TinyURL fails."""
    for api in FALLBACK_APIS:
        try:
            response = requests.get(api, params={"format": "simple", "url": long_url}, timeout=10)
            if response.status_code == 200:
                short_url = response.text.strip()
                if short_url.startswith("http"):
                    return short_url
        except Exception as e:
            logger.error(f"Fallback API error {api}: {e}")
            continue
    return None


# ============ COMMAND HANDLERS ============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    logger.info(f"✅ Start command from {user.id} ({user.username})")
    
    welcome_text = (
        f"✂️ **Hello {user.first_name}!**\n\n"
        "Welcome to **CutterPro1bot** - your professional URL cutter!\n\n"
        "📌 **How it works:**\n"
        "1. Send me any long URL\n"
        "2. I'll cut it down instantly\n"
        "3. Get your short link back!\n\n"
        "🔗 **Example:**\n"
        "`https://www.example.com/very/long/url`\n"
        "→ `https://tinyurl.com/abc123`\n\n"
        "📊 **Commands:**\n"
        "/start - Show this menu\n"
        "/help - Get help\n"
        "/about - Bot information"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✂️ Try It Now", callback_data="try_now")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "🆘 **Help Guide**\n\n"
        "📖 **How to use:**\n"
        "Simply send me any URL that starts with `http://` or `https://`\n\n"
        "✅ **Valid examples:**\n"
        "• `https://www.google.com`\n"
        "• `http://example.com`\n"
        "• `https://github.com/yourusername`\n\n"
        "❌ **Invalid examples:**\n"
        "• `www.google.com` (missing http://)\n"
        "• `google.com` (missing http://)\n"
        "• `not-a-url`\n\n"
        "⚡ **Tips:**\n"
        "• You can send multiple URLs one at a time\n"
        "• The bot uses TinyURL service\n"
        "• No registration required!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command"""
    about_text = (
        f"🤖 **{BOT_NAME}**\n\n"
        f"📌 Version: `{BOT_VERSION}`\n"
        "🔗 Service: TinyURL API\n"
        "⚡ Built with: `python-telegram-bot`\n"
        "📅 Status: ✅ **Online**\n\n"
        "🔹 **Features:**\n"
        "• Instant URL shortening\n"
        "• No registration required\n"
        "• Clean and simple interface\n"
        "• Multiple fallback APIs\n"
        "• Character savings display\n"
        "• Production-ready for Railway\n\n"
        f"💡 **Created for:** @{BOT_NAME}"
    )
    await update.message.reply_text(about_text, parse_mode="Markdown")


# ============ MESSAGE HANDLERS ============

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages (URL shortening)"""
    user = update.effective_user
    text = update.message.text.strip()
    
    logger.info(f"📩 Message from {user.id}: {text[:50]}...")
    
    # Check if it's a URL
    if not is_valid_url(text):
        await update.message.reply_text(
            "❌ **Invalid URL!**\n\n"
            "Please send a valid URL starting with `http://` or `https://`\n\n"
            "Example: `https://www.example.com`",
            parse_mode="Markdown"
        )
        return
    
    # Send "processing" message
    processing_msg = await update.message.reply_text("⏳ **Cutting your URL...**", parse_mode="Markdown")
    
    # Try primary URL shortener
    short_url = shorten_url_tinyurl(text)
    
    # If primary fails, try fallback
    if not short_url:
        short_url = shorten_url_fallback(text)
    
    if short_url:
        await processing_msg.delete()
        
        # Calculate length reduction
        original_len = len(text)
        short_len = len(short_url)
        reduction = original_len - short_len
        reduction_percent = int((reduction / original_len) * 100) if original_len > 0 else 0
        
        response_text = (
            f"✂️ **URL Cut Successfully!**\n\n"
            f"🔗 **Original:** `{text}`\n"
            f"📎 **Shortened:** `{short_url}`\n"
            f"📊 **Saved:** `{reduction}` characters ({reduction_percent}% shorter)\n\n"
            f"🔄 Send another URL to cut it down!"
        )
        
        # Add copy button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{short_url}")]
        ])
        
        await update.message.reply_text(
            response_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await processing_msg.edit_text(
            "❌ **Failed to shorten URL.**\n\n"
            "Please try again with a different URL or check if the URL is valid.",
            parse_mode="Markdown"
        )


# ============ CALLBACK QUERY HANDLERS ============

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline buttons"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "try_now":
        await query.message.reply_text(
            "✂️ **Send me any URL** and I'll cut it down for you!\n\n"
            "Example: `https://www.example.com/very/long/url`",
            parse_mode="Markdown"
        )
    elif query.data == "help":
        await help_command(query.message, context)
    elif query.data.startswith("copy_"):
        short_url = query.data.replace("copy_", "")
        await query.message.reply_text(
            f"📋 **Link copied!**\n\n"
            f"`{short_url}`\n\n"
            f"You can now paste this link anywhere.",
            parse_mode="Markdown"
        )


# ============ ERROR HANDLER ============

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")


# ============ MAIN ============

def main():
    """Main entry point"""
    logger.info(f"🚀 Starting {BOT_NAME}...")
    logger.info(f"📌 Version: {BOT_VERSION}")
    logger.info(f"🔧 Debug Mode: {DEBUG_MODE}")
    
    try:
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("about", about_command))
        
        # Add message handler for URLs
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Add callback query handler
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Start polling
        logger.info("✅ Bot is running and listening for messages...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise


if __name__ == "__main__":
    main()
