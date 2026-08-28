#(©)AniZoneFlix
#ᴀɴɪᴢᴏɴᴇꜰʟɪx on ᴛɢ #Dont remove this line

import base64
import re
import asyncio
import time
import aiohttp
import json
import urllib.parse
import hashlib
import random

try:
    from pyrogram import filters
    from pyrogram.enums import ChatMemberStatus
    from pyrogram.types import Message, InlineKeyboardMarkup as PyrogramInlineKeyboardMarkup, InlineKeyboardButton as PyrogramInlineKeyboardButton
except ImportError:
    from pyrofork import filters
    from pyrofork.enums import ChatMemberStatus
    from pyrofork.types import Message, InlineKeyboardMarkup as PyrogramInlineKeyboardMarkup, InlineKeyboardButton as PyrogramInlineKeyboardButton

SUPPORTED_STYLES = [
    "primary",
    "success",
    "danger"
]

def random_button_style():
    return random.choice(SUPPORTED_STYLES)

class ColorInlineKeyboardButton(PyrogramInlineKeyboardButton):
    def __init__(self, text: str, *args, **kwargs):
        style = kwargs.pop("style", None)
        icon_custom_emoji_id = kwargs.pop("icon_custom_emoji_id", None)
        api_kwargs = kwargs.pop("api_kwargs", None)

        if api_kwargs and isinstance(api_kwargs, dict):
            if "style" in api_kwargs:
                style = style or api_kwargs.get("style")
            if "icon_custom_emoji_id" in api_kwargs:
                icon_custom_emoji_id = icon_custom_emoji_id or api_kwargs.get("icon_custom_emoji_id")

        if style in ["bg_success", "bg_danger", "bg_primary"]:
            if style == "bg_success":
                style_str = "success"
            elif style == "bg_danger":
                style_str = "danger"
            else:
                style_str = "primary"
        elif isinstance(style, str) and style:
            style_lower = style.lower()
            if style_lower in ["primary", "success", "danger", "default"]:
                style_str = style_lower
            else:
                style_str = "primary"
        elif style is not None:
            style_str = str(getattr(style, "value", style)).lower()
        else:
            style_str = None

        self.style = style_str
        self.icon_custom_emoji_id = icon_custom_emoji_id

        extra_kwargs = {}
        if style_str is not None:
            extra_kwargs["style"] = style_str
        if icon_custom_emoji_id is not None:
            extra_kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id

        if extra_kwargs:
            try:
                super().__init__(text, *args, **{**kwargs, **extra_kwargs})
                return
            except TypeError:
                pass
            except Exception:
                pass

        super().__init__(text, *args, **kwargs)

ColoredInlineKeyboardButton = ColorInlineKeyboardButton
InlineKeyboardButton = ColorInlineKeyboardButton
InlineKeyboardMarkup = PyrogramInlineKeyboardMarkup

import pyrogram.types
pyrogram.types.InlineKeyboardButton = ColorInlineKeyboardButton
pyrogram.types.InlineKeyboardMarkup = PyrogramInlineKeyboardMarkup
from config import *
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait
from database.database import *
from database.db_premium import is_premium_user



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

async def get_banners(client=None):
    # Forced centralization: Clones use main bot's configuration
    settings = await db.get_settings()
    banners = settings.get('anime_banners', [])
    videos = settings.get('video_banners', [])

    all_banners = []
    if isinstance(banners, list): all_banners.extend(banners)
    if isinstance(videos, list): all_banners.extend(videos)

    if not all_banners:
        from config import ANIME_BANNERS
        all_banners.extend(list(ANIME_BANNERS))

    return all_banners

async def send_media(client, chat_id, photo, caption, reply_markup, message_effect_id=None):
    """Helper to send photo or video based on URL extension. Fallbacks to text if photo is empty."""
    if not photo:
        return await client.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, message_effect_id=message_effect_id)

    is_video = str(photo).lower().split('?')[0].endswith(('.mp4', '.mkv', '.webm'))
    try:
        if is_video:
            return await client.send_video(
                chat_id=chat_id,
                video=photo,
                caption=caption,
                reply_markup=reply_markup
            )
        else:
            return await client.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"Error in send_media: {e}")
        return await client.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, message_effect_id=message_effect_id)

#used for cheking if a user is admin ~Owner also treated as admin level
async def check_admin(filter, client, update):
    try:
        if not update or not update.chat:
            return False

        # If it's a channel post, only administrators can post, so it is automatically authorized as admin
        if update.chat.type.name == "CHANNEL":
            return True

        # If it's a private chat
        if update.chat.type.name == "PRIVATE":
            if not update.from_user:
                return False
            user_id = update.from_user.id
            return any([user_id == OWNER_ID, await db.admin_exist(user_id)])

        # If it's a group or supergroup
        else:
            # Check if the bot itself is an admin in this chat (so we can delete commands)
            try:
                bot_member = await client.get_chat_member(update.chat.id, "self")
                if bot_member.status.name not in ["ADMINISTRATOR", "OWNER"]:
                    return False
            except Exception:
                return False

            # Check if the sender is an anonymous admin / sender chat
            if update.sender_chat and update.sender_chat.id == update.chat.id:
                return True

            if update.from_user:
                try:
                    user_member = await client.get_chat_member(update.chat.id, update.from_user.id)
                    return user_member.status.name in ["ADMINISTRATOR", "OWNER"]
                except Exception:
                    # Fallback to checking if they are a global bot admin/owner
                    user_id = update.from_user.id
                    return any([user_id == OWNER_ID, await db.admin_exist(user_id)])
            return False
    except Exception as e:
        print(f"! Exception in check_admin: {e}")
        return False


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

# Global session for performance
aio_session = None

async def get_session():
    global aio_session
    if aio_session is None or aio_session.closed:
        aio_session = aiohttp.ClientSession()
    return aio_session

# Create a global dictionary to store chat data
chat_data_cache = {}
chat_username_cache = {}

# Global Force Subscribe cache
# Key: (user_id, bot_username) -> Value: expiry_time (float)
FSUB_CACHE = {}

async def check_user_access(client, user_id):
    """
    Mandatory 6-Step Content Delivery Security Flow (Optimized with Concurrency)
    """
    bot_username = getattr(client, "username", "Bot").lower()
    now_time = time.time()
    if FSUB_CACHE.get((user_id, bot_username), 0) > now_time:
        # Cache hit! User has successfully subscribed within the last 5 minutes.
        return "granted"

    # STEP 1: Check banned status
    if await db.is_user_banned(user_id):
        return "banned"

    # Admin/Owner/Premium bypass for remaining checks
    if user_id == OWNER_ID: return "granted"

    # Check premium and admin status concurrently
    res = await asyncio.gather(is_premium_user(user_id), db.admin_exist(user_id))
    is_premium, is_admin = res[0], res[1]

    if is_premium: return "granted"

    settings = await db.get_settings()
    if is_admin and not settings.get('shorten_admins', True):
        return "granted"

    # CLONE SPECIFIC FSUB DETECTION
    is_clone = getattr(client, "name", "Bot") != "Bot"
    clone_data = None
    if is_clone:
        clone_data = await db.get_clone(client.username)

    if clone_data and clone_data.get('fsub_channels'):
        channel_ids = [int(c) for c in clone_data['fsub_channels']]
    else:
        channel_ids = await db.show_channels()

    # STEP 2 & 3: Check Force Subscribe (Channels/Groups/Bots) CONCURRENTLY
    fsub_bots = await db.get_fsub_bots()

    tasks = []
    for cid in channel_ids: tasks.append(is_sub(client, user_id, cid))
    for bot in fsub_bots: tasks.append(is_bot_started(user_id, bot['token']))

    if tasks:
        results = await asyncio.gather(*tasks)

        # Mapping results back
        num_channels = len(channel_ids)
        for i in range(num_channels):
            if not results[i]: return "fsub"

        for j in range(len(fsub_bots)):
            if not results[num_channels + j]: return "bot"

    # Successfully subscribed! Update the cache
    FSUB_CACHE[(user_id, bot_username)] = now_time + 300 # Cache for 5 minutes

    # STEP 4: Check permissions
    if not settings.get('core_features', True):
        return "maintenance"

    # STEP 5: Validate request integrity
    if not await db.present_user(user_id):
        await db.add_user(user_id)

    # STEP 6: Access Granted
    return "granted"

async def is_subscribed(client, user_id):
    # Legacy support
    return await check_user_access(client, user_id) == "granted"

async def get_sub_status(client, user_id):
    is_clone = getattr(client, "name", "Bot") != "Bot"
    clone_data = None
    if is_clone:
        clone_data = await db.get_clone(client.username)

    if clone_data and clone_data.get('fsub_channels'):
        channel_ids = [int(c) for c in clone_data['fsub_channels']]
    else:
        channel_ids = await db.show_channels()

    async def fetch_one(cid):
        try:
            if cid in chat_data_cache: chat = chat_data_cache[cid]
            else:
                chat = await client.get_chat(cid)
                chat_data_cache[cid] = chat

            is_joined = await is_sub(client, user_id, cid)
            link = f"https://t.me/{chat.username}" if chat.username else ""

            if not link and not is_joined:
                mode = await db.get_channel_mode(cid)
                invite = await client.create_chat_invite_link(chat_id=cid, creates_join_request=(mode == "on"))
                link = invite.invite_link

            return {"name": chat.title, "link": link, "is_joined": is_joined}
        except Exception as e:
            print(f"Error sub status {cid}: {e}")
            return None

    results = await asyncio.gather(*[fetch_one(cid) for cid in channel_ids])
    return [r for r in results if r]


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

_FSUB_SUB_CACHE = {}
_FSUB_BOT_CACHE = {}

async def is_bot_started(user_id, bot_token):
    """
    Check if a user has started a required bot using its token.
    """
    now = time.time()
    cache_key = (user_id, bot_token)
    if cache_key in _FSUB_BOT_CACHE:
        val, expiry = _FSUB_BOT_CACHE[cache_key]
        if now < expiry:
            return val

    try:
        session = await get_session()
        # getChat only returns 'ok: true' if the user has started the bot.
        api_url = f"https://api.telegram.org/bot{bot_token}/getChat?chat_id={user_id}"
        async with session.get(api_url, timeout=5) as resp:
            data = await resp.json()
            res = data.get("ok", False)
            ttl = 300 if res else 5
            _FSUB_BOT_CACHE[cache_key] = (res, now + ttl)
            return res
    except Exception as e:
        print(f"Error in is_bot_started: {e}")
        return False

async def get_fsub_buttons(client, user_id, payload=None):
    # Concurrent status fetch
    res = await asyncio.gather(get_sub_status(client, user_id), db.get_fsub_bots())
    status_list, fsub_bots = res[0], res[1]

    buttons = []

    # 1. Add FSUB Channels/Groups buttons
    for status in status_list:
        if not status['is_joined']:
            buttons.append([InlineKeyboardButton(text=f"📢 ᴊᴏɪɴ {status['name']}", url=status['link'], style=random_button_style())])

    # 2. Add Required Bots buttons (Check started status concurrently)
    if fsub_bots:
        bot_tasks = [is_bot_started(user_id, bot['token']) for bot in fsub_bots]
        started_results = await asyncio.gather(*bot_tasks)

        for i, started in enumerate(started_results):
            if not started:
                bot = fsub_bots[i]
                username = bot.get('username')
                name = bot.get('name', 'Required Bot')
                if username:
                    buttons.append([InlineKeyboardButton(text=f"🤖 ᴏᴘᴇɴ {name}", url=f"https://t.me/{username}?start=fsub", style=random_button_style())])

    # 3. Add Try Again button
    callback_data = "ck"
    if payload:
        callback_data = f"ck_{payload}"

    buttons.append([InlineKeyboardButton("🔄 ᴛʀʏ ᴀɢᴀɪɴ", callback_data=callback_data, style=random_button_style())])

    return InlineKeyboardMarkup(buttons)

async def is_sub(client, user_id, channel_id):
    now = time.time()
    cache_key = (user_id, channel_id)
    if cache_key in _FSUB_SUB_CACHE:
        val, expiry = _FSUB_SUB_CACHE[cache_key]
        if now < expiry:
            return val

    try:
        member = await client.get_chat_member(channel_id, user_id)
        status = member.status
        res = status in {
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        }
        ttl = 300 if res else 5
        _FSUB_SUB_CACHE[cache_key] = (res, now + ttl)
        return res

    except UserNotParticipant:
        mode = await db.get_channel_mode(channel_id)
        if mode == "on":
            exists = await db.req_user_exist(channel_id, user_id)
            ttl = 300 if exists else 5
            _FSUB_SUB_CACHE[cache_key] = (exists, now + ttl)
            return exists
        _FSUB_SUB_CACHE[cache_key] = (False, now + 5)
        return False

    except Exception as e:
        print(f"[!] Error in is_sub(): {e}")
        return False

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


async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

async def decode(base64_string):
    base64_string = base64_string.strip("=") # links generated before this commit will be having = sign, hence striping them to handle padding errors.
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes) 
    string = string_bytes.decode("ascii")
    return string


async def get_messages(client, message_ids, chat_id=None):
    messages = []
    total_messages = 0

    db_channels = []
    if chat_id:
        db_channels.append(chat_id)

    bot_uname = getattr(client, "username", None)
    if bot_uname:
        known_channels = await db.get_all_db_channels(bot_uname)
        for c in known_channels:
            if c and c not in db_channels:
                db_channels.append(c)

    if hasattr(client, 'db_channel') and client.db_channel and client.db_channel.id not in db_channels:
        db_channels.append(client.db_channel.id)
    if hasattr(client, 'db_channel_id') and client.db_channel_id and client.db_channel_id not in db_channels:
        db_channels.append(client.db_channel_id)
    if CHANNEL_ID and CHANNEL_ID not in db_channels:
        db_channels.append(CHANNEL_ID)

    if not db_channels:
        return []

    while total_messages < len(message_ids):
        temb_ids = message_ids[total_messages:total_messages+200]

        # Try fetching from all assigned DB channels
        batch_msgs = [None] * len(temb_ids)
        remaining_ids = list(temb_ids)

        for cid in db_channels:
            if not remaining_ids: break
            try:
                msgs = await client.get_messages(
                    chat_id=cid,
                    message_ids=remaining_ids
                )
                if not isinstance(msgs, list): msgs = [msgs]

                for m in msgs:
                    if m and not m.empty:
                        # Find original index in temb_ids to maintain order
                        try:
                            idx = temb_ids.index(m.id)
                            batch_msgs[idx] = m
                        except ValueError:
                            # This message ID wasn't in the current batch we requested
                            continue
                        if m.id in remaining_ids: remaining_ids.remove(m.id)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"[ERROR] get_messages from {cid}: {e}")

        messages.extend([m for m in batch_msgs if m])
        total_messages += len(temb_ids)

    return messages

async def get_message_id(client, message):
    # Multi-DB support
    db_channels = await db.get_all_db_channels(client.username)
    if not db_channels:
        if hasattr(client, 'db_channel') and client.db_channel:
            db_channels = [client.db_channel.id]
        elif hasattr(client, 'db_channel_id') and client.db_channel_id:
            db_channels = [client.db_channel_id]

    if message.forward_from_chat:
        if message.forward_from_chat.id in db_channels:
            return message.forward_from_message_id, message.forward_from_chat.id
        else:
            return 0, 0
    elif message.forward_sender_name:
        return 0, 0

    text = message.text or message.caption
    if text:
        pattern = r"(?:https?://)?(?:t\.me|telegram\.(?:me|dog))/(?:c/)?([^//\s]+)/(\d+)"
        matches = re.search(pattern, text, re.IGNORECASE)
        if not matches:
            return 0, 0

        channel_id = matches.group(1).strip()
        msg_id = int(matches.group(2))

        # Check against all DB channels
        cleaned_channel_id = channel_id.replace("-100", "").replace("-", "")
        for cid in db_channels:
            str_cid = str(cid).replace("-100", "").replace("-", "")
            if cleaned_channel_id.isdigit() and str_cid.isdigit():
                if str_cid == cleaned_channel_id or str_cid.endswith(cleaned_channel_id) or cleaned_channel_id.endswith(str_cid):
                    return msg_id, cid
            else:
                # If we have chat username, we need to compare
                if cid in chat_username_cache:
                    username = chat_username_cache[cid]
                    if username and username.lower() == channel_id.lower():
                        return msg_id, cid
                    continue

                try:
                    chat = await client.get_chat(cid)
                    chat_username_cache[cid] = chat.username
                    if chat.username and chat.username.lower() == channel_id.lower():
                        return msg_id, cid
                except:
                    pass
        return 0, 0
    else:
        return 0, 0



def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time


def get_exp_time(seconds):
    periods = [('days', 86400), ('hours', 3600), ('mins', 60), ('secs', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)} {period_name}'
    return result

def is_video(message):
    if message.video or message.animation:
        return True
    if message.document and message.document.mime_type:
        if message.document.mime_type.startswith('video/'):
            return True
    if message.document and message.document.file_name:
        video_extensions = ('.mkv', '.mp4', '.avi', '.webm', '.mov', '.wmv', '.3gp', '.m4v', '.ts', '.m3u8', '.flv')
        if message.document.file_name.lower().endswith(video_extensions):
            return True
    return False

def get_filename(message):
    if message.video:
        return message.video.file_name or "Video"
    if message.animation:
        return message.animation.file_name or "Animation"
    if message.document:
        return message.document.file_name or "File"
    if message.audio:
        return message.audio.file_name or "Audio"
    if message.voice:
        return "Voice_Message.ogg"
    return "File"

def generate_stream_hash(msg_id):
    from config import API_HASH
    return hashlib.sha256(f"{msg_id}{API_HASH}".encode()).hexdigest()[:10]

class MockMessage:
    def __init__(self, text):
        self.text = text
        self.caption = None
        self.forward_from_chat = None
        self.forward_sender_name = None

async def resolve_link_id(client, link):
    """Mocks a message to use get_message_id logic for a link string."""
    mock_msg = MockMessage(text=link)
    return await get_message_id(client, mock_msg)

def extract_urls(message: Message):
    """Extracts all URLs from a message including plain text, hyperlinks, and raw HTML links."""
    urls = []
    text = message.text or message.caption
    if not text:
        return []

    # 1. Extract using Telegram Entities (Highly Accurate)
    entities = message.entities or message.caption_entities
    if entities:
        for entity in entities:
            try:
                if entity.type.name == "URL":
                    urls.append(text[entity.offset:entity.offset+entity.length])
                elif entity.type.name == "TEXT_LINK":
                    urls.append(entity.url)
            except:
                continue

    # 2. Extract using Regex (Fallback for raw HTML tags or unparsed text)
    # This pattern looks for http/https and stops at common delimiters like space, quote, or angle bracket
    regex_pattern = r"(https?://[^\s<>\"'()]+)"
    found_urls = re.findall(regex_pattern, text)
    if found_urls:
        for url in found_urls:
            # Clean trailing punctuation that might be part of the sentence but not the URL
            cleaned_url = url.rstrip('.,;!?)]} ')
            urls.append(cleaned_url)

    return list(dict.fromkeys(urls)) # Remove duplicates and preserve order

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





class BotAdminTaskContext:
    def __init__(self, client, user_id, message=None):
        self.client = client
        self.user_id = user_id
        self.message = message
        self.queue_msg = None
        self.lock = db.get_bot_admin_lock(client.username, user_id)

    async def __aenter__(self):
        if self.lock.locked():
            if self.message:
                self.queue_msg = await self.message.reply(
                    "⏳ <b>Task added to queue. Waiting for previous task to finish...</b>"
                )
        await self.lock.acquire()
        if self.queue_msg:
            try:
                await self.queue_msg.delete()
            except:
                pass
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()


subscribed = filters.create(is_subscribed)
admin = filters.create(check_admin)


# --- MONKEYPATCHING PYROGRAM CLIENT & MESSAGE TO ACHIEVE COMPLETE UI/MEDIA REVOLUTION --- #

import re
from pyrogram import Client
from pyrogram.types import Message
import random

# Save original methods
orig_send_message = Client.send_message
orig_send_photo = Client.send_photo
orig_send_video = Client.send_video
orig_send_document = Client.send_document
orig_send_animation = Client.send_animation
orig_send_audio = Client.send_audio

orig_edit_message_text = Client.edit_message_text
orig_edit_message_caption = Client.edit_message_caption

orig_msg_reply_text = Message.reply_text
orig_msg_reply = Message.reply
orig_msg_edit_text = Message.edit_text
orig_msg_edit = Message.edit

def make_fancy_sans_bold_italic(text):
    res = []
    for char in text:
        val = ord(char)
        if 65 <= val <= 90: # A-Z
            res.append(chr(val + 120315))
        elif 97 <= val <= 122: # a-z
            res.append(chr(val + 120309))
        elif 48 <= val <= 57: # 0-9
            res.append(chr(val + 120764))
        else:
            res.append(char)
    return "".join(res)

def enhance_ui_layout(text):
    if not text:
        return text
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 5 and all(c in '-=_*~•' for c in stripped):
            cleaned_lines.append("✦ ━━━━━━━━━━━━━━━━━ ✦")
        else:
            if stripped.startswith("• "):
                line = line.replace("• ", "💎 ", 1)
            elif stripped.startswith("- "):
                line = line.replace("- ", "✨ ", 1)
            elif stripped.startswith("* "):
                line = line.replace("* ", "⭐ ", 1)
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def style_text_safely(text):
    if not text:
        return text
    try:
        text = enhance_ui_layout(text)
        pattern = re.compile(
            r'(<[^>]+>|https?://[^\s<>"]+|@[a-zA-Z0-9_]+|/[a-zA-Z0-9_]+|`[^`]+`)',
            re.IGNORECASE
        )
        parts = pattern.split(text)
        new_parts = []
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Clean raw markdown characters (*, **, __) from plain text to prevent them showing on screen
                part_cleaned = part.replace("**", "").replace("*", "").replace("__", "")

                # Style numeric IDs with Bold-Italic-Mono
                id_pattern = re.compile(r'(\b\d{5,}\b)')
                sub_parts = id_pattern.split(part_cleaned)
                sub_new_parts = []
                for j, sub_part in enumerate(sub_parts):
                    if j % 2 == 1:
                        sub_new_parts.append(f"<b><i><code>{sub_part}</code></i></b>")
                    else:
                        sub_new_parts.append(make_fancy_sans_bold_italic(sub_part))
                new_parts.append("".join(sub_new_parts))
            else:
                # Odd index: HTML tag, URL link, mention, or command
                if part.startswith("@"):
                    # Username/mention: wrap in a clickable normal-font HTML hyperlink
                    username_clean = part[1:]
                    new_parts.append(f'<a href="https://t.me/{username_clean}">{part}</a>')
                elif part.startswith(("http://", "https://")) or "t.me/" in part:
                    new_parts.append(f"<b><i><code>{part}</code></i></b>")
                else:
                    new_parts.append(part)
        return "".join(new_parts)
    except Exception as e:
        print(f"[UI ENHANCER ERROR] Exception in style_text_safely: {e}")
        return text

async def patched_send_message(self, chat_id, text, *args, **kwargs):
    if text:
        try:
            text = style_text_safely(text)
        except Exception as e:
            print(f"[UI ENHANCER ERROR] Exception in style_text_safely: {e}")

        # Check if we should convert to a beautiful media banner
        is_admin_or_system = False
        text_str = str(text)
        text_lower = text_str.lower()
        if "system logs" in text_lower or "database" in text_lower or "active tasks" in text_lower or "username:" in text_lower or "user id:" in text_lower or "total count" in text_lower or len(text_str) > 1000:
            is_admin_or_system = True

        if not is_admin_or_system:
            try:
                banners = await get_banners(self)
                if banners:
                    banner = random.choice(banners)
                    is_video = str(banner).lower().split('?')[0].endswith(('.mp4', '.mkv', '.webm', '.gif'))

                    media_kwargs = {}
                    for k in ['reply_to_message_id', 'reply_markup', 'parse_mode', 'protect_content', 'message_effect_id', 'disable_notification']:
                        if k in kwargs:
                            media_kwargs[k] = kwargs[k]

                    if is_video:
                        return await orig_send_video(
                            self,
                            chat_id=chat_id,
                            video=banner,
                            caption=text,
                            **media_kwargs
                        )
                    else:
                        return await orig_send_photo(
                            self,
                            chat_id=chat_id,
                            photo=banner,
                            caption=text,
                            **media_kwargs
                        )
            except Exception as e:
                print(f"[MONKEYPATCH ERROR] Failed to send banner, falling back to text: {e}")

    # Fallback to standard text message safely
    try:
        return await orig_send_message(self, chat_id, text, *args, **kwargs)
    except Exception as e:
        print(f"[MONKEYPATCH ERROR] Standard send_message failed: {e}")
        try:
            # Attempt plain text delivery without custom formatting if HTML parse fails
            kwargs.pop("parse_mode", None)
            clean_text = re.sub(r'<[^>]*>', '', str(text)) if text else ""
            return await orig_send_message(self, chat_id, clean_text, *args, **kwargs)
        except Exception as ex:
            print(f"[MONKEYPATCH ERROR] Plain send_message fallback failed: {ex}")
            return None

async def patched_send_photo(self, chat_id, photo, caption=None, *args, **kwargs):
    if caption:
        caption = style_text_safely(caption)
    return await orig_send_photo(self, chat_id, photo, caption=caption, *args, **kwargs)

async def patched_send_video(self, chat_id, video, caption=None, *args, **kwargs):
    if caption:
        caption = style_text_safely(caption)
    return await orig_send_video(self, chat_id, video, caption=caption, *args, **kwargs)

async def patched_send_document(self, chat_id, document, caption=None, *args, **kwargs):
    if caption:
        caption = style_text_safely(caption)
    return await orig_send_document(self, chat_id, document, caption=caption, *args, **kwargs)

async def patched_send_animation(self, chat_id, animation, caption=None, *args, **kwargs):
    if caption:
        caption = style_text_safely(caption)
    return await orig_send_animation(self, chat_id, animation, caption=caption, *args, **kwargs)

async def patched_send_audio(self, chat_id, audio, caption=None, *args, **kwargs):
    if caption:
        caption = style_text_safely(caption)
    return await orig_send_audio(self, chat_id, audio, caption=caption, *args, **kwargs)

async def patched_edit_message_text(self, chat_id, message_id, text, *args, **kwargs):
    if text:
        text = style_text_safely(text)
    try:
        return await orig_edit_message_text(self, chat_id, message_id, text, *args, **kwargs)
    except Exception as e:
        # If it's a media message, try editing the caption instead!
        try:
            cap_kwargs = {}
            for k in ['reply_markup', 'parse_mode']:
                if k in kwargs:
                    cap_kwargs[k] = kwargs[k]
            return await orig_edit_message_caption(self, chat_id, message_id, caption=text, **cap_kwargs)
        except Exception:
            raise e

async def patched_edit_message_caption(self, chat_id, message_id, caption, *args, **kwargs):
    if caption:
        caption = style_text_safely(caption)
    return await orig_edit_message_caption(self, chat_id, message_id, caption, *args, **kwargs)


# Message level methods
async def patched_msg_reply_text(self, text, *args, **kwargs):
    kwargs["reply_to_message_id"] = self.id
    return await self._client.send_message(self.chat.id, text, *args, **kwargs)

async def patched_msg_reply(self, text, *args, **kwargs):
    kwargs["reply_to_message_id"] = self.id
    return await self._client.send_message(self.chat.id, text, *args, **kwargs)

async def patched_msg_edit_text(self, text, *args, **kwargs):
    if self.photo or self.video or self.animation or self.document or self.audio:
        if text:
            text = style_text_safely(text)
        kwargs.pop("disable_web_page_preview", None)
        kwargs.pop("disable_preview", None)
        return await self.edit_caption(caption=text, *args, **kwargs)
    if text:
        text = style_text_safely(text)
    return await orig_msg_edit_text(self, text, *args, **kwargs)

async def patched_msg_edit(self, text, *args, **kwargs):
    if self.photo or self.video or self.animation or self.document or self.audio:
        if text:
            text = style_text_safely(text)
        kwargs.pop("disable_web_page_preview", None)
        kwargs.pop("disable_preview", None)
        return await self.edit_caption(caption=text, *args, **kwargs)
    if text:
        text = style_text_safely(text)
    return await orig_msg_edit(self, text, *args, **kwargs)


# Apply the monkey patches
Client.send_message = patched_send_message
Client.send_photo = patched_send_photo
Client.send_video = patched_send_video
Client.send_document = patched_send_document
Client.send_animation = patched_send_animation
Client.send_audio = patched_send_audio

Client.edit_message_text = patched_edit_message_text
Client.edit_message_caption = patched_edit_message_caption

Message.reply_text = patched_msg_reply_text
Message.reply = patched_msg_reply
Message.edit_text = patched_msg_edit_text
Message.edit = patched_msg_edit


# --- MONKEYPATCHING CLIENT.ON_MESSAGE TO SUPPORT MULTI-CHAT ADMIN COMMAND FLOWS --- #

orig_on_message = Client.on_message

def remove_private_filter(f):
    if f is None:
        return None
    name = type(f).__name__
    if name == "AndFilter":
        left = remove_private_filter(f.base)
        right = remove_private_filter(f.other)
        if left is None: return right
        if right is None: return left
        return left & right
    if name == "OrFilter":
        left = remove_private_filter(f.base)
        right = remove_private_filter(f.other)
        if left is None: return right
        if right is None: return left
        return left | right
    if name == "InvertFilter":
        inner = remove_private_filter(f.base)
        if inner is None: return None
        return ~inner
    if name == "private_filter":
        return None
    return f

def has_admin_filter(f):
    if f is None:
        return False
    name = type(f).__name__
    if name in ["AndFilter", "OrFilter"]:
        return has_admin_filter(f.base) or has_admin_filter(f.other)
    if name == "InvertFilter":
        return has_admin_filter(f.base)
    if hasattr(f, "func") and f.func == check_admin:
        return True
    return False

def patched_on_message(self, filters=None, group=0):
    if filters and has_admin_filter(filters):
        filters = remove_private_filter(filters)

    def decorator(func):
        async def wrapper(client, message, *args, **kwargs):
            if message and message.chat and message.chat.type.name != "PRIVATE":
                msg_text = message.text or message.caption
                if msg_text and msg_text.strip().startswith("/"):
                    is_cmd_admin = False
                    try:
                        is_cmd_admin = await check_admin(None, client, message)
                    except Exception:
                        pass
                    if is_cmd_admin:
                        try:
                            await message.delete()
                        except Exception:
                            pass
            return await func(client, message, *args, **kwargs)
        return orig_on_message(self, filters, group)(wrapper)
    return decorator

Client.on_message = patched_on_message


# Upgrade all InlineKeyboardButton classes to ColoredInlineKeyboardButton in all Pyrogram libraries
import sys
for pkg in ["pyrogram", "pyrofork", "wzgram"]:
    try:
        types_mod = sys.modules.get(f"{pkg}.types")
        if not types_mod:
            types_mod = __import__(f"{pkg}.types", fromlist=["InlineKeyboardButton"])
        if types_mod:
            setattr(types_mod, "InlineKeyboardButton", ColoredInlineKeyboardButton)
            print(f"[PATCH] Patched {pkg}.types.InlineKeyboardButton successfully.")
    except Exception as e:
        pass


#ᴀɴɪᴢᴏɴᴇꜰʟɪx on ᴛɢ :

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