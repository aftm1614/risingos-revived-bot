import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackContext, Application
from datetime import datetime
from telegram.error import Conflict, NetworkError

# Debug print environment variables
print("Environment Variables:")
print(f"BOT_TOKEN exists: {'BOT_TOKEN' in os.environ}")
print(f"CHANNEL_ID exists: {'CHANNEL_ID' in os.environ}")
print(f"ALLOWED_USER_IDS exists: {'ALLOWED_USER_IDS' in os.environ}")

# Bot configuration from environment variables with no default values
BOT_TOKEN = os.environ['BOT_TOKEN']  # Railway variable required
CHANNEL_ID = os.environ['CHANNEL_ID']  # Railway variable required
ALLOWED_USER_IDS = [int(id.strip()) for id in os.environ['ALLOWED_USER_IDS'].split(',')]  # Railway variable required
DEVICES_JSON_URL = os.environ.get('DEVICES_JSON_URL', 'https://raw.githubusercontent.com/RisingOS-Revived-devices/portal/refs/heads/main/devices.json')

# Print configured values (excluding BOT_TOKEN for security)
print("\nConfigured Values:")
print(f"CHANNEL_ID: {CHANNEL_ID}")
print(f"ALLOWED_USER_IDS: {ALLOWED_USER_IDS}")
print(f"DEVICES_JSON_URL: {DEVICES_JSON_URL}")

# Validate configuration
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is required")
if not ALLOWED_USER_IDS:
    raise ValueError("ALLOWED_USER_IDS environment variable is required")

async def post_command(update: Update, context: CallbackContext):
    """Handle /post command"""
    try:
        user_id = update.effective_user.id
        print(f"Received /post command from user ID: {user_id}")
        
        if user_id not in ALLOWED_USER_IDS:
            await update.message.reply_text(
                f"❌ You are not authorized to use this bot.\n"
                f"Your ID: {user_id}\n"
                f"Allowed IDs: {ALLOWED_USER_IDS}"
            )
            return

        if not context.args:
            await update.message.reply_text("❌ Please provide a device codename.\nUsage: /post <codename>")
            return

        codename = context.args[0].lower()
        print(f"Processing request for device: {codename}")
        
        response = requests.get(DEVICES_JSON_URL)
        response.raise_for_status()
        devices = response.json()
        
        device_data = None
        for device in devices:
            if device['codename'].lower() == codename:
                device_data = device
                break
        
        if device_data:
            await send_announcement(context.application.bot, device_data)
            await update.message.reply_text(f"✅ Posted announcement for {device_data['codename']}")
        else:
            await update.message.reply_text(f"❌ Device '{codename}' not found in devices list")
            
    except Exception as e:
        print(f"Error in post_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def id_command(update: Update, context: CallbackContext):
    """Handle /id command"""
    user_id = update.effective_user.id
    await update.message.reply_text(f"Your Telegram ID: {user_id}")

async def send_announcement(bot, device_data):
    """Send formatted announcement to Telegram channel"""
    try:
        # Format date
        build_date = datetime.fromtimestamp(device_data['timestamp']).strftime("%d %B %Y")
        
        def escape_markdown(text):
            """Helper function to escape special characters"""
            special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in special_chars:
                text = str(text).replace(char, f"\\{char}")
            return text
        
        # Escape all text fields
        device_name = escape_markdown(device_data['device'])
        oem_name = escape_markdown(device_data['oem'])
        maintainer_name = escape_markdown(device_data['maintainer'])
        version = escape_markdown(device_data['version'])
        buildtype = escape_markdown(device_data['buildtype'])
        codename = escape_markdown(device_data['codename'])
        build_date = escape_markdown(build_date)
        
        # Create keyboard buttons
        keyboard = [
            [
                InlineKeyboardButton("📱 Official Website", url="https://risingosrevived.tech/"),
                InlineKeyboardButton("⬇️ Download Page", url=f"https://risingosrevived.tech/downloads.html?codename={device_data['codename']}")
            ]
        ]
        
        # Add support group and changelog buttons
        second_row = []
        if device_data.get('telegram'):
            second_row.append(InlineKeyboardButton("💬 Support Group", url=device_data['telegram']))
        else:
            second_row.append(InlineKeyboardButton("💬 Support Group", url=f"https://t.me/RisingOS{device_data['codename']}"))
            
        if device_data.get('device_changelog'):
            second_row.append(InlineKeyboardButton("📝 Changelog", url=device_data['device_changelog']))
        
        if second_row:
            keyboard.append(second_row)
        
        if device_data.get('paypal'):
            keyboard.append([InlineKeyboardButton("☕️ Support Maintainer", url=device_data['paypal'])])

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "🚀 *New RisingOS\\-Revived Update Available\\!*\n\n"
            f"📱 *Device:* {oem_name} {device_name} \\({codename}\\)\n"
            f"👨‍💻 *Maintainer:* {maintainer_name}\n"
            f"📦 *Version:* {version}\n"
            f"🔧 *Build Type:* {buildtype}\n"
            f"📅 *Build Date:* {build_date}\n\n"
            f"\\#ROR \\#{codename} \\#{version} \\#fifteen"
        )
        
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo="https://raw.githubusercontent.com/RisingOS-Revived-devices/portal/main/banner.png",
            caption=message,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        print(f"Error in send_announcement: {e}")
        raise Exception(f"Failed to send announcement: {str(e)}")

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Handle errors in the dispatcher."""
    print(f"Error occurred: {context.error}")
    if isinstance(context.error, Conflict):
        print("Conflict error: Another instance of the bot is running")
    elif isinstance(context.error, NetworkError):
        print("Network error occurred")
    else:
        print(f"Unexpected error: {context.error}")

def main():
    """Start the bot"""
    try:
        # Create application with specific defaults
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler('post', post_command))
        application.add_handler(CommandHandler('id', id_command))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Start polling with specific settings
        print("🤖 Starting bot...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
            read_timeout=30,
            write_timeout=30,
            pool_timeout=30,
            connect_timeout=30
        )
        
    except Exception as e:
        print(f"Fatal error: {e}")
        raise e

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}") 