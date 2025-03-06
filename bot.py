import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackContext, Application
from datetime import datetime
from aiohttp import web
import asyncio

# Bot configuration from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')
ALLOWED_USER_IDS = [int(id.strip()) for id in os.environ.get('ALLOWED_USER_IDS', '').split(',') if id.strip()]
DEVICES_JSON_URL = os.environ.get('DEVICES_JSON_URL', 'https://raw.githubusercontent.com/RisingOS-Revived-devices/portal/refs/heads/main/devices.json')

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
        user_id = update.effective_user.id
        print(f"Received command from user ID: {user_id}")
        print(f"Allowed IDs (from env): {ALLOWED_USER_IDS}")
        print(f"Type of user_id: {type(user_id)}")
        print(f"Type of allowed IDs: {[type(id) for id in ALLOWED_USER_IDS]}")
        
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
        
        try:
            response = requests.get(DEVICES_JSON_URL)
            response.raise_for_status()
            devices = response.json()
            
            device_data = None
            for device in devices:
                if device['codename'].lower() == codename:
                    device_data = device
                    break
            
            if device_data:
                await self.send_announcement(device_data)
                await update.message.reply_text(f"✅ Posted announcement for {device_data['codename']}")
            else:
                await update.message.reply_text(f"❌ Device '{codename}' not found in devices list")
                
        except requests.RequestException as e:
            await update.message.reply_text(f"❌ Error fetching devices data: {str(e)}")
        except json.JSONDecodeError:
            await update.message.reply_text("❌ Error parsing devices data!")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def send_announcement(self, device_data):
        """Send formatted announcement to Telegram channel"""
        try:
            # Format file size
            size_gb = device_data['filesize'] / (1024 * 1024 * 1024)
            
            # Format date
            build_date = datetime.fromtimestamp(device_data['timestamp']).strftime("%d %B %Y")
            
            # Create inline keyboard with buttons
            keyboard = [
                [
                    InlineKeyboardButton("📱 Official Website", url="https://risingosrevived.tech/"),
                    InlineKeyboardButton("⬇️ Download Page", url=f"https://risingosrevived.tech/downloads.html?codename={device_data['codename']}")
                ],
                [
                    InlineKeyboardButton("💬 Support Group", url=f"https://t.me/RisingOS{device_data['codename']}"),
                    InlineKeyboardButton("📝 Changelog", url=device_data['device_changelog'])
                ]
            ]
            
            if device_data['paypal']:
                keyboard.append([InlineKeyboardButton("☕️ Support Maintainer", url=device_data['paypal'])])

            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = f"""
🚀 *New RisingOS-Revived Update Available!*

📱 *Device:* {device_data['oem']} {device_data['device']} ({device_data['codename']})
👨‍💻 *Maintainer:* {device_data['maintainer']}
📦 *Version:* {device_data['version']}
🔧 *Build Type:* {device_data['buildtype']}
📅 *Build Date:* {build_date}

#ROR #{device_data['codename']} #{device_data['version']} #fifteen
"""
            
            await self.application.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo="https://raw.githubusercontent.com/RisingOS-Revived-devices/portal/main/banner.png",
                caption=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            raise Exception(f"Failed to send announcement: {str(e)}")

    async def start(self):
        """Start both the webhook server and the bot"""
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
        await self.application.run_polling(allowed_updates=Update.ALL_TYPES)

async def main():
    bot = RisingOSBot()
    try:
        await bot.start()
    except Exception as e:
        print(f"Error: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(main()) 