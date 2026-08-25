# Don't Remove Credit @AniZoneFlix, @AniZoneFlix
# Ask Doubt on telegram @AniZoneFlix
#
# Copyright (C) 2025 by AniZoneFlix@AniZoneFlix, < https://github.com/AniZoneFlix >.
#
# This file is part of < https://t.me/AniZoneFlix > project,
# and is released under the MIT License.
# Please see < https://t.me/AniZoneFlix/blob/master/LICENSE >
#
# All rights reserved.
#

import os
import random
from os import environ, getenv
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AniZoneFlix on Tg
TG_BOT_TOKEN = getenv("TG_BOT_TOKEN")
APP_ID = int(getenv("APP_ID", 0))
API_HASH = getenv("API_HASH")
#--------------------------------------------

CHANNEL_ID = int(getenv("CHANNEL_ID", 0))
OWNER = getenv("OWNER", "Alonekingstarback")
OWNER_ID = int(getenv("OWNER_ID", 0))
#--------------------------------------------
PORT = int(getenv("PORT", "8080"))
#--------------------------------------------
BOT_NAME = getenv("BOT_NAME", "AniZoneFlix_bot")
BOT_USERNAME = getenv("BOT_USERNAME", "AniZoneFlix_Bot")

DB_URI = getenv("DATABASE_URL")
DB_NAME = getenv("DATABASE_NAME", BOT_USERNAME)
#--------------------------------------------
FSUB_LINK_EXPIRY = int(getenv("FSUB_LINK_EXPIRY", "10"))  # 0 means no expiry
BAN_SUPPORT = getenv("BAN_SUPPORT", "https://t.me/AniZoneFlix")
TG_BOT_WORKERS = int(getenv("TG_BOT_WORKERS", "200"))
COMMAND_PREFIXES = ['/', '.', '|', '\\', '']
#--------------------------------------------
# Random Anime Banners (Neon / Dark Theme)
ANIME_BANNERS = [
    "https://telegra.ph/file/ec17880d61180d3312d6a.jpg", # Zoro
    "https://telegra.ph/file/e292b12890b8b4b9dcbd1.jpg", # Solo Leveling
    "https://telegra.ph/file/3e83c69804826b3cba066-16cffa90cd682570da.jpg", # Naruto
    "https://telegra.ph/file/ec17880d61180d3312d6a.jpg", # Add more
    "https://telegra.ph/file/e292b12890b8b4b9dcbd1.jpg"
]

START_PIC = random.choice(ANIME_BANNERS)
FORCE_PIC = random.choice(ANIME_BANNERS)
PICS = ANIME_BANNERS

#--------------------------------------------
# URL SHORTENER AUTHENTICATION GATE CONFIG
SHORTENER_URL = getenv("SHORTENER_URL", "arolinks.com")
SHORTENER_API_KEY = getenv("SHORTENER_API_KEY")
WEBSITE_URL = getenv("WEBSITE_URL", "https://filestore-1-6jyo.onrender.com")
CDN_URL = getenv("CDN_URL", WEBSITE_URL)

TUT_VID = getenv("TUT_VID", "https://t.me/anizoneflix")

RECAPTCHA_SITE_KEY = getenv("RECAPTCHA_SITE_KEY")
RECAPTCHA_SECRET_KEY = getenv("RECAPTCHA_SECRET_KEY")
TURNSTILE_SITE_KEY = getenv("TURNSTILE_SITE_KEY")
TURNSTILE_SECRET_KEY = getenv("TURNSTILE_SECRET_KEY")
#--------------------------------------------
SHORT_MSG = (
    "━━━━━━━━━━━━━━━━━━━\n"
    "💎 <b>Secure Link Ready</b>\n\n"
    "🛡️ Hello {mention}, your requested file is protected.\n"
    "Please complete the verification process to unlock access. 🚀\n\n"
    "🌟 <b>How to Unlock</b>\n"
    "<blockquote><code>1. Tap the secure link below. 🔗</code>\n"
    "<code>2. Complete the quick verification steps. 🛡️</code>\n"
    "<code>3. Retrieve your file instantly! ⚡</code></blockquote>\n"
    "━━━━━━━━━━━━━━━━━━━"
)

#--------------------------------------------
HELP_TXT = (
    "━━━━━━━━━━━━━━━━━━━\n"
    "✨ <b>Help Center</b>\n\n"
    "<blockquote>I am a high-performance secure file store bot.\n"
    "Simply send me any file, and I will securely save and generate links for you! 🛡️</blockquote>\n\n"
    "📜 <b>Available Commands</b>\n"
    "├ <code>/start</code> : Start or restart the bot 🔄\n"
    "├ <code>/batch</code> : Create range/batch links 📦\n"
    "├ <code>/auto_batch</code> : Group and batch files by quality 🎬\n"
    "├ <code>/genlink</code> : Generate a secure link or process in bulk 🔗\n"
    "├ <code>/save</code> : Backup and restore system data 📤\n"
    "├ <code>/panel</code> : Open the security control panel ⚙️\n"
    "└ <code>/help</code> : Seek system guidance ✨\n\n"
    "💎 <b>Powered by <code>https://t.me/AniZoneFlix</code></b>\n"
    "━━━━━━━━━━━━━━━━━━━"
)
ABOUT_TXT = (
    "━━━━━━━━━━━━━━━━━━━\n"
    "🛡️ <b>About Secure File Store</b>\n\n"
    "<blockquote>💎 This bot securely stores and delivers files at high speeds.\n"
    "Experience ultra-fast downloads with a clean, simple, and professional interface. ✨</blockquote>\n\n"
    "👥 <b>Community</b>: <code>https://t.me/AniZoneFlix</code>\n"
    "🛠 <b>Developer Contact</b>: <code>https://t.me/ALONEKINGSTARBACK</code>\n"
    "━━━━━━━━━━━━━━━━━━━"
)
#--------------------------------------------
START_MSG = getenv("START_MESSAGE", (
    "━━━━━━━━━━━━━━━━━━━\n"
    "⚡ <b>Welcome, {mention}!</b>\n\n"
    "<blockquote>💎 I am a powerful secure file storage bot.\n"
    "I can save and deliver your files securely with lightning-fast speeds! 🚀</blockquote>\n"
    "━━━━━━━━━━━━━━━━━━━"
))
FORCE_MSG = getenv("FORCE_SUB_MESSAGE", (
    "━━━━━━━━━━━━━━━━━━━\n"
    "🚫 <b>Access Denied</b>\n\n"
    "<blockquote>Hey {mention}, please join our official channels\n"
    "to unlock and access your requested files. 🔓</blockquote>\n"
    "━━━━━━━━━━━━━━━━━━━"
))

CMD_TXT = """━━━━━━━━━━━━━━━━━━━
⚙️ <b>Admin Control Panel</b>
━━━━━━━━━━━━━━━━━━━

🌟 <b>›› /auto_delete —</b> <code>Set delete timer</code> 🕒
🌟 <b>›› /dbroadcast —</b> <code>Broadcast media</code> 📢
🌟 <b>›› /ban —</b> <code>Ban a user</code> 🚫
🌟 <b>›› /unban —</b> <code>Unban a user</code> 🔓
🌟 <b>›› /addchnl —</b> <code>Add force subscription</code> 🔗
🌟 <b>›› /delchnl —</b> <code>Remove force subscription</code> ❌
🌟 <b>›› /listchnl —</b> <code>View all channels</code> 📋
🌟 <b>›› /fsub_mode —</b> <code>Toggle force subscription</code> ⚙️
🌟 <b>›› /addpremium —</b> <code>Add premium user</code> 👑
🌟 <b>›› /premium_users —</b> <code>Show premium users</code> ⭐
🌟 <b>›› /myplan —</b> <code>Your subscription plan</code> 📜
🌟 <b>›› /count —</b> <code>Today's statistics</code> 📊
🌟 <b>›› /access_limit —</b> <code>Set access credit limit</code> 🔢
🌟 <b>›› /validity —</b> <code>Set session validity duration</code> 🕒
🌟 <b>›› /info —</b> <code>User force sub status</code> 📊

💎 <b>Powered by <code>https://t.me/AniZoneFlix</code></b>
━━━━━━━━━━━━━━━━━━━"""
#--------------------------------------------
CUSTOM_CAPTION = getenv("CUSTOM_CAPTION", "<b>• By <code>https://t.me/AniZoneFlix</code></b>")  # set your Custom Caption here, Keep None for Disable Custom Caption
PROTECT_CONTENT = getenv('PROTECT_CONTENT', "False") == "True"  # set True if you want to prevent users from forwarding files from bot
#--------------------------------------------
# Set true if you want Disable your Channel Posts Share button
DISABLE_CHANNEL_BUTTON = getenv("DISABLE_CHANNEL_BUTTON", "False") == 'True'
#--------------------------------------------
BOT_STATS_TEXT = "📊 <b>System Uptime</b>\n\n<code>{uptime}</code>"
USER_REPLY_TEXT = "❌ <b>Access Denied</b>\n\nYou do not have permission to use this command. 🛡️"

#==========================(BUY PREMIUM)====================#

OWNER_TAG = getenv("OWNER_TAG", "ᴀɴɪᴢᴏɴᴇꜰʟɪx")
UPI_ID = getenv("UPI_ID", "AniZoneFlix@AniZoneFlix")
QR_PIC = random.choice(ANIME_BANNERS)
SCREENSHOT_URL = getenv("SCREENSHOT_URL", "t.me/AniZoneFlix")
#--------------------------------------------
# Time and its price
# 7 Days
PRICE1 = getenv("PRICE1", "29 rs")

# 1 Month
PRICE2 = getenv("PRICE2", "99 rs")

# 3 Months
PRICE3 = getenv("PRICE3", "249 rs")

# 6 Months
PRICE4 = getenv("PRICE4", "449 rs")

# 1 Year
PRICE5 = getenv("PRICE5", "799 rs")

#===================(END)========================#

# Default Proxies Config (Supports http://username:password@ip:port format)
PROXIES = getenv("PROXIES", "").split(",") if getenv("PROXIES") else []

LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
