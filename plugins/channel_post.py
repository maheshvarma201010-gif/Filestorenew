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

import asyncio
import urllib.parse
import time
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup
from pyrogram.errors import FloodWait

from collections import defaultdict
from config import CHANNEL_ID, OWNER_ID, DISABLE_CHANNEL_BUTTON, WEBSITE_URL
from helper_func import encode, admin, is_video, get_filename, generate_stream_hash, InlineKeyboardButton, random_button_style
from database.database import db

# In-memory fail-safe lock registry to safely handle task serialization
admin_locks = defaultdict(asyncio.Lock)

def get_admin_lock(client, admin_id):
    try:
        return db.get_bot_admin_lock(client.username, admin_id)
    except Exception:
        return admin_locks[admin_id]

# Highly optimized, safe Pyrogram API execution wrapper with dynamic FloodWait control
async def safe_call(func, *args, **kwargs):
    last_err = None
    for i in range(5):
        try:
            return await func(*args, **kwargs)
        except FloodWait as e:
            sleep_time = getattr(e, "value", getattr(e, "x", 5))
            await asyncio.sleep(sleep_time + 0.5)
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if any(k in err_str for k in ["forbidden", "private", "not an admin", "admin", "chat_write_forbidden"]):
                raise e
            await asyncio.sleep(0.5)
    if last_err:
        raise last_err
    return None

async def process_single_post(client: Client, message: Message, reply_text, target_db):
    # Copy message to target database channel
    post_message = await safe_call(message.copy, chat_id=target_db, disable_notification=True)
    if not post_message:
        if reply_text:
            await safe_call(reply_text.edit_text, "❌ <b>sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ ᴡʜɪʟᴇ sᴛᴏʀɪɴɢ ᴛʜᴇ ꜰɪʟᴇ!</b>")
        return

    converted_id = post_message.id * abs(target_db)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    share_button = [InlineKeyboardButton("🔁 sʜᴀʀᴇ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}', style="primary")]

    # Preserve existing buttons
    buttons = []
    if message.reply_markup and message.reply_markup.inline_keyboard:
        buttons.extend(list(message.reply_markup.inline_keyboard))

    # Add Watch/Download buttons if it's a video
    settings = await db.get_settings()
    if is_video(post_message):
        stream_hash = generate_stream_hash(post_message.id)
        filename = get_filename(post_message)
        encoded_name = urllib.parse.quote(filename)
        web_url = settings.get('website_url', WEBSITE_URL).rstrip('/')

        watch_url_raw = f"{web_url}/watch/{client.username}/{post_message.id}/{encoded_name}?hash={stream_hash}"
        short_id = await db.create_local_redirect(watch_url_raw, expire=604800) # 7 days

        if settings.get('streaming_active', True):
            stream_url = f"{web_url}/v/{short_id}"
            buttons.append([InlineKeyboardButton("🚀 ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ", url=stream_url, style="success")])

        if settings.get('download_btn_active', True):
            cdn_url = settings.get('cdn_url', web_url).rstrip('/')
            dl_url = f"{cdn_url}/download?path={short_id}"
            buttons.append([InlineKeyboardButton("📥 ᴅᴏᴡɴʟᴏᴀᴅ ꜰɪʟᴇ", url=dl_url, style="success")])

    buttons.append(share_button)
    reply_markup = InlineKeyboardMarkup(buttons)

    filename = "Unknown"
    if post_message.document: filename = post_message.document.file_name
    elif post_message.video: filename = post_message.video.file_name or "Video"
    elif post_message.audio: filename = post_message.audio.file_name or "Audio"

    file_caption = post_message.caption or "No Caption"

    text = (
        "━━━━━━━━━━━━━━━━━━━\n"
        "✨ <b>˹ ꜰɪʟᴇ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴛᴏʀᴇᴅ ˼</b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>ꜰɪʟᴇɴᴀᴍᴇ:</b> <code>{filename}</code>\n"
        f"📝 <b>ᴄᴀᴘᴛɪᴏɴ:</b> <code>{file_caption}</code>\n\n"
        f"🔗 <b>ʏᴏᴜʀ ʟɪɴᴋ:</b> <code>{link}</code>\n\n"
        "<blockquote>🛡️ ᴛʜɪs ꜰɪʟᴇ ɪs sᴀᴠᴇᴅ ɪɴ ʏᴏᴜʀ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ʀᴇᴀᴅʏ ᴛᴏ sʜᴀʀᴇ!</blockquote>\n"
        "━━━━━━━━━━━━━━━━━━━"
    )

    if reply_text:
        await safe_call(reply_text.edit, text, reply_markup=reply_markup)

    if not DISABLE_CHANNEL_BUTTON:
        try:
            await safe_call(post_message.edit_reply_markup, reply_markup)
        except Exception as e:
            print(f"Error editing post reply markup: {e}")

@Client.on_message(filters.private & admin & (filters.document | filters.video | filters.audio | filters.photo | filters.animation | filters.voice | filters.video_note | filters.sticker) & ~filters.command(['start', 'help', 'ping', 'commands','users','broadcast','batch', 'custom_batch', 'genlink', 'panel', 'shortner', 'shortener', 'stats', 'dlt_time', 'check_dlt_time', 'auto_delete', 'check_auto_delete', 'autodelete', 'checkautodelete', 'dbroadcast', 'ban', 'unban', 'banlist', 'addchnl', 'delchnl', 'listchnl', 'fsub_mode', 'pbroadcast', 'add_admin', 'deladmin', 'admins', 'addpremium', 'premium_users', 'remove_premium', 'myplan', 'count', 'delreq']))
async def channel_post(client: Client, message: Message):
    if message.from_user and message.from_user.id in db.busy_admins:
        return

    admin_id = message.from_user.id if message.from_user else OWNER_ID
    lock = get_admin_lock(client, admin_id)

    # STRICT SEQUENTIAL SERIALIZATION (Inside the lock with pacing)
    # Processing and copying of files happens strictly one by one, one after the other, slowly and neatly.
    async with lock:
        reply_text = None
        try:
            reply_text = await safe_call(message.reply_text, "⚡️ <b>˹ ᴘʀᴏᴄᴇssɪɴɢ... ˼</b>", quote=True)
        except Exception as e:
            print(f"Error sending processing reply: {e}")

        try:
            # Safely resolve target database channel with fallbacks
            db_channels = await db.get_all_db_channels(client.username)
            if db_channels:
                target_db = db_channels[0]
            elif hasattr(client, "db_channel_id") and client.db_channel_id:
                target_db = client.db_channel_id
            elif hasattr(client, "db_channel") and client.db_channel:
                target_db = client.db_channel.id
            else:
                target_db = CHANNEL_ID

            # Execute with a strict safety timeout of 15 seconds so files can never get stuck (stocking)
            await asyncio.wait_for(process_single_post(client, message, reply_text, target_db), timeout=15.0)

            # Introduce a strict 1.5-second pacing delay to guarantee slow and neat sequential generation
            await asyncio.sleep(1.5)

        except asyncio.TimeoutError:
            print("Link generation timed out to prevent lock blockage.")
            if reply_text:
                try:
                    await safe_call(reply_text.edit_text, "⚠️ <b>ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛɪᴏɴ ᴛɪᴍᴇᴅ ᴏᴜᴛ. ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀɢᴀɪɴ.</b>")
                except:
                    pass
        except Exception as e:
            print(f"Unhandled error in sequential post processing: {e}")
            if reply_text:
                try:
                    err_msg = str(e)
                    custom_err = "❌ <b>sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ ᴡʜɪʟᴇ sᴛᴏʀɪɴɢ ᴛʜᴇ ꜰɪʟᴇ!</b>\n\n"
                    if "forbidden" in err_msg.lower() or "chat_write_forbidden" in err_msg.lower():
                        custom_err += "⚠️ <i>Make sure the Bot is Admin in your DB Channel with post/write permissions!</i>"
                    elif "private" in err_msg.lower() or "chat_private" in err_msg.lower():
                        custom_err += "⚠️ <i>Make sure the DB Channel exists and the Bot has access to it!</i>"
                    else:
                        custom_err += f"<blockquote><code>{err_msg}</code></blockquote>"
                    await safe_call(reply_text.edit_text, custom_err)
                except:
                    pass

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
