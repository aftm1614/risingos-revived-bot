import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackContext, Application
from datetime import datetime

# Rest of your code remains the same

# Bot configuration
BOT_TOKEN = '6760432925:AAF1QtMjdIHQKIPWGM_1PFQBqN4htFOkWXI'
CHANNEL_ID = '-1002226931868'
ALLOWED_USER_IDS = [7013293652]  # Add Telegram user IDs who can use the bot
DEVICES_JSON_URL = 'https://raw.githubusercontent.com/RisingOS-Revived-devices/portal/refs/heads/main/devices.json'

class RisingOSBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Add command handler
        self.application.add_handler(CommandHandler('post', self.post_command))

    async def post_command(self, update: Update, context: CallbackContext):
        """Handle /post command"""
        # Check if user is authorized
        if update.effective_user.id not in ALLOWED_USER_IDS:
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return

        # Check if device codename was provided
        if not context.args:
            await update.message.reply_text("❌ Please provide a device codename.\nUsage: /post <codename>")
            return

        codename = context.args[0].lower()
        
        try:
            # Fetch devices data from URL
            response = requests.get(DEVICES_JSON_URL)
            response.raise_for_status()
            devices = response.json()
            
            # Find device with matching codename
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
            
            # Send single post with banner and message
            message = f"""
🚀 *New RisingOS-Revived Update Available!*

📱 *Device:* {device_data['oem']} {device_data['device']} ({device_data['codename']})
👨‍💻 *Maintainer:* {device_data['maintainer']}
📦 *Version:* {device_data['version']}
🔧 *Build Type:* {device_data['buildtype']}
📅 *Build Date:* {build_date}

#ROR #{device_data['codename']} #{device_data['version']} #fifteen
"""
            
            # Send photo with caption and buttons
            await self.application.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo="https://raw.githubusercontent.com/RisingOS-Revived-devices/portal/main/banner.png",
                caption=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            raise Exception(f"Failed to send announcement: {str(e)}")

    def run(self):
        """Run the bot"""
        print("🤖 Bot is running...")
        self.application.run_polling()

def main():
    bot = RisingOSBot()
    bot.run()

if __name__ == "__main__":
    main()