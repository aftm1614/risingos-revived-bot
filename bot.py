import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackContext, Application
from datetime import datetime
from aiohttp import web
import asyncio

# Debug print environment variables
print("Environment Variables:")
print(f"BOT_TOKEN exists: {'BOT_TOKEN' in os.environ}")
print(f"CHANNEL_ID exists: {'CHANNEL_ID' in os.environ}")
print(f"ALLOWED_USER_IDS exists: {'ALLOWED_USER_IDS' in os.environ}")

# Bot configuration from environment variables with fallbacks
BOT_TOKEN = os.environ.get('BOT_TOKEN', '6760432925:AAF1QtMjdIHQKIPWGM_1PFQBqN4htFOkWXI')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '-1002226931868')
ALLOWED_USER_IDS = [int(id.strip()) for id in os.environ.get('ALLOWED_USER_IDS', '7013293652').split(',') if id.strip()]
DEVICES_JSON_URL = os.environ.get('DEVICES_JSON_URL', 'https://raw.githubusercontent.com/RisingOS-Revived-devices/portal/refs/heads/main/devices.json')

# Print configured values (excluding BOT_TOKEN for security)
print("\nConfigured Values:")
print(f"CHANNEL_ID: {CHANNEL_ID}")
print(f"ALLOWED_USER_IDS: {ALLOWED_USER_IDS}")
print(f"DEVICES_JSON_URL: {DEVICES_JSON_URL}")

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is required")
if not ALLOWED_USER_IDS:
    raise ValueError("ALLOWED_USER_IDS environment variable is required")

async def handle_health_check(request):
    """Handle health check requests"""
    return web.Response(text='Bot is running!')

class RisingOSBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.application.add_handler(CommandHandler('post', self.post_command))
        self.application.add_handler(CommandHandler('id', self.id_command))
        
        # Setup web app for health checks
        self.web_app = web.Application()
        self.web_app.router.add_get('/', handle_health_check)

    async def id_command(self, update: Update, context: CallbackContext):
        """Handle /id command"""
        user_id = update.effective_user.id
        env_value = os.environ.get('ALLOWED_USER_IDS', '')
        await update.message.reply_text(
            f"Your Telegram ID: `{user_id}`\n"
            f"Current allowed IDs: `{ALLOWED_USER_IDS}`\n"
            f"Raw env value: `{env_value}`\n"
            f"Type of your ID: `{type(user_id)}`\n"
            f"Type of allowed IDs: `{[type(id) for id in ALLOWED_USER_IDS]}`",
            parse_mode=ParseMode.MARKDOWN
        )

    async def post_command(self, update: Update, context: CallbackContext):
        """Handle /post command"""
        try:
            user_id = update.effective_user.id
            print(f"Received /post command from user ID: {user_id}")
            print(f"Allowed IDs (from env): {ALLOWED_USER_IDS}")
            
            # Check if user is authorized
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
            print(f"Fetching data for device: {codename}")
            
            # Fetch devices data from URL
            print(f"Fetching from URL: {DEVICES_JSON_URL}")
            response = requests.get(DEVICES_JSON_URL)
            response.raise_for_status()
            devices = response.json()
            print(f"Found {len(devices)} devices in total")
            
            # Find device with matching codename
            device_data = None
            for device in devices:
                if device['codename'].lower() == codename:
                    device_data = device
                    print(f"Found matching device: {device['codename']}")
                    break
            
            if device_data:
                print("Sending announcement...")
                await self.send_announcement(device_data)
                await update.message.reply_text(f"✅ Posted announcement for {device_data['codename']}")
            else:
                await update.message.reply_text(f"❌ Device '{codename}' not found in devices list")
                
        except requests.RequestException as e:
            print(f"Request error: {e}")
            await update.message.reply_text(f"❌ Error fetching devices data: {str(e)}")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            await update.message.reply_text("❌ Error parsing devices data!")
        except Exception as e:
            print(f"Unexpected error in post_command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def send_announcement(self, device_data):
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
            
            # Create base keyboard with website and download buttons
            keyboard = [
                [
                    InlineKeyboardButton("📱 Official Website", url="https://risingosrevived.tech/"),
                    InlineKeyboardButton("⬇️ Download Page", url=f"https://risingosrevived.tech/downloads.html?codename={device_data['codename']}")
                ]
            ]
            
            # Add support group and changelog buttons if available
            second_row = []
            if device_data.get('telegram'):
                second_row.append(InlineKeyboardButton("💬 Support Group", url=device_data['telegram']))
            else:
                second_row.append(InlineKeyboardButton("💬 Support Group", url=f"https://t.me/RisingOS{device_data['codename']}"))
                
            if device_data.get('device_changelog'):
                second_row.append(InlineKeyboardButton("📝 Changelog", url=device_data['device_changelog']))
            
            if second_row:
                keyboard.append(second_row)
            
            # Add PayPal button if available
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
            
            print("Sending message to channel...")
            print(f"Channel ID: {CHANNEL_ID}")
            
            # Send photo with caption and buttons
            await self.application.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo="https://raw.githubusercontent.com/RisingOS-Revived-devices/portal/main/banner.png",
                caption=message,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup
            )
            print("Message sent successfully")
            
        except Exception as e:
            print(f"Error in send_announcement: {e}")
            raise Exception(f"Failed to send announcement: {str(e)}")

    async def start(self):
        """Start both the webhook server and the bot"""
        try:
            # Start the webhook server
            runner = web.AppRunner(self.web_app)
            await runner.setup()
            port = int(os.environ.get('PORT', 8080))
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            print(f"🌐 Webhook running on port {port}")

            # Start the bot
            print("🤖 Bot is running...")
            await self.application.initialize()
            await self.application.start()
            
            # Start polling and keep the bot running
            await self.application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            print(f"Startup error: {e}")
            # Ensure proper cleanup
            await self.application.stop()
            await self.application.shutdown()
            raise e

async def main():
    bot = RisingOSBot()
    try:
        await bot.start()
    except Exception as e:
        print(f"Fatal error: {e}")
        raise e

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}") 