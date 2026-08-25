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
import os
import random
import secrets
import sys
import re
import string
import time
import traceback
import urllib.parse
from urllib.parse import quote
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges, WebAppInfo
from helper_func import InlineKeyboardButton, random_button_style
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant, MessageNotModified
from config import *
from pytz import timezone
from helper_func import *
from helper_func import get_banners, send_media
from database.database import *
from database.db_premium import *
from utils.formatter import RichText


BAN_SUPPORT = f"{BAN_SUPPORT}"
TUT_VID = f"{TUT_VID}"

def ensure_underscore_wrapping(url: str) -> str:
    if not url or not url.startswith("http"):
        return url
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.strip('/')
    if path and not (path.startswith("___") and path.endswith("___")):
        if '/' not in path:
            return f"{parsed.scheme}://{parsed.netloc}/___{path}___"
    return url

def format_ist_time(epoch_time):
    ist = pytz.timezone("Asia/Kolkata")
    dt = datetime.fromtimestamp(epoch_time, tz=ist)
    ms = dt.strftime("%f")[:3]
    return dt.strftime(f"%d %b %Y • %I:%M:%S.{ms} %p")

def parse_iso_to_epoch(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.timestamp()
    except:
        return 0

async def send_verify_log(event_type: str, user_id: int, user_obj, session_id: str, verify_link: str, bot_username: str):
    from bot import Bot
    main_bot = next((b for b in Bot.instances.values() if getattr(b, "name", "") == "Bot"), None)
    if not main_bot:
        main_bot = next(iter(Bot.instances.values()), None)
    if not main_bot:
        return

    dests = await db.get_verify_log_destinations()
    if not dests:
        return

    import pytz
    now_ist = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y • %I:%M:%S %p")

    if user_obj:
        user_details = f"{user_obj.mention} (<code>{user_id}</code>)"
        username_val = f"@{user_obj.username}" if getattr(user_obj, "username", None) else "No Username"
    else:
        user_details = f"<code>{user_id}</code>"
        username_val = "No Username"

    if event_type == "link_generated":
        log_text = (
            "<b>🔗 ˹ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>ᴜsᴇʀ:</b> {user_details}\n"
            f"🆔 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{user_id}</code>\n"
            f"🏷️ <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {username_val}\n"
            f"🕒 <b>ᴛɪᴍᴇ:</b> <code>{now_ist}</code>\n"
            f"🔑 <b>sᴇssɪᴏɴ ɪᴅ:</b> <code>{session_id}</code>\n"
            f"🌐 <b>ᴠᴇʀɪꜰʏ ʟɪɴᴋ:</b> <code>{verify_link}</code>\n"
            f"🤖 <b>ʙᴏᴛ:</b> @{bot_username}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        markup = None
    elif event_type == "verified":
        log_text = (
            "<b>✅ ˹ ɴᴇᴡ ᴜsᴇʀ ᴠᴇʀɪꜰɪᴇᴅ ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🛡️ <b>sᴛᴀᴛᴜs:</b> <b>Verified</b> ✅\n"
            f"👤 <b>ᴜsᴇʀ:</b> {user_details}\n"
            f"🆔 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{user_id}</code>\n"
            f"🏷️ <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {username_val}\n"
            f"🕒 <b>ᴄᴏᴍᴘʟᴇᴛɪᴏɴ ᴛɪᴍᴇ:</b> <code>{now_ist}</code>\n"
            f"🔑 <b>sᴇssɪᴏɴ ɪᴅ:</b> <code>{session_id}</code>\n"
            f"🌐 <b>ᴠᴇʀɪꜰʏ ʟɪɴᴋ:</b> <code>{verify_link}</code>\n"
            f"🤖 <b>ʙᴏᴛ:</b> @{bot_username}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete Verification", callback_data=f"del_ver_{user_id}_{bot_username}", style="danger", icon_custom_emoji_id=5354968347094046619)]
        ])

    for d in dests:
        cid = d['chat_id']
        try:
            await main_bot.send_message(chat_id=cid, text=log_text, reply_markup=markup)
        except Exception as e:
            print(f"[VERIFY LOG ERROR] Destination {cid} failed: {e}")
            try:
                report_text = f"⚠️ <b>Verify Log Destination Failed:</b> {d.get('title')} (<code>{cid}</code>)\nError: `{e}`"
                await main_bot.send_message(OWNER_ID, report_text)
            except: pass

SESSION_CLIENTS = {}

async def get_session_client(session_str: str) -> Client:
    global SESSION_CLIENTS
    if session_str in SESSION_CLIENTS:
        cli = SESSION_CLIENTS[session_str]
        try:
            if getattr(cli, "is_connected", False):
                return cli
            await cli.start()
            return cli
        except Exception:
            SESSION_CLIENTS.pop(session_str, None)

    import config
    import random
    cli = Client(
        name=f"delivery_{random.randint(10000, 99999)}",
        api_id=config.APP_ID,
        api_hash=config.API_HASH,
        session_string=session_str,
        in_memory=True
    )
    await cli.start()
    SESSION_CLIENTS[session_str] = cli
    return cli

async def get_protect_content_for_user(user_id: int, bot_username: str = None) -> bool:
    settings = await db.get_settings(bot_username=bot_username)
    # Check if user is admin or owner (Auth user)
    from config import OWNER_ID
    is_auth = (user_id == OWNER_ID or await db.admin_exist(user_id))
    if is_auth:
        return settings.get('protect_content_auth', False)

    # Check if user is premium
    from database.db_premium import is_premium_user
    is_premium = await is_premium_user(user_id)
    if is_premium:
        return settings.get('protect_content_premium', False)

    # Otherwise, normal user
    return settings.get('protect_content_normal', False)

async def resume_delivery(client: Client, task: dict):
    try:
        user_id = int(task["user_id"])
        base64_string = task["base64_string"]
        current_index = task.get("current_index", 0)
        await send_files(client, user_id, base64_string, resume_index=current_index, task_id=task["_id"], force_sequential=True)
    except Exception as e:
        print(f"[RESUME DELIVERY ERROR] {e}")

async def send_files(client: Client, user_id: int, base64_string, messages=None, resume_index=0, task_id=None, force_sequential=False):
    # Mandatory Access Check
    access_status = await check_user_access(client, user_id)
    if access_status != "granted":
        if access_status == "banned":
            return # Should have been handled by caller or access_control
        if access_status in ["fsub", "bot"]:
            # We can't easily return a photo message from here without the original message object
            # But we should at least block the delivery
            return

    settings = await db.get_settings(bot_username=client.username)

    if not settings.get('file_delivery', True) and user_id != OWNER_ID:
        try:
            await client.send_message(
                chat_id=user_id,
                text="<b>⚡️ <blockquote>˹ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ ˼\n\n🛡 ꜰɪʟᴇ ᴅᴇʟɪᴠᴇʀʏ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴅɪsᴀʙʟᴇᴅ ʙʏ ᴛʜᴇ sᴜᴘʀᴇᴍᴇ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ. 💤</blockquote></b>"
            )
        except: pass
        return

    try:
        # Instant delivery: Skip processing message to reduce roundtrips and latency
        temp_msg = None

        # New Payload Storage support
        stored_payload = await db.get_payload(base64_string)
        if stored_payload:
            string = stored_payload
        else:
            string = await decode(base64_string)

        argument = string.split("-")

        ids = []
        # Multi-DB support: We need to find which DB channel this ID belongs to.
        # Since we multiply by abs(channel_id), we can recover the channel_id if we have the list.
        db_channels = await db.get_all_db_channels(client.username)
        if not db_channels:
            if hasattr(client, 'db_channel') and client.db_channel:
                db_channels = [client.db_channel.id]
            elif hasattr(client, 'db_channel_id') and client.db_channel_id:
                db_channels = [client.db_channel_id]
            elif CHANNEL_ID:
                db_channels = [CHANNEL_ID]

        def get_real_id(val):
            if not val or val == 0:
                return None, None
            for cid in db_channels:
                if cid and val % abs(cid) == 0:
                    return val // abs(cid), cid

            default_cid = None
            if db_channels:
                default_cid = db_channels[0]
            elif hasattr(client, 'db_channel') and client.db_channel:
                default_cid = client.db_channel.id
            elif hasattr(client, 'db_channel_id') and client.db_channel_id:
                default_cid = client.db_channel_id
            elif CHANNEL_ID:
                default_cid = CHANNEL_ID

            if default_cid and val % abs(default_cid) == 0:
                return val // abs(default_cid), default_cid

            # If val is raw (unmultiplied message ID), val ITSELF is the real message ID!
            return val, default_cid

        get_match = re.match(r"^get-(-?\d+)(?:-(-?\d+))?$", string)
        list_match = re.match(r"^list-(-?\d+)-(.+)$", string)

        if get_match:
            try:
                start_raw = int(get_match.group(1))
                end_raw = get_match.group(2)
                if end_raw:
                    start, cid = get_real_id(start_raw)
                    end, _ = get_real_id(int(end_raw))
                    if start is not None:
                        ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
                else:
                    real_id, cid = get_real_id(start_raw)
                    if real_id is not None:
                        ids = [real_id]
            except Exception as e:
                print(f"Error parsing regex get match: {e}")
        elif list_match:
            try:
                cid_raw = int(list_match.group(1))
                id_list_str = list_match.group(2)
                _, cid = get_real_id(cid_raw)
                if cid is not None:
                    ids = [int(x) for x in id_list_str.split("-") if x.strip().replace("-", "").isdigit()]
            except Exception as e:
                print(f"Error parsing regex list match: {e}")
        else:
            if argument[0] == "get":
                if len(argument) == 3:
                    try:
                        start_raw = int(argument[1])
                        end_raw = int(argument[2])
                        start, cid = get_real_id(start_raw)
                        end, _ = get_real_id(end_raw)
                        if start is None: return
                        ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
                    except Exception as e:
                        print(f"Error decoding IDs: {e}")
                        return
                elif len(argument) == 2:
                    try:
                        val_raw = int(argument[1])
                        real_id, cid = get_real_id(val_raw)
                        if real_id is None: return
                        ids = [real_id]
                    except Exception as e:
                        print(f"Error decoding ID: {e}")
                        return
            elif argument[0] == "list":
                try:
                    cid_raw = int(argument[1])
                    _, cid = get_real_id(cid_raw)
                    if cid is None: return
                    ids = [int(x) for x in argument[2:]]
                except Exception as e:
                    print(f"Error decoding list IDs: {e}")
                    return
            else:
                # Legacy Format: ID-ID or ID (without 'get-' or 'list-' prefix)
                if len(argument) == 2:
                    try:
                        start_raw = int(argument[0])
                        end_raw = int(argument[1])
                        start, cid = get_real_id(start_raw)
                        end, _ = get_real_id(end_raw)
                        if start is not None:
                            ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
                    except: pass
                elif len(argument) == 1:
                    try:
                        val_raw = int(argument[0])
                        real_id, cid = get_real_id(val_raw)
                        if real_id is not None:
                            ids = [real_id]
                    except: pass

        try:
            if not messages:
                messages = await get_messages(client, ids, chat_id=cid)
        except Exception as e:
            try:
                await client.send_message(chat_id=user_id, text="Something went wrong!")
            except: pass
            print(f"Error getting messages: {e}")
            return
        finally:
            if temp_msg:
                try:
                    await temp_msg.delete()
                except:
                    pass

        # File auto-delete time in seconds
        FILE_AUTO_DELETE = await db.get_del_timer()

        # Load custom caption settings once for the delivery run
        settings_caption = await db.get_settings(bot_username=client.username)
        caption_active = settings_caption.get('custom_caption_active', True)
        custom_caption = settings_caption.get('custom_caption_text', "") if caption_active else ""

        # Carousel logic: if multiple files, send as Carousel
        carousel_active = settings_caption.get('carousel_active', True)
        if len(messages) > 1 and carousel_active and not force_sequential:
            from utils.carousel import create_carousel_session, render_carousel_page
            session_id = await create_carousel_session(user_id, cid, ids, client.username, base64_string=base64_string)
            input_media, markup = await render_carousel_page(client, session_id, 0)
            if input_media and markup:
                buttons = list(markup.inline_keyboard)
                buttons.append([InlineKeyboardButton("📥 Download All", callback_data=f"car_dl_all:{session_id}")])
                markup = InlineKeyboardMarkup(buttons)

                is_legacy = False
                try:
                    user_doc = await db.user_data.find_one({"_id": user_id})
                    if user_doc and user_doc.get("legacy_client") is True:
                        is_legacy = True
                except: pass

                caption = RichText.clean_unsupported(input_media.caption, is_legacy=is_legacy)

                msg0 = messages[0]
                protect_val = await get_protect_content_for_user(user_id, client.username)

                if msg0.photo:
                    await client.send_photo(chat_id=user_id, photo=msg0.photo.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                elif msg0.video:
                    await client.send_video(chat_id=user_id, video=msg0.video.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                elif msg0.document:
                    await client.send_document(chat_id=user_id, document=msg0.document.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                elif msg0.audio:
                    await client.send_audio(chat_id=user_id, audio=msg0.audio.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                elif msg0.animation:
                    await client.send_animation(chat_id=user_id, animation=msg0.animation.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                return

        # ULTRA-FAST SEQUENTIAL DELIVERY (V12 Engine)
        # Guarantees perfect chronological order (strictly non-shuffled) by using sequential awaiting
        # while maximizing speed and eliminating FloodWait issues via round-robin helper bot selection.
        AniZoneFlix_msgs = []

        from bot import Bot
        helper_tokens = list(Bot.helper_clients.keys())

        # Persist task delivery progress if multiple files are sent
        if not task_id and len(messages) > 1:
            import uuid
            task_id = f"delivery_{user_id}_{int(time.time())}"
            await db.database['active_tasks'].insert_one({
                "_id": task_id,
                "type": "delivery",
                "status": "running",
                "user_id": str(user_id),
                "base64_string": base64_string,
                "current_index": 0,
                "total_files": len(messages),
                "created_at": time.time()
            })

        for index, msg in enumerate(messages):
            if not msg or msg.empty:
                continue

            if index < resume_index:
                # Already sent in previous run, skip
                continue

            # Update active task index
            if task_id:
                await db.database['active_tasks'].update_one(
                    {"_id": task_id},
                    {"$set": {"current_index": index}}
                )

            # User preference: "Custom caption allow to modify"
            original_caption = msg.caption.html if (msg.caption and hasattr(msg.caption, "html")) else (msg.caption or "")
            caption = f"{original_caption}\n\n{custom_caption}" if (original_caption and custom_caption) else (original_caption or custom_caption)

            # Truncate caption for media to prevent MEDIA_CAPTION_TOO_LONG errors
            if caption and len(caption) > 1024:
                caption = caption[:1020] + "..."

            reply_markup = None

            # Round-robin selection of helper bot based on index to distribute workload
            # and completely eliminate FloodWait issues!
            if not helper_tokens:
                clients_to_try = [client]
            else:
                # Build an ordered list of helper clients starting with the round-robin choice
                start_idx = index % len(helper_tokens)
                ordered_tokens = helper_tokens[start_idx:] + helper_tokens[:start_idx]
                clients_to_try = [Bot.helper_clients[t] for t in ordered_tokens] + [client]

            sent_msg = None
            from_chat_id = msg.chat.id if (msg and hasattr(msg, 'chat') and msg.chat and getattr(msg.chat, 'id', None)) else cid

            for current_client in clients_to_try:
                try:
                    protect_val = await get_protect_content_for_user(user_id, client.username)
                    sent_msg = await current_client.copy_message(
                        chat_id=user_id,
                        from_chat_id=from_chat_id,
                        message_id=msg.id,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=protect_val
                    )
                    break # Succeeded, move to next message in the sequential loop!
                except FloodWait as e:
                    # If hit with FloodWait, try the next helper client immediately
                    await asyncio.sleep(e.value if e.value else 0.5)
                except Exception as e:
                    pass

            if sent_msg:
                AniZoneFlix_msgs.append(sent_msg)

        if task_id:
            await db.database['active_tasks'].update_one(
                {"_id": task_id},
                {"$set": {"status": "completed"}}
            )

        if AniZoneFlix_msgs:
            await db.log_event(user_id, "CONTENT_ACCESSED", f"Delivered {len(AniZoneFlix_msgs)} files (ID: {base64_string[:10]}...)")
        else:
            try:
                await client.send_message(chat_id=user_id, text="<b>⚠️ requested files not found or deleted from our database.</b>")
            except: pass
            return

        if FILE_AUTO_DELETE > 0 and AniZoneFlix_msgs:
            async def auto_delete_task(cli, uid, msgs, delay, reload_payload):
                try:
                    notification_msg = await cli.send_message(
                        chat_id=uid,
                        text=f"<b>⚡️ <blockquote>˹ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀʟᴇʀᴛ ˼\n\n🛡 ᴛʜɪs ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴛᴇʀᴍɪɴᴀᴛᴇᴅ ɪɴ {get_exp_time(delay)}.\n\n💎 ᴘʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ꜰᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ʙᴇꜰᴏʀᴇ ɪᴛ ɪs ɢᴏɴᴇ! 💫</blockquote></b>"
                    )

                    await asyncio.sleep(delay)

                    for snt_msg in msgs:
                        if snt_msg:
                            try:
                                await snt_msg.delete()
                            except Exception as e:
                                print(f"Error deleting message {getattr(snt_msg, 'id', '')}: {e}")

                    try:
                        reload_url = f"https://t.me/{cli.username}?start={reload_payload}"
                        keyboard = InlineKeyboardMarkup(
                            [[InlineKeyboardButton("⚡️ ˹ ʀᴇᴄᴏᴠᴇʀ ꜰɪʟᴇ ˼ ⚡️", url=reload_url, style="primary", icon_custom_emoji_id=5440389890787281213)]]
                        )

                        await notification_msg.edit(
                            f"<b>🛡 <blockquote>˹ ꜰɪʟᴇ ᴛᴇʀᴍɪɴᴀᴛᴇᴅ ˼\n\n💎 ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪs sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\n🚀 ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ʀᴇᴄᴏᴠᴇʀ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴀssᴇᴛ 👇\n\n<code>{reload_url}</code></blockquote></b>",
                            reply_markup=keyboard
                        )
                    except Exception as e:
                        print(f"Error updating notification with 'Get File Again' button: {e}")
                except Exception as ex:
                    print(f"Error in background auto_delete_task: {ex}")

            asyncio.create_task(auto_delete_task(client, user_id, AniZoneFlix_msgs, FILE_AUTO_DELETE, base64_string))

    except Exception as e:
        print(f"Final Error in send_files: {e}")

async def short_url(client: Client, message: Message, base64_string, anim_msg=None):
    user_id = message.from_user.id

    # Credentials and status from merged settings
    settings = await db.get_settings(bot_username=client.username)

    # 0. Check Shortener Status
    shortener_cfg = settings.get('shortener', {})
    shortener_enabled = settings.get('shortener_active', True)
    if shortener_cfg and 'enabled' in shortener_cfg:
        shortener_enabled = shortener_cfg['enabled']

    if not shortener_enabled:
        return await send_files(client, user_id, base64_string)

    # 2. Check for Pending Referral
    referral = await db.referrals.find_one({"referred_id": str(user_id), "status": "pending"})
    referral_id = referral.get("referrer_id") if referral else None

    # 3. Create Session with Masking Token
    session_id, mask_token = await db.create_verification_session(
        user_id, base64_string, referral_id=referral_id, bot_username=client.username
    )

    verification_enabled = settings.get('verification_enabled', True)
    session_doc = await db.sessions.find_one({"session_id": session_id})
    verification_method = session_doc.get("verification_method") if session_doc else settings.get('verification_method', 'mini_app')

    if not verification_enabled:
        web_url = settings.get('website_url', WEBSITE_URL).rstrip('/')
        final_redirect = f"{web_url}/verify/{session_id}"
        bot_username = client.username
        tg_deeplink = f"https://t.me/{bot_username}?start=verify_{session_id}"
        await db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {
                "original_shortlink": tg_deeplink,
                "traced_url": tg_deeplink,
                "last_traced_url": tg_deeplink,
                "LAST_TRACED_URL": tg_deeplink
            }}
        )
    else:
        if verification_method == "api_url":
            web_url = (settings.get('api_url') or settings.get('website_url', WEBSITE_URL)).rstrip('/')
        else:
            web_url = settings.get('website_url', WEBSITE_URL).rstrip('/')

        final_redirect = f"{web_url}/verify/{session_id}"
        original_shortlink = final_redirect

        if shortener_cfg and shortener_cfg.get('enabled') and shortener_cfg.get('domain') and shortener_cfg.get('api_key_encrypted'):
            from protect import get_short_link
            try:
                shortened = await get_short_link(
                    f"{web_url}/track/{session_id}",
                    alias=mask_token,
                    shortener_url=shortener_cfg['domain'],
                    api_key=shortener_cfg['api_key_encrypted']
                )
                if shortened and shortened.startswith("http"):
                    original_shortlink = ensure_underscore_wrapping(shortened)
                    await db.sessions.update_one(
                        {"session_id": session_id},
                        {"$set": {"original_shortlink": original_shortlink, "traced_url": original_shortlink}}
                    )
            except Exception as e:
                print(f"Error shortening URL with custom shortener: {e}")

    # CONTENT INFO FETCH
    stored_payload = await db.get_payload(base64_string)
    if stored_payload:
        string = stored_payload
    else:
        string = await decode(base64_string)
    argument = string.split("-")
    ids = []

    # Multi-DB aware ID recovery for content info
    db_channels = await db.get_all_db_channels(client.username)
    if not db_channels:
        if hasattr(client, 'db_channel') and client.db_channel:
            db_channels = [client.db_channel.id]
        elif hasattr(client, 'db_channel_id') and client.db_channel_id:
            db_channels = [client.db_channel_id]
        elif CHANNEL_ID:
            db_channels = [CHANNEL_ID]

    def get_real_id_simple(val):
        if not val or val == 0:
            return None, None
        for c in db_channels:
            if c and val % abs(c) == 0:
                return val // abs(c), c

        default_cid = None
        if db_channels:
            default_cid = db_channels[0]
        elif hasattr(client, 'db_channel') and client.db_channel:
            default_cid = client.db_channel.id
        elif hasattr(client, 'db_channel_id') and client.db_channel_id:
            default_cid = client.db_channel_id
        elif CHANNEL_ID:
            default_cid = CHANNEL_ID

        if default_cid and val % abs(default_cid) == 0:
            return val // abs(default_cid), default_cid

        # If val is raw (unmultiplied message ID), val ITSELF is the real message ID!
        return val, default_cid

    get_match = re.match(r"^get-(-?\d+)(?:-(-?\d+))?$", string)
    list_match = re.match(r"^list-(-?\d+)-(.+)$", string)

    if get_match:
        try:
            start_raw = int(get_match.group(1))
            end_raw = get_match.group(2)
            if end_raw:
                start, cid = get_real_id_simple(start_raw)
                end, _ = get_real_id_simple(int(end_raw))
                if start is not None:
                    ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
            else:
                real_id, cid = get_real_id_simple(start_raw)
                if real_id is not None:
                    ids = [real_id]
        except Exception as e:
            print(f"Error parsing regex get match in short_url: {e}")
    elif list_match:
        try:
            cid_raw = int(list_match.group(1))
            id_list_str = list_match.group(2)
            _, cid = get_real_id_simple(cid_raw)
            if cid is not None:
                ids = [int(x) for x in id_list_str.split("-") if x.strip().replace("-", "").isdigit()]
        except Exception as e:
            print(f"Error parsing regex list match in short_url: {e}")
    else:
        if argument[0] == "get":
            if len(argument) == 3:
                start, cid = get_real_id_simple(int(argument[1]))
                end, _ = get_real_id_simple(int(argument[2]))
                if start is not None:
                    ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
            elif len(argument) == 2:
                real_id, cid = get_real_id_simple(int(argument[1]))
                if real_id is not None: ids = [real_id]
        elif argument[0] == "list":
            try:
                cid_raw = int(argument[1])
                _, cid = get_real_id_simple(cid_raw)
                if cid is not None: ids = [int(x) for x in argument[2:]]
            except: pass
        else:
            # Legacy format support in short_url
            if len(argument) == 2:
                start, cid = get_real_id_simple(int(argument[0]))
                end, _ = get_real_id_simple(int(argument[1]))
                if start is not None:
                    ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
            elif len(argument) == 1:
                real_id, cid = get_real_id_simple(int(argument[0]))
                if real_id is not None: ids = [real_id]

    messages = await get_messages(client, ids)
    file_info = ""
    if messages:
        if len(messages) > 1:
            file_info = f"📦 <b>Bᴀᴛᴄʜ:</b> {len(messages)} Fɪʟᴇs"
        else:
            msg = messages[0]
            if msg.document: file_info = f"📄 <b>Fɪʟᴇ:</b> {msg.document.file_name}"
            elif msg.video: file_info = f"🎬 <b>Vɪᴅᴇᴏ:</b> {msg.video.file_name or 'Video'}"
            elif msg.audio: file_info = f"🎵 <b>Aᴜᴅɪᴏ:</b> {msg.audio.file_name or 'Audio'}"
            else: file_info = "💎 <b>Cᴏɴᴛᴇɴᴛ Rᴇᴀᴅʏ</b>"

    validity_secs = settings.get('verify_window', 86400)
    validity_text = get_exp_time(validity_secs)

    access_limit = settings.get('access_limit', 1)
    access_text = "Unlimited" if access_limit == -1 else f"{access_limit} accesses"

    if not verification_enabled or verification_method in ["mini_app", "browser"]:
        buttons = [
            [InlineKeyboardButton("✅ Verify Now", web_app=WebAppInfo(url=final_redirect), style="primary", icon_custom_emoji_id=5440389890787281213)]
        ]
    else:
        buttons = [
            [InlineKeyboardButton("✅ Verify Now", url=final_redirect, style="primary", icon_custom_emoji_id=5440389890787281213)]
        ]

    tut_link = settings.get("tutorial_link", TUT_VID)
    tut_enabled = settings.get("tutorial_enabled", True)
    if tut_enabled and tut_link:
        buttons.append([InlineKeyboardButton("📹 Tutorial", url=tut_link, style="primary", icon_custom_emoji_id=5440389890787281213)])

    buttons.append([
        InlineKeyboardButton(
            "✅ I Have Verified",
            url=f"https://t.me/{client.username}?start={base64_string}",
            style="success", icon_custom_emoji_id=5355142851615283756
        )
    ])

    heading = RichText.format_heading("Your File is Ready", level=1)
    body = "🔐 <b>Verification is required before accessing your content.</b>\n\nComplete verification to continue."

    blockquote_content = (
        f"◈ {file_info}\n"
        f"◈ Expiry Duration: <b>{validity_text}</b>\n"
        f"◈ Access Limit: <b>{access_text}</b>"
    )

    quote = RichText.format_quote(blockquote_content, expandable=True)
    caption = f"{heading}\n\n{body}\n\n{quote}"

    is_legacy = False
    try:
        user_doc = await db.user_data.find_one({"_id": user_id})
        if user_doc and user_doc.get("legacy_client") is True:
            is_legacy = True
    except:
        pass

    caption = RichText.clean_unsupported(caption, is_legacy=is_legacy)

    if anim_msg:
        await anim_msg.edit(
            text=caption,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await message.reply(
            text=caption,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Send verification link generated log to all configured destinations
    asyncio.create_task(send_verify_log("link_generated", user_id, message.from_user, session_id, final_redirect, client.username))

async def handle_payload(client: Client, message: Message, basic_payload: str):
    user_id = message.from_user.id

    # Credentials and status from merged settings
    settings = await db.get_settings(bot_username=client.username)
    shortener_enabled = settings.get('shortener_active', True)


    # Clean payload and get base64 string
    is_verified_payload = basic_payload.startswith("yu3elk")
    if is_verified_payload:
        base64_string = basic_payload[6:-1]
    else:
        base64_string = basic_payload

    # CHECK FOR GLOBAL OR WORKER VERIFICATION
    is_verified = await db.is_user_verified(user_id, bot_username=client.username)
    if not is_verified:
        shortener_cfg = settings.get('shortener', {})
        if shortener_cfg and shortener_cfg.get('enabled'):
            expire_secs = shortener_cfg.get('verify_expire', 86400)
            is_verified = await db.is_verified_worker(client.username, user_id, expire_secs)

    if is_verified:
        await db.decrement_user_credits(user_id, bot_username=client.username)
        return await send_files(client, user_id, base64_string)

    if not shortener_enabled:
        return await send_files(client, user_id, base64_string)

    is_premium = await is_premium_user(user_id)
    is_admin = await db.admin_exist(user_id) or user_id == OWNER_ID
    shorten_admins = settings.get('shorten_admins', True)

    # Skip shortening for admins if configured
    if is_admin and not shorten_admins:
        return await send_files(client, user_id, base64_string)

    if is_premium:
        return await send_files(client, user_id, base64_string)

    # Proceed to verification with Content Info
    await short_url(client, message, base64_string)

@Client.on_message(filters.command('ping') & filters.private)
async def ping_command(client: Client, message: Message):
    start_time = time.time()
    reply = await message.reply_text("<b>⚡ ᴘɪɴɢɪɴɢ...</b>")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 2)
    await reply.edit_text(f"<b>🏓 ᴘᴏɴɢ!</b>\n\n⏱️ <code>{ping_time} ms</code>")

@Client.on_message(filters.command('help') & filters.private)
async def help_command(client: Client, message: Message):
    # help_command logic
    buttons = [
        [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start', style="primary", icon_custom_emoji_id=5440389890787281213),
         InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close', style="danger", icon_custom_emoji_id=5354968347094046619)]
    ]
    await message.reply_text(
        text=HELP_TXT.format(first=message.from_user.first_name),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r"^del_ver_"))
async def delete_verification_callback(client: Client, query: CallbackQuery):
    try:
        data = query.data
        parts = data.split("_")
        # format: del_ver_{user_id}_{bot_username}
        user_id = int(parts[2])
        bot_username = parts[3].lower().replace("@", "")

        # Check if the clicking user is admin or owner
        is_admin = await db.admin_exist(query.from_user.id) or query.from_user.id == OWNER_ID
        if not is_admin:
            return await query.answer("❌ You are not authorized to perform this action!", show_alert=True)

        # Set verification to False / expired
        await db.user_data.update_one(
            {'_id': user_id},
            {'$set': {
                f'bot_verifications.{bot_username}.verified': False,
                f'bot_verifications.{bot_username}.remaining_access': 0,
                f'bot_verifications.{bot_username}.expires_at': 0,
                'verified': False,
                'remaining_access': 0,
                'expires_at': 0
            }}
        )

        await query.answer("✅ User verification successfully deleted/expired!", show_alert=True)

        # Edit the log channel message to indicate it was deleted by an admin
        await query.message.edit_text(
            f"{query.message.text}\n\n"
            f"🗑️ <b>ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴅᴇʟᴇᴛᴇᴅ/ᴇxᴘɪʀᴇᴅ</b> ʙʏ {query.from_user.mention}"
        )
    except Exception as e:
        print(f"Error in delete_verification_callback: {e}")
        await query.answer("❌ Error: Could not delete verification session.", show_alert=True)

@Client.on_message(filters.command('proverify') & filters.private & admin)
async def proverify_command(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        settings = await db.get_settings(bot_username=client.username)

        # Create new verification session
        session_id, wrapped_token = await db.create_verification_session(
            user_id, "verify_general", bot_username=client.username
        )

        # Set is_pro to True on the session
        await db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"is_pro": True}}
        )

        verification_enabled = settings.get('verification_enabled', True)
        session_doc = await db.sessions.find_one({"session_id": session_id})
        verification_method = session_doc.get("verification_method") if session_doc else settings.get('verification_method', 'mini_app')

        if not verification_enabled:
            web_url = settings.get('website_url', WEBSITE_URL).rstrip('/')
            final_redirect = f"{web_url}/verify/{session_id}"
            bot_username = client.username
            tg_deeplink = f"https://t.me/{bot_username}?start=verify_{session_id}"
            await db.sessions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "original_shortlink": tg_deeplink,
                    "traced_url": tg_deeplink,
                    "last_traced_url": tg_deeplink,
                    "LAST_TRACED_URL": tg_deeplink
                }}
            )
        else:
            if verification_method == "api_url":
                web_url = (settings.get('api_url') or settings.get('website_url', WEBSITE_URL)).rstrip('/')
            else:
                web_url = settings.get('website_url', WEBSITE_URL).rstrip('/')

            final_redirect = f"{web_url}/verify/{session_id}"
            original_shortlink = final_redirect

            shortener_cfg = settings.get('shortener', {})
            if shortener_cfg and shortener_cfg.get('enabled') and shortener_cfg.get('domain') and shortener_cfg.get('api_key_encrypted'):
                from protect import get_short_link
                try:
                    shortened = await get_short_link(
                        f"{web_url}/track/{session_id}",
                        alias=wrapped_token,
                        shortener_url=shortener_cfg['domain'],
                        api_key=shortener_cfg['api_key_encrypted']
                    )
                    if shortened and shortened.startswith("http"):
                        original_shortlink = ensure_underscore_wrapping(shortened)
                        await db.sessions.update_one(
                            {"session_id": session_id},
                            {"$set": {"original_shortlink": original_shortlink, "traced_url": original_shortlink}}
                        )
                except Exception as e:
                    print(f"Error shortening URL: {e}")

        # Build beautiful UI message
        if not verification_enabled or verification_method in ["mini_app", "browser"]:
            buttons = [
                [InlineKeyboardButton("🔗 ᴘʀᴏ ᴠᴇʀɪꜰʏ", web_app=WebAppInfo(url=final_redirect), style="primary", icon_custom_emoji_id=5440389890787281213)]
            ]
        else:
            buttons = [
                [InlineKeyboardButton("🔗 ᴘʀᴏ ᴠᴇʀɪꜰʏ", url=final_redirect, style="primary", icon_custom_emoji_id=5440389890787281213)]
            ]

        buttons.append([
            InlineKeyboardButton(
                "✅ ɪ ʜᴀᴠᴇ ᴠᴇʀɪꜰɪᴇᴅ",
                url=f"https://t.me/{client.username}?start=verify_{session_id}",
                style="success", icon_custom_emoji_id=5355142851615283756
            )
        ])

        caption = (
            "<b>━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👑 ˹ ᴘʀᴏ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ˼ 👑\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote>ʜᴇʏ {message.from_user.mention},\n\n"
            "ʏᴏᴜ ʜᴀᴠᴇ ɢᴇɴᴇʀᴀᴛᴇᴅ ᴀ <b>ᴘʀᴏ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ</b>! 🚀\n\n"
            "ᴛʜɪs ʟɪɴᴋ sᴇᴛs ᴛʜᴇ sᴇssɪᴏɴ ᴀs <b>ᴘʀᴏ</b>, ᴡʜɪᴄʜ ᴀʟʟᴏᴡs:\n"
            "• <b>ᴀɴʏ ᴜsᴇʀ</b> ᴛᴏ ᴠᴇʀɪꜰʏ ᴛʜᴇᴍsᴇʟᴠᴇs ᴜsɪɴɪɢ ɪᴛ.\n"
            "• ʙʏᴘᴀssᴇs ᴀʟʟ ᴇxᴘɪʀʏ ᴄᴏɴsᴛʀᴀɪɴᴛs.\n"
            "• ʙʏᴘᴀssᴇs sɪɴɢʟᴇ-ᴜsᴇʀ ʀᴇsᴛʀɪᴄᴛɪᴏɴs.\n\n"
            f"◈ sᴇssɪᴏɴ ɪᴅ: <code>{session_id}</code></blockquote>"
        )

        banners = await get_banners(client)
        photo = random.choice(banners) if banners else None
        await send_media(
            client=client,
            chat_id=message.chat.id,
            photo=photo,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as e:
        print(f"Error in proverify_command: {e}")
        await message.reply_text("❌ Error generating pro verification session.")

@Client.on_message(filters.command('verify') & filters.private)
async def verify_command(client: Client, message: Message):
    user_id = message.from_user.id
    settings = await db.get_settings(bot_username=client.username)

    # Check if already verified
    user = await db.user_data.find_one({'_id': user_id})
    is_verified = await db.is_user_verified(user_id, bot_username=client.username)

    # Get current status
    bot_username = client.username
    bot_ver = user.get('bot_verifications', {}).get(bot_username, {}) if user else {}
    expires_at = bot_ver.get('expires_at', 0) if is_verified else 0
    remaining_access = bot_ver.get('remaining_access', 0) if is_verified else 0

    time_left_str = "0 secs"
    if is_verified and expires_at > time.time():
        time_left_str = get_exp_time(int(expires_at - time.time()))

    # Create new verification session
    session_id, wrapped_token = await db.create_verification_session(
        user_id, "verify_general", bot_username=client.username
    )

    verification_enabled = settings.get('verification_enabled', True)
    session_doc = await db.sessions.find_one({"session_id": session_id})
    verification_method = session_doc.get("verification_method") if session_doc else settings.get('verification_method', 'mini_app')

    if not verification_enabled:
        web_url = settings.get('website_url', WEBSITE_URL).rstrip('/')
        final_redirect = f"{web_url}/verify/{session_id}"
        bot_username = client.username
        tg_deeplink = f"https://t.me/{bot_username}?start=verify_{session_id}"
        await db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {
                "original_shortlink": tg_deeplink,
                "traced_url": tg_deeplink,
                "last_traced_url": tg_deeplink,
                "LAST_TRACED_URL": tg_deeplink
            }}
        )
    else:
        if verification_method == "api_url":
            web_url = (settings.get('api_url') or settings.get('website_url', WEBSITE_URL)).rstrip('/')
        else:
            web_url = settings.get('website_url', WEBSITE_URL).rstrip('/')

        final_redirect = f"{web_url}/verify/{session_id}"
        original_shortlink = final_redirect

        shortener_cfg = settings.get('shortener', {})
        if shortener_cfg and shortener_cfg.get('enabled') and shortener_cfg.get('domain') and shortener_cfg.get('api_key_encrypted'):
            from protect import get_short_link
            try:
                shortened = await get_short_link(
                    f"{web_url}/track/{session_id}",
                    alias=wrapped_token,
                    shortener_url=shortener_cfg['domain'],
                    api_key=shortener_cfg['api_key_encrypted']
                )
                if shortened and shortened.startswith("http"):
                    original_shortlink = ensure_underscore_wrapping(shortened)
                    await db.sessions.update_one(
                        {"session_id": session_id},
                        {"$set": {"original_shortlink": original_shortlink, "traced_url": original_shortlink}}
                    )
            except Exception as e:
                print(f"Error shortening URL: {e}")

    # Build beautiful UI message
    if not verification_enabled or verification_method in ["mini_app", "browser"]:
        buttons = [
            [InlineKeyboardButton("🔗 ᴠᴇʀɪꜰʏ / ᴇxᴛᴇɴᴅ", web_app=WebAppInfo(url=final_redirect), style="primary", icon_custom_emoji_id=5440389890787281213)]
        ]
    else:
        buttons = [
            [InlineKeyboardButton("🔗 ᴠᴇʀɪꜰʏ / ᴇxᴛᴇɴᴅ", url=final_redirect, style="primary", icon_custom_emoji_id=5440389890787281213)]
        ]

    tut_link = settings.get("tutorial_link", TUT_VID)
    tut_enabled = settings.get("tutorial_enabled", True)
    if tut_enabled and tut_link:
        buttons.append([InlineKeyboardButton("📹 ᴛᴜᴛᴏʀɪᴀʟ", url=tut_link, style="primary", icon_custom_emoji_id=5440389890787281213)])

    buttons.append([
        InlineKeyboardButton(
            "✅ ɪ ʜᴀᴠᴇ ᴠᴇʀɪꜰɪᴇᴅ",
            url=f"https://t.me/{client.username}?start=verify_{session_id}",
            style="success", icon_custom_emoji_id=5355142851615283756
        )
    ])

    if is_verified:
        caption = (
            "<b>━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛡️ ˹ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ sᴛᴀᴛᴜs ˼\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote>ʜᴇʏ {message.from_user.mention},\n\n"
            f"ʏᴏᴜ ᴀʀᴇ ᴄᴜʀʀᴇɴᴛʟʏ <b>ᴠᴇʀɪꜰɪᴇᴅ</b>! ✅\n\n"
            f"◈ 👤 <b>ᴜsᴇʀ:</b> {message.from_user.mention}\n"
            f"◈ ⏳ <b>ᴛɪᴍᴇ ʀᴇᴍᴀɪɴɪɴɢ:</b> <code>{time_left_str}</code>\n"
            f"◈ 🔑 <b>ʀᴇᴍᴀɪɴɪɴɢ ᴀᴄᴄᴇssᴇs:</b> <code>{remaining_access if remaining_access != -1 else 'ᴜɴʟɪᴍɪᴛᴇᴅ'}</code>\n\n"
            f"💡 <i>ʏᴏᴜ ᴄᴀɴ ᴇxᴛᴇɴᴅ ʏᴏᴜʀ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴀɴʏᴛɪᴍᴇ ʙʏ ᴛᴀᴘᴘɪɴɢ ʙᴇʟᴏᴡ.</i></blockquote>"
        )
    else:
        caption = (
            "<b>━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔑 ˹ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ʀᴇǫᴜɪʀᴇᴅ ˼\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote>ʜᴇʏ {message.from_user.mention},\n\n"
            f"ʏᴏᴜ ᴀʀᴇ ᴄᴜʀʀᴇɴᴛʟʏ <b>ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ</b>. ❌\n\n"
            f"ᴛᴀᴘ <b>🔗 ᴠᴇʀɪꜰʏ / ᴇxᴛᴇɴᴅ</b> ᴛᴏ ᴄᴏᴍᴘʟᴇᴛᴇ\n"
            f"ᴛʜᴇ sʜᴏʀᴛ ʟɪɴᴋ ᴀɴᴅ ᴜɴʟᴏᴄᴋ ᴀʟʟ sᴇʀᴠɪᴄᴇs.\n\n"
            f"◈ ᴠᴀʟɪᴅɪᴛʏ: <b>{get_exp_time(settings.get('verify_window', 86400))}</b>\n"
            f"◈ ᴀᴄᴄᴇss ʟɪᴍɪᴛ: <b>{settings.get('access_limit', 1) if settings.get('access_limit', 1) != -1 else 'ᴜɴʟɪᴍɪᴛᴇᴅ'}</b></blockquote>"
        )

    banners = await get_banners(client)
    photo = random.choice(banners) if banners else None
    await send_media(
        client=client,
        chat_id=message.chat.id,
        photo=photo,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

@Client.on_message(filters.command('mystatus') & filters.private)
async def mystatus_command(client: Client, message: Message):
    user_id = message.from_user.id
    is_admin = await db.admin_exist(user_id) or user_id == OWNER_ID

    # Parse arguments (Admins can query other users)
    target_user_id = user_id
    if len(message.command) > 1:
        if is_admin:
            try:
                target_user_id = int(message.command[1].strip())
            except ValueError:
                return await message.reply_text("❌ **Invalid User ID! Must be a numeric value.**")
        else:
            target_user_id = user_id

    # Check status of target_user_id
    is_premium = await is_premium_user(target_user_id)
    is_verified = await db.is_user_verified(target_user_id, bot_username=client.username)

    if not is_premium and not is_verified:
        if target_user_id == user_id:
            return await message.reply_text("❌ You are not verified.\n\nPlease complete verification to continue using this bot.")
        else:
            return await message.reply_text("❌ This user is not verified.")

    # Get details
    activated_time = 0
    expires_at = 0
    plan_name = "Verification Active"

    if is_premium:
        plan_name = "👑 PREMIUM PLAN"
        # Fetch premium doc
        user_doc = await collection.find_one({"user_id": target_user_id})
        if user_doc:
            iso_str = user_doc.get("expiration_timestamp")
            expires_at = parse_iso_to_epoch(iso_str)
            activated_time = expires_at - 2592000 # Fallback 30 days ago
    else:
        # Verified
        plan_name = "🔒 VERIFICATION PLAN"
        user_doc = await db.user_data.find_one({'_id': target_user_id})
        if user_doc:
            bot_ver = user_doc.get('bot_verifications', {}).get(client.username.lower(), {})
            expires_at = bot_ver.get('expires_at', 0)
            activated_time = bot_ver.get('verified_at', 0)

    # Convert times to IST formatted strings
    activated_str = format_ist_time(activated_time) if activated_time > 0 else "N/A"
    expires_str = format_ist_time(expires_at) if expires_at > 0 else "N/A"

    # Send status message first
    status_msg = await message.reply_text("⏳ **Calculating remaining time...**")

    # Start live countdown editing loop
    try:
        loop_count = 0
        while loop_count < 15:
            loop_count += 1
            now = time.time()
            if now >= expires_at:
                await status_msg.edit_text(
                    f"❌ **{plan_name} Expired**\n\n"
                    f"👤 User ID: <code>{target_user_id}</code>\n\n"
                    f"User is not verified."
                )
                break

            remaining_secs = expires_at - now

            # Format countdown
            days = int(remaining_secs // 86400)
            hours = int((remaining_secs % 86400) // 3600)
            minutes = int((remaining_secs % 3600) // 60)
            seconds = int(remaining_secs % 60)
            ms = int((remaining_secs % 1) * 1000)

            # Build premium countdown output
            status_header = RichText.format_heading("Your Account Status", level=1)
            quote_text = (
                f"👤 <b>User ID:</b> <code>{target_user_id}</code>\n"
                f"🟢 <b>Status:</b> <b>Active</b> ✅\n"
                f"🏆 <b>Plan:</b> <b>{plan_name}</b>\n\n"
                f"📅 <b>Activated:</b> <code>{activated_str}</code>\n"
                f"📅 <b>Expires:</b> <code>{expires_str}</code>\n\n"
                f"⏳ <b>Time Left:</b>\n"
                f"<code>{days}d {hours}h {minutes}m {seconds}s {ms}ms</code>"
            )
            quote_block = RichText.format_quote(quote_text, expandable=True)
            text = f"{status_header}\n\n{quote_block}"

            # Add resource-saving pause note on final iteration
            if loop_count == 15:
                text += "\n\n💡 <i>Live countdown paused. Run `/mystatus` again to refresh.</i>"

            try:
                await status_msg.edit_text(text)
            except MessageNotModified:
                pass
            except Exception:
                break

            # Sleep for 1.2 seconds before the next edit
            if loop_count < 15:
                await asyncio.sleep(1.2)

    except Exception as e:
        print(f"Error in countdown loop: {e}")

@Client.on_message(filters.command('id'))
async def id_command(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    username = f"@{message.from_user.username}" if (message.from_user and message.from_user.username) else "No Username"

    # Check if the command was triggered in a group/supergroup or private chat
    if message.chat.type.name in ["SUPERGROUP", "GROUP"]:
        text = (
            "━━━━━━━━━━━━━━━━━━━\n"
            "🆔  <b>˹ ᴛᴇʟᴇɢʀᴀᴍ sʏsᴛᴇᴍ ɪᴅs ˼</b>  🆔\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
        )
        if user_id:
            text += f"👤  <b>ᴜsᴇʀ:</b> <code>{username}</code>\n"
            text += f"👤  <b>ᴜsᴇʀ ɪᴅ:</b> <code>{user_id}</code>\n\n"
        text += (
            f"💬  <b>ᴄʜᴀᴛ ᴛʏᴘᴇ:</b> <code>{message.chat.type.name}</code>\n"
            f"💬  <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{chat_id}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
    else:
        if not user_id:
            return
        text = (
            "━━━━━━━━━━━━━━━━━━━\n"
            "🆔  <b>˹ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ ˼</b>  🆔\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤  <b>ᴜsᴇʀɴᴀᴍᴇ:</b> <code>{username}</code>\n"
            f"👤  <b>ʏᴏᴜʀ ɪᴅ:</b> <code>{user_id}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

    await message.reply_text(text)

@Client.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    if message.from_user.id in db.busy_admins:
        return
    user_id = message.from_user.id

    # Always allow basic user storage for analytics
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
            await db.log_event(user_id, "USER_JOINED", "New user started the bot.")
        except: pass

    # Handle deep link payload
    text = message.text
    if len(text) > 7:
        # Check Shortener Status (SYSTEM button)
        settings = await db.get_settings(bot_username=client.username)
        shortener_active = settings.get('shortener_active', True)

        # Admin bypass logic
        is_admin = await db.admin_exist(user_id) or user_id == OWNER_ID
        is_premium = await is_premium_user(user_id)

        # Parse deep link payload first
        try:
            basic = text.split(" ", 1)[1]
        except IndexError:
            basic = ""

        # Check banned status first globally
        access_status = await check_user_access(client, user_id)
        if access_status == "banned":
            ban_data = await db.get_ban_user_data(user_id)
            reason = ban_data.get('reason', "Policy violations.") if ban_data else "Policy violations."
            return await message.reply_text(
                "🚫 <b>˹ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ ˼</b>\n\n"
                f"<blockquote>ʀᴇᴀsᴏɴ: {reason}</blockquote>\n\n"
                "📩 <b>ꜰᴏʀ ᴜɴʙᴀɴ ᴄᴏɴᴛᴀᴄᴛ:</b>\n"
                "@ALONEKINGSTARBACK\n\n"
                "<i>ʀᴇᴊᴏɪɴ ᴀʟʟ ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟs/ɢʀᴏᴜᴘs ᴀɴᴅ ᴄᴏɴᴛᴀᴄᴛ ᴛʜᴇ ᴏᴡɴᴇʀ ꜰᴏʀ ʀᴇᴠɪᴇᴡ.</i>\n\n"
                "⚠️ ᴛʜɪs ᴀᴄᴛɪᴏɴ ɪs ᴀᴜᴛᴏᴍᴀᴛɪᴄ ᴀɴᴅ ᴛʀɪɢɢᴇʀᴇᴅ ɪᴍᴍᴇᴅɪᴀᴛᴇʟʏ ᴡʜᴇɴ ᴀ ᴠɪᴏʟᴀᴛɪᴏɴ ɪs ᴅᴇᴛᴇᴄᴛᴇᴅ.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🛡 ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ 🛡", url="https://t.me/ALONEKINGSTARBACK", style="primary", icon_custom_emoji_id=5440389890787281213)]]
                )
            )
        elif access_status == "maintenance":
            return await message.reply_text("<b>⚠️ Bot is under maintenance. Please try again later.</b>")

        # 1. AUTHENTICATION GATE DEEP LINK (Must handle before bypass / fsub checks to complete verification successfully)
        try:
            # Check for redeem code candidate
            code_candidate = basic.strip()
            if code_candidate:
                code_to_check = code_candidate.replace("redeem_", "", 1) if code_candidate.startswith("redeem_") else code_candidate
                code_doc = await db.database['redeem_codes'].find_one({"_id": code_to_check.strip().lower()})
                if code_doc:
                    # 1. Verify admin status (Admins cannot claim)
                    is_admin = await db.admin_exist(user_id) or user_id == OWNER_ID
                    if is_admin:
                        return await message.reply_text("❌ <b>Admins are not allowed to redeem codes!</b>")

                    # 2. Check if already premium
                    is_prem = await is_premium_user(user_id)
                    if is_prem:
                        return await message.reply_text("❌ <b>You already have an active Premium membership! Premium users cannot redeem codes.</b>")

                    # 3. Check code expiration
                    if time.time() > code_doc['expires_at']:
                        return await message.reply_text("❌ <b>This redeem code has expired!</b>")

                    # 4. Check claim limit
                    if code_doc['claim_count'] >= code_doc['claim_limit']:
                        return await message.reply_text("❌ <b>This redeem code has reached its maximum claim limit!</b>")

                    # 5. Check if already claimed by this user
                    if user_id in code_doc.get('claimed_users', []):
                        return await message.reply_text("❌ <b>You have already redeemed this code! Each user can redeem a code only once.</b>")

                    # 6. Try atomically to claim and update claim count
                    updated = await db.database['redeem_codes'].find_one_and_update(
                        {
                            "_id": code_doc["_id"],
                            "claim_count": {"$lt": code_doc["claim_limit"]},
                            "claimed_users": {"$ne": user_id}
                        },
                        {
                            "$inc": {"claim_count": 1},
                            "$addToSet": {"claimed_users": user_id}
                        }
                    )

                    if not updated:
                        return await message.reply_text("❌ <b>Redemption failed! Code might have just been fully claimed or already redeemed by you.</b>")

                    # 7. Grant premium
                    formatted_expiry = await add_premium(user_id, code_doc['validity_value'], code_doc['validity_unit'])

                    val_text = f"{code_doc['validity_value']} {code_doc['validity_unit']}"

                    success_msg = (
                        "<b>━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "👑 ˹ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛᴇᴅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ˼ 👑\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
                        f"<blockquote>🎉 <b>Congratulations!</b> Your premium access has been activated.\n\n"
                        f"◈ 👤 <b>User:</b> {message.from_user.mention}\n"
                        f"◈ ⏳ <b>Granted Duration:</b> <code>{val_text}</code>\n"
                        f"◈ 📅 <b>Premium Expires:</b> <code>{formatted_expiry}</code>\n"
                        f"◈ 🚀 <b>Status:</b> Active ✅</blockquote>\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    return await message.reply_text(success_msg)

            if basic.startswith("verify_"):
                # Handle both hyphens and underscores for maximum compatibility
                token = basic.replace("verify_", "")
                session = await db.get_session_by_token(token)

                if not session:
                    normalized = token.replace("___", "")
                    tokens = [token, token.replace("-", "_"), token.replace("_", "-"), normalized, normalized.replace("-", "_"), normalized.replace("_", "-")]
                    session = await db.sessions.find_one({"session_id": {"$in": tokens}})
                    if not session:
                        session = await db.sessions.find_one({"short_token": {"$in": tokens}})
                    if not session:
                        session = await db.sessions.find_one({"mask_token": {"$in": tokens}})
                    if not session:
                        session = await db.sessions.find_one({"secure_token": {"$in": tokens}})
                    if not session:
                        session = await db.sessions.find_one({"alias": {"$in": tokens}})

                is_user_ok = await db.is_user_verified(user_id, bot_username=client.username)

                if not session:
                    if is_user_ok:
                        await message.reply_text("<b>✅ You are already verified!</b>\n\nPlease click the original file link to access your content.")
                    else:
                        await message.reply_text(f"<b>❌ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ!</b>\n\nSecurity Error: Session invalid, expired, or belongs to another user.\n\n<code>DEBUG: {token}</code>")
                    return

                if session and (session.get('is_pro') or str(session['user_id']) == str(user_id)):
                    bot_uname = session.get('bot_username')
                    bot_settings = await db.get_settings(bot_username=bot_uname)

                    # Fallback for used sessions when user is already verified
                    if is_user_ok and session.get('status') == 'used':
                        if session.get('content_id') and session['content_id'] != "verify_general":
                            await send_files(client, user_id, session['content_id'])
                        else:
                            await message.reply_text("<b>✅ You are already verified!</b>")
                        return

                    # Enforce Session Lock
                    if session.get('blocked') or session.get('status') == 'blocked':
                        return await message.reply_text(
                            "🚫 <b>˹ sᴇᴄᴜʀɪᴛʏ ʟᴏᴄᴋ ˼</b>\n\n"
                            "ᴛʜɪs ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ sᴇssɪᴏɴ ʜᴀs ʙᴇᴇɴ <b>ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ʟᴏᴄᴋᴇᴅ</b> ᴅᴜᴇ ᴛᴏ ᴀ ʙʏᴘᴀss ᴅᴇᴛᴇᴄᴛɪᴏɴ.\n\n"
                            "🛡️ ᴘʟᴇᴀsᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ᴀ ɴᴇᴡ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ʜᴏɴᴇsᴛʟʏ ᴛᴏ ᴀᴄᴄᴇss ᴄᴏɴᴛᴇɴᴛ."
                        )

                    # Ensure backend verification status is checked server-side every time
                    db_session = await db.sessions.find_one({"session_id": session["session_id"]})
                    if not db_session:
                        db_session = session

                    if db_session.get('status') != 'verified':
                        return await message.reply_text(
                            "<b>❌ Verification Incomplete!</b>\n\n"
                            "You have not completed or passed backend verification. "
                            "Please complete the verification flow before returning to the bot."
                        )

                    # Check Access Limit (Session-based)
                    if not await db.check_session_access(session['session_id']):
                        return await message.reply_text("<b>❌ ᴀᴄᴄᴇss ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ!</b>\n\nPlease verify again to get a new session.")

                    updated_session = await db.decrement_access_count(session['session_id'])
                    if not updated_session:
                        return await message.reply_text("<b>❌ sᴇssɪᴏɴ ᴇʀʀᴏʀ!</b>\n\nPlease verify again.")

                    # Update global verification status only on first use of THIS session
                    if updated_session.get('usage_count') == 1:
                        count = await db.get_verify_count(user_id)
                        await db.set_verify_count(user_id, count + 1)

                        # set_user_verified also initializes global access_credits
                        await db.set_user_verified(user_id, bot_username=bot_uname, token=session['session_id'])
                        await db.set_verified_worker(client.username, user_id)

                        limit = bot_settings.get('access_limit', 1)
                        limit_text = "unlimited" if limit == -1 else f"{limit}"
                        window = bot_settings.get('verify_window', 86400)
                        window_text = get_exp_time(window)

                        # Show Success Message
                        await message.reply_text(
                            "<b>━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            "🌟 ˹ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ sᴜᴄᴄᴇssꜰᴜʟ ˼ 🌟\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
                            f"<blockquote>🎉 <b>ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs!</b> ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴠᴇʀɪꜰɪᴇᴅ.\n\n"
                            f"⚡ <b>sᴛᴀᴛᴜs:</b> ᴀᴄᴛɪᴠᴇ ✅\n"
                            f"🔑 <b>ᴀᴄᴄᴇssᴇs ʟᴇꜰᴛ:</b> <code>{limit_text}</code> 🎯\n"
                            f"⏳ <b>ᴠᴀʟɪᴅɪᴛʏ:</b> <code>{window_text}</code> 🕒\n"
                            f"👤 <b>ᴜsᴇʀ:</b> {message.from_user.mention}</blockquote>\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━",
                            message_effect_id=5104841245755180586 # 🔥
                        )

                        # Send verified log to all configured destinations
                        traced_link = session.get('original_shortlink') or session.get('traced_url') or f"https://t.me/{client.username}?start=verify_{session['session_id']}"
                        asyncio.create_task(send_verify_log("verified", user_id, message.from_user, session['session_id'], traced_link, client.username))

                        # Immediately consume 1 credit for the current delivery
                        await db.decrement_user_credits(user_id, bot_username=bot_uname)
                        # No return here, deliver the files immediately!
                    else:
                        # Subsequent uses of same session must also honor global credits
                        if not await db.is_user_verified(user_id, bot_username=bot_uname):
                            return await message.reply_text("<b>❌ ᴀᴄᴄᴇss ᴇxᴘɪʀᴇᴅ!</b>\n\nYour global access credits have finished. Please verify again.")
                        await db.decrement_user_credits(user_id, bot_username=bot_uname)

                    if session['content_id'] != "verify_general":
                        await send_files(client, user_id, session['content_id'])

                    # Log usage
                    remaining = updated_session.get('access_count', 0)
                    await db.log_event(user_id, "SESSION_USED", f"Session {session['session_id']} used. Remaining: {remaining if remaining != -1 else 'Unlimited'}")
                else:
                    await message.reply_text(f"<b>❌ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ!</b>\n\nSecurity Error: Session invalid, expired, or belongs to another user.\n\n<code>DEBUG: {token}</code>")
                return


            # 2. REFERRAL LINK
            if basic.startswith("ref_"):
                referrer_id = basic.replace("ref_", "")
                if await db.add_referral(referrer_id, user_id):
                    await message.reply_text("<b>✨ ʀᴇꜰᴇʀʀᴀʟ ᴀᴄᴄᴇᴘᴛᴇᴅ!</b>\n\nComplete any verification to reward your referrer.")
                else:
                    await message.reply_text("<b>⚠️ ʀᴇꜰᴇʀʀᴀʟ ɪɢɴᴏʀᴇᴅ (Self-referral or already referred).</b>")
                return

            # 3. PREMIUM CONTENT FLOW (Order strictly follows the user's specification)
            # Find if the Shortener feature is active for this bot instance
            settings = await db.get_settings(bot_username=client.username)
            shortener_active = settings.get('shortener_active', True)
            verification_enabled = settings.get('verification_enabled', True)

            # Bypass verification if user is premium or admin (if bypass allowed) or if shortener/verification is disabled
            is_premium = await is_premium_user(user_id)
            is_admin = await db.admin_exist(user_id) or user_id == OWNER_ID
            shorten_admins = settings.get('shorten_admins', True)
            bypass_verification = (not shortener_active) or (not verification_enabled) or is_premium or (is_admin and not shorten_admins)

            # Check if there is any recently completed (verified) session in the database for this user
            bot_uname_filter = {"$regex": f"^{client.username}$", "$options": "i"} if client.username else {"$in": [None, ""]}
            latest_verified_session = await db.sessions.find_one({
                "user_id": str(user_id),
                "bot_username": bot_uname_filter,
                "content_id": basic,
                "status": "verified"
            })
            if not latest_verified_session:
                latest_verified_session = await db.sessions.find_one({
                    "user_id": str(user_id),
                    "bot_username": bot_uname_filter,
                    "content_id": "verify_general",
                    "status": "verified"
                })

            if latest_verified_session:
                await db.set_user_verified(user_id, bot_username=client.username, token=latest_verified_session['session_id'])
                await db.set_verified_worker(client.username, user_id)
                await db.decrement_user_credits(user_id, bot_username=client.username)
                await db.mark_session_used(latest_verified_session['session_id'])

            # Check FSUB status first
            access_status = await check_user_access(client, user_id)
            if access_status in ["fsub", "bot"]:
                # Subscription missing: show required join details directly as a new message instantly
                status_list = await get_sub_status(client, user_id)
                missing_fsub = any(not s['is_joined'] for s in status_list)

                fsub_bots = await db.get_fsub_bots()
                missing_bots = False
                for bot in fsub_bots:
                    if not await is_bot_started(user_id, bot['token']):
                        missing_bots = True
                        break

                if missing_fsub and missing_bots:
                    warning_msg = "⚠️ <b>Access Denied</b>\n\nPlease join our channels and start the required bots below to unlock your files."
                elif missing_fsub:
                    warning_msg = "⚠️ <b>Access Denied</b>\n\nPlease join all required channels/groups below to continue."
                elif missing_bots:
                    warning_msg = "⚠️ <b>Access Denied</b>\n\nPlease start the required bots below to unlock content."
                else:
                    warning_msg = "⚠️ <b>Access Denied</b>\n\nPlease complete the verification to proceed."

                reply_markup = await get_fsub_buttons(client, user_id, basic)

                caption = (
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "✨ ˹ ʜᴇʏ sᴀᴍᴀ × ᴀɴɪᴢᴏɴᴇꜰʟɪx ˼ ✨\n\n"
                    "🎉 <b>˹ ᴀɴɪᴍᴇ ꜰɪʟᴇs ᴀʀᴇ ʀᴇᴀᴅʏ ˼ !!</b>\n\n"
                    f"{warning_msg}\n\n"
                    "━━━━━━━━━━━━━━━━━━━"
                )
                await message.reply(text=caption, reply_markup=reply_markup)
                return

            if bypass_verification:
                # Shortener is Disabled / Bypassed -> Deliver content immediately
                return await send_files(client, user_id, basic)

            # Shortener is Enabled -> Check Verification
            is_verified = await db.is_user_verified(user_id, bot_username=client.username)
            if is_verified:
                # Already Verified -> Deliver content immediately
                await db.decrement_user_credits(user_id, bot_username=client.username)
                return await send_files(client, user_id, basic)

            # Not Verified -> Show verification session and link instantly
            await short_url(client, message, basic)
            return

        except Exception as e:
            print(f"Error processing start payload: {e}")
            try:
                await message.reply_text("<b>❌ Error!</b>\n\nSomething went wrong while processing your request. Please try again.")
            except: pass
            return

    # Handle normal message flow
    else:
        settings = await db.get_settings()
        if not settings.get('core_features', True) and user_id != OWNER_ID:
            return await message.reply_text("<b>⚠️ Bot is under maintenance. Please try again later.</b>")

        # Premium Start UI Redesign
        is_clone = getattr(client, "name", "Bot") != "Bot"
        clone_data = await db.get_clone(client.username) if is_clone else None

        bot_name = clone_data.get('name', settings.get('bot_name', BOT_NAME)) if clone_data else settings.get('bot_name', BOT_NAME)
        community_url = clone_data.get('community_link', "https://t.me/AniZoneFlix") if clone_data else "https://t.me/AniZoneFlix"
        banners = await get_banners(client)

        buttons = [
            [InlineKeyboardButton(f"📢 {bot_name}: JOIN OUR COMMUNITY", url=community_url, style="primary", icon_custom_emoji_id=5440389890787281213)],
            [
                InlineKeyboardButton("⚙️ ˹ ᴀʙᴏᴜᴛ ˼", callback_data="about", style="primary", icon_custom_emoji_id=5440389890787281213),
                InlineKeyboardButton("✨ ˹ ʜᴇʟᴘ ˼", callback_data="help", style="primary", icon_custom_emoji_id=5440389890787281213)
            ],
            [
                InlineKeyboardButton("💎 ˹ ᴘʀᴇᴍɪᴜᴍ ˼", callback_data="premium", style="success", icon_custom_emoji_id=5355142851615283756),
                InlineKeyboardButton("🤝 ˹ ʀᴇꜰᴇʀ ˼", callback_data="referral_info", style="primary", icon_custom_emoji_id=5440389890787281213)
            ]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        # Premium Welcome Message
        header = RichText.format_heading(f"Hey, {message.from_user.first_name}", level=2)
        body = f"💎 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴍᴏsᴛ ᴘᴏᴡᴇʀꜰᴜʟ ꜰɪʟᴇ sᴛᴏʀᴇ ᴇɴɢɪɴᴇ (<b>{bot_name}</b>).\nɪ ᴄᴀɴ sᴛᴏʀᴇ ᴀɴᴅ sʜᴀʀᴇ ꜰɪʟᴇs sᴇᴄᴜʀᴇʟʏ ᴡɪᴛʜ ᴜʟᴛʀᴀ-ꜰᴀsᴛ sᴘᴇᴇᴅ. 🚀"
        quote = RichText.format_quote("🛡️ ᴜɴʟᴏᴄᴋ ᴛʜᴇ ꜰᴜʟʟ ᴘᴏᴛᴇɴᴛɪᴀʟ ʙʏ ᴊᴏɪɴɪɴɢ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ʙᴇʟᴏᴡ.", expandable=False)
        caption = f"━━━━━━━━━━━━━━━━━━━\n{header}\n\n{body}\n\n{quote}\n━━━━━━━━━━━━━━━━━━━"

        photo = random.choice(banners) if banners else None
        await send_media(
            client=client,
            chat_id=message.chat.id,
            photo=photo,
            caption=caption,
            reply_markup=reply_markup,
            message_effect_id=5104841245755180586 # 🔥
        )
        return



#=====================================================================================##
# Don't Remove Credit @AniZoneFlix, @AniZoneFlix
# Ask Doubt on telegram @AniZoneFlix



async def not_joined(client: Client, message: Message):
    user_id = message.from_user.id
    payload = None
    if hasattr(message, 'command') and len(message.command) > 1:
        payload = message.command[1]

    # Determine what's missing for custom message
    status_list = await get_sub_status(client, user_id)
    missing_fsub = any(not s['is_joined'] for s in status_list)

    fsub_bots = await db.get_fsub_bots()
    missing_bots = False
    for bot in fsub_bots:
        if not await is_bot_started(user_id, bot['token']):
            missing_bots = True
            break

    if missing_fsub and missing_bots:
        warning_msg = "⚠️ **˹ ACᴄᴇss Dᴇɴɪᴇᴅ ˼**\n\nᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ʙᴏᴛs ʙᴇʟᴏᴡ ᴛᴏ ᴜɴʟᴏᴄᴋ ʏᴏᴜʀ ꜰɪʟᴇs."
    elif missing_fsub:
        warning_msg = "⚠️ **˹ ACᴄᴇss Dᴇɴɪᴇᴅ ˼**\n\nᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴀʟʟ ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟs/ɢʀᴏᴜᴘs ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ."
    elif missing_bots:
        warning_msg = "⚠️ **˹ ACᴄᴇss Dᴇɴɪᴇᴅ ˼**\n\nᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ʙᴏᴛs ʙᴇʟᴏᴡ ᴛᴏ ᴜɴʟᴏᴄᴋ ᴄᴏɴᴛᴇɴᴛ."
    else:
        warning_msg = "⚠️ **˹ ACᴄᴇss Dᴇɴɪᴇᴅ ˼**\n\nᴘʟᴇᴀsᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ᴛʜᴇ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ."

    reply_markup = await get_fsub_buttons(client, user_id, payload)

    caption = (
        "━━━━━━━━━━━━━━━━━━━\n"
        "✨ ˹ ʜᴇʏ sᴀᴍᴀ × ᴀɴɪᴢᴏɴᴇꜰʟɪx ˼ ✨\n\n"
        "🎉 <b>˹ ᴀɴɪᴍᴇ ꜰɪʟᴇs ᴀʀᴇ ʀᴇᴀᴅʏ ˼ !!</b>\n\n"
        f"{warning_msg}\n\n"
        "━━━━━━━━━━━━━━━━━━━"
    )

    await message.reply_text(
        text=caption,
        reply_markup=reply_markup
    )

#=====================================================================================##

@Client.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id  # Get user ID from the message

    # Get the premium status of the user
    status_message = await check_user_plan(user_id)

    # Send the response message to the user
    await message.reply(status_message)

#=====================================================================================##
# Command to add premium user
@Client.on_message(filters.command('addpremium') & filters.private & admin)
async def add_premium_user_command(client, msg):
    if len(msg.command) < 4:
        await msg.reply_text(
            "Usage: /addpremium <user_id1,user_id2,...> <time_value> <time_unit>\n\n"
            "Time Units:\n"
            "s - seconds\n"
            "m - minutes\n"
            "h - hours\n"
            "d - days\n"
            "y - years\n\n"
            "Examples:\n"
            "/addpremium 123456789 30 m → 30 minutes\n"
            "/addpremium 123456789,987654321 1 y → 1 year"
        )
        return

    try:
        user_ids = msg.command[1].split(",")
        time_value = int(msg.command[2])
        time_unit = msg.command[3].lower()

        report = ""
        for uid in user_ids:
            try:
                user_id = int(uid.strip())
                expiration_time = await add_premium(user_id, time_value, time_unit)
                report += f"✅ User `{user_id}` added. Expires: `{expiration_time}`\n"

                try:
                    await client.send_message(
                        chat_id=user_id,
                        text=f"🎉 Premium Activated!\n\nYou have received premium access for `{time_value} {time_unit}`.\nExpires on: `{expiration_time}`",
                    )
                except: pass
            except Exception as e:
                report += f"❌ Error for `{uid}`: {e}\n"

        await msg.reply_text(f"📊 **ᴘʀᴇᴍɪᴜᴍ ᴀᴅᴅ ʀᴇᴘᴏʀᴛ:**\n\n{report}")

    except ValueError:
        await msg.reply_text("❌ Invalid time value. Must be a number.")
    except Exception as e:
        await msg.reply_text(f"⚠️ An error occurred: `{str(e)}`")


# Command to remove premium user
@Client.on_message(filters.command('remove_premium') & filters.private & admin)
async def pre_remove_user(client: Client, msg: Message):
    if len(msg.command) < 2:
        await msg.reply_text("<b>Usage:</b> <code>/remove_premium id1,id2,...</code>")
        return

    user_ids = msg.command[1].split(",")
    report = ""
    for uid in user_ids:
        try:
            user_id = int(uid.strip())
            await remove_premium(user_id)
            report += f"✅ User `{user_id}` removed from premium.\n"
        except Exception as e:
            report += f"❌ Error for `{uid}`: {e}\n"

    await msg.reply_text(f"📊 **ᴘʀᴇᴍɪᴜᴍ ʀᴇᴍᴏᴠᴀʟ ʀᴇᴘᴏʀᴛ:**\n\n{report}")


# Command to list active premium users
@Client.on_message(filters.command('premium_users') & filters.private & admin)
async def list_premium_users_command(client, message):
    # Define IST timezone
    ist = timezone("Asia/Kolkata")

    # Retrieve all users from the collection
    premium_users_cursor = collection.find({})
    premium_user_list = ['Active Premium Users in database:']
    current_time = datetime.now(ist)  # Get current time in IST

    # Use async for to iterate over the async cursor
    async for user in premium_users_cursor:
        user_id = user["user_id"]
        expiration_timestamp = user["expiration_timestamp"]

        try:
            # Convert expiration_timestamp to a timezone-aware datetime object in IST
            expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)

            # Calculate remaining time
            remaining_time = expiration_time - current_time

            if remaining_time.total_seconds() <= 0:
                # Remove expired users from the database
                await collection.delete_one({"user_id": user_id})
                continue  # Skip to the next user if this one is expired

            # If not expired, retrieve user info
            user_info = await client.get_users(user_id)
            username = user_info.username if user_info.username else "No Username"
            first_name = user_info.first_name
            mention=user_info.mention

            # Calculate days, hours, minutes, seconds left
            days, hours, minutes, seconds = (
                remaining_time.days,
                remaining_time.seconds // 3600,
                (remaining_time.seconds // 60) % 60,
                remaining_time.seconds % 60,
            )
            expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"

            # Add user details to the list
            premium_user_list.append(
                f"UserID: <code>{user_id}</code>\n"
                f"User: @AniZoneFlix{username}\n"
                f"Name: {mention}\n"
                f"Expiry: {expiry_info}"
            )
        except Exception as e:
            premium_user_list.append(
                f"UserID: <code>{user_id}</code>\n"
                f"Error: Unable to fetch user details ({str(e)})"
            )

    if len(premium_user_list) == 1:  # No active users found
        await message.reply_text("I found 0 active premium users in my DB")
    else:
        await message.reply_text("\n\n".join(premium_user_list), parse_mode=None)


#=====================================================================================##



#=====================================================================================##

def parse_date_filter(arg):
    arg = arg.strip().replace("/", "-")
    parts = arg.split("-")
    if len(parts) == 3:
        try:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            return f"{day:02d}-{month:02d}-{year:04d}"
        except ValueError:
            pass
    return None

def format_time_ist(epoch):
    import pytz
    from datetime import datetime
    ist = pytz.timezone("Asia/Kolkata")
    dt = datetime.fromtimestamp(epoch, tz=ist)
    return dt.strftime("%I:%M %p")

async def get_verifications_for_date(date_str):
    import pytz
    from datetime import datetime
    ist = pytz.timezone("Asia/Kolkata")

    from collections import defaultdict
    grouped = defaultdict(list)

    # Parse date_str (DD-MM-YYYY)
    try:
        day, month, year = map(int, date_str.split("-"))
    except Exception:
        return grouped

    # 1. Fetch from verifications_history
    cursor = db.database["verifications_history"].find({"date_str": date_str})
    history_records = await cursor.to_list(length=None)
    for r in history_records:
        u_id = int(r["user_id"])
        grouped[u_id].append(r)

    # 2. Fetch from sessions (UTC created_at)
    try:
        start_ist = ist.localize(datetime(year, month, day, 0, 0, 0))
        end_ist = ist.localize(datetime(year, month, day, 23, 59, 59, 999999))
        start_utc = start_ist.astimezone(pytz.utc)
        end_utc = end_ist.astimezone(pytz.utc)

        session_cursor = db.sessions.find({
            "status": {"$in": ["verified", "used", "timer_started"]},
            "created_at": {"$gte": start_utc, "$lte": end_utc}
        })
        session_records = await session_cursor.to_list(length=None)
        for s in session_records:
            if not s.get("user_id"): continue
            try:
                u_id = int(s["user_id"])
            except ValueError:
                continue

            created_at_dt = s["created_at"]
            if created_at_dt.tzinfo is None:
                created_at_dt = pytz.utc.localize(created_at_dt)
            v_at = created_at_dt.timestamp()
            e_at = s.get("expiry", v_at + 86400)

            # Avoid duplicates with history
            exists = any(abs(r.get("verified_at", 0) - v_at) < 5.0 for r in grouped[u_id])
            if not exists:
                grouped[u_id].append({
                    "user_id": u_id,
                    "verified_at": v_at,
                    "expires_at": e_at,
                    "date_str": date_str
                })
    except Exception as ex:
        print(f"Error querying sessions in count: {ex}")

    # 3. Fetch from user_data (currently verified users with active sessions)
    user_cursor = db.user_data.find({
        "$or": [
            {"verified": True},
            {"bot_verifications": {"$exists": True}}
        ]
    })
    all_users = await user_cursor.to_list(length=None)

    for user in all_users:
        u_id = int(user["_id"])

        # Check global verification
        g_verified_at = user.get("verified_at", 0)
        if g_verified_at > 0:
            dt = datetime.fromtimestamp(g_verified_at, tz=ist)
            g_date = dt.strftime("%d-%m-%Y")
            if g_date == date_str:
                exists = any(abs(r.get("verified_at", 0) - g_verified_at) < 5.0 for r in grouped[u_id])
                if not exists:
                    u_count = await db.get_verify_count(u_id) or 1
                    grouped[u_id].append({
                        "user_id": u_id,
                        "verified_at": g_verified_at,
                        "expires_at": user.get("expires_at", g_verified_at + 86400),
                        "date_str": date_str,
                        "count_override": u_count
                    })

        # Check bot-specific/clone verifications
        bot_verifications = user.get("bot_verifications", {})
        if bot_verifications and isinstance(bot_verifications, dict):
            for bot_uname, b_ver in bot_verifications.items():
                b_verified_at = b_ver.get("verified_at", 0)
                if b_verified_at > 0:
                    dt = datetime.fromtimestamp(b_verified_at, tz=ist)
                    b_date = dt.strftime("%d-%m-%Y")
                    if b_date == date_str:
                        exists = any(abs(r.get("verified_at", 0) - b_verified_at) < 5.0 for r in grouped[u_id])
                        if not exists:
                            u_count = await db.get_verify_count(u_id) or 1
                            grouped[u_id].append({
                                "user_id": u_id,
                                "verified_at": b_verified_at,
                                "expires_at": b_ver.get("expires_at", b_verified_at + 86400),
                                "date_str": date_str,
                                "count_override": u_count
                            })

    # 4. Fallback for any user who has verify_count in sex_data but not in grouped, if date is today, include them
    ist_today = datetime.now(ist).strftime("%d-%m-%Y")
    if date_str == ist_today:
        sex_cursor = db.sex_data.find({"verify_count": {"$gt": 0}})
        all_sex = await sex_cursor.to_list(length=None)
        for sex in all_sex:
            u_id = int(sex["_id"])
            if u_id not in grouped:
                u_doc = await db.user_data.find_one({"_id": u_id})
                import time
                v_at = time.time()
                e_at = v_at + 86400
                if u_doc:
                    v_at = u_doc.get("verified_at", v_at)
                    e_at = u_doc.get("expires_at", e_at)
                grouped[u_id].append({
                    "user_id": u_id,
                    "verified_at": v_at,
                    "expires_at": e_at,
                    "date_str": date_str,
                    "count_override": sex["verify_count"]
                })

    return grouped

@Client.on_message(filters.command("count") & filters.private)
async def total_verify_count_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    is_admin = await db.admin_exist(user_id) or user_id == OWNER_ID

    args = message.command
    date_filter = None

    if len(args) > 1:
        if not is_admin:
            return await message.reply_text("❌ <b>Only admins can query verifications for specific dates.</b>")
        date_filter = parse_date_filter(args[1])
        if not date_filter:
            return await message.reply_text("❌ <b>Invalid date format! Use DD-MM-YYYY or DD/MM/YYYY.</b>")

    import pytz
    from datetime import datetime
    ist = pytz.timezone("Asia/Kolkata")

    if date_filter:
        target_date_str = date_filter
    else:
        target_date_str = datetime.now(ist).strftime("%d-%m-%Y")

    grouped_verifications = await get_verifications_for_date(target_date_str)

    if not is_admin:
        # Normal user flow: show only their own data for today
        user_records = grouped_verifications.get(user_id, [])
        if not user_records:
            return await message.reply_text("❌ <b>You have not been verified today.</b>")

        username_disp = f"@{message.from_user.username}" if message.from_user.username else "No Username"

        user_records.sort(key=lambda r: r["verified_at"])
        latest_record = user_records[-1]

        verified_time = format_time_ist(latest_record["verified_at"])
        expire_time = format_time_ist(latest_record["expires_at"])

        u_count = 0
        for r in user_records:
            if "count_override" in r:
                u_count = max(u_count, r["count_override"])
        if u_count == 0:
            u_count = len(user_records)

        response_text = (
            f"1. Username: {username_disp}\n"
            f"   User ID: {user_id}\n"
            f"   User Verified Time: {verified_time}\n"
            f"   Expire Time: {expire_time}\n"
            f"   Today How Many Times Verified: {u_count}"
        )
        return await message.reply_text(response_text)

    else:
        # Admin flow: show all users' records for the selected date
        if not grouped_verifications:
            if date_filter:
                return await message.reply_text(f"📋 No verifications found for {date_filter}.\n\nTotal Count for {date_filter}: 0")
            else:
                return await message.reply_text("📋 No verifications found for today.\n\nToday Total Count: 0")

        # Resolve all users in parallel to prevent blocking network calls
        u_ids = list(grouped_verifications.keys())

        async def resolve_user(uid):
            try:
                user_obj = await client.get_users(uid)
                return uid, user_obj
            except FloodWait as e:
                sleep_time = getattr(e, "value", getattr(e, "x", 5))
                await asyncio.sleep(sleep_time + 1)
                try:
                    user_obj = await client.get_users(uid)
                    return uid, user_obj
                except Exception:
                    return uid, None
            except Exception:
                return uid, None

        # Resolve users in small controlled batches to completely avoid Telegram mass limits and network congestion
        results = []
        chunk_size = 25
        for i in range(0, len(u_ids), chunk_size):
            chunk = u_ids[i:i+chunk_size]
            tasks = [resolve_user(uid) for uid in chunk]
            chunk_results = await asyncio.gather(*tasks)
            results.extend(chunk_results)
            await asyncio.sleep(0.3)

        resolved_users = {uid: user_obj for uid, user_obj in results if user_obj}

        user_entries = []
        total_count = 0
        pos = 1

        for u_id, records in grouped_verifications.items():
            user_obj = resolved_users.get(u_id)
            username_val = f"@{user_obj.username}" if (user_obj and user_obj.username) else "No Username"

            records.sort(key=lambda r: r["verified_at"])
            latest = records[-1]

            v_time = format_time_ist(latest["verified_at"])
            e_time = format_time_ist(latest["expires_at"])

            u_count = 0
            for r in records:
                if "count_override" in r:
                    u_count = max(u_count, r["count_override"])
            if u_count == 0:
                u_count = len(records)

            total_count += u_count

            count_label = "Verified Count" if date_filter else "Today How Many Times Verified"

            entry = (
                f"{pos}. Username: {username_val}\n"
                f"   User ID: {u_id}\n"
                f"   User Verified Time: {v_time}\n"
                f"   Expire Time: {e_time}\n"
                f"   {count_label}: {u_count}"
            )
            user_entries.append(entry)
            pos += 1

        if date_filter:
            end_line = f"Total Count for {date_filter}: {total_count}"
        else:
            end_line = f"Today Total Count: {total_count}"

        # Split output into multiple messages if it exceeds Telegram's 4096 character limit
        max_chars = 4000
        current_msg = ""
        messages_to_send = []

        for entry in user_entries:
            if len(current_msg) + len(entry) + 2 > max_chars:
                messages_to_send.append(current_msg.strip())
                current_msg = entry + "\n\n"
            else:
                current_msg += entry + "\n\n"

        if current_msg:
            if len(current_msg) + len(end_line) + 2 > max_chars:
                messages_to_send.append(current_msg.strip())
                messages_to_send.append(end_line)
            else:
                current_msg += end_line
                messages_to_send.append(current_msg.strip())
        else:
            messages_to_send.append(end_line)

        for msg_part in messages_to_send:
            await message.reply_text(msg_part)
        return

@Client.on_callback_query(filters.regex(r"^referral_info$"))
async def referral_info_cb(client, query: CallbackQuery):
    user_id = query.from_user.id
    settings = await db.get_settings()
    if not settings.get('referral_active'):
        return await query.answer("Referral system is currently disabled.", show_alert=True)

    stats = await db.get_referral_stats(user_id)
    web_url = settings.get('website_url', WEBSITE_URL).rstrip('/')
    ref_link = f"https://t.me/{client.username}?start=ref_{user_id}"

    text = (
        "🤝 <b>˹ ᴀɴɪᴢᴏɴᴇꜰʟɪx ʀᴇꜰᴇʀʀᴀʟ sʏsᴛᴇᴍ ˼</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "sʜᴀʀᴇ ʏᴏᴜʀ ʟɪɴᴋ ᴡɪᴛʜ ꜰʀɪᴇɴᴅs ᴛᴏ ᴇᴀʀɴ ʀᴇᴡᴀʀᴅs!\n\n"
        f"🔗 <b>ʏᴏᴜʀ ʟɪɴᴋ:</b>\n<code>{ref_link}</code>\n\n"
        f"👥 <b>ᴛᴏᴛᴀʟ ʀᴇꜰᴇʀʀᴀʟs:</b> <code>{stats['total']}</code>\n"
        f"💎 <b>sᴜᴄᴄᴇssꜰᴜʟ:</b> <code>{stats['success']}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    await query.message.edit_caption(
        caption=text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start", style="primary", icon_custom_emoji_id=5440389890787281213)]])
    )

@Client.on_message(filters.command('commands') & filters.private & admin)
async def bcmd(client: Client, message: Message):
    # Dynamic generation of commands
    commands = await client.get_bot_commands()
    if not commands:
        text = CMD_TXT # Fallback
    else:
        text = "📜 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs**\n\n"
        for cmd in commands:
            text += f"• `/{cmd.command}` - {cmd.description}\n"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data = "close", style="danger", icon_custom_emoji_id=5354968347094046619)]])
    await message.reply(text=text, reply_markup = reply_markup, quote= True)


@Client.on_message(filters.private & ~admin, group=-1)
async def access_control(client: Client, message: Message):
    user_id = message.from_user.id

    # 1. Access Check
    access_status = await check_user_access(client, user_id)

    if access_status == "banned":
        ban_data = await db.get_ban_user_data(user_id)
        reason = ban_data.get('reason', "Policy violations.") if ban_data else "Policy violations."
        await message.reply_text(
            "🚫 <b>˹ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ ˼</b>\n\n"
            f"<blockquote>ʀᴇᴀsᴏɴ: {reason}</blockquote>\n\n"
            "📩 <b>ꜰᴏʀ ᴜɴʙᴀɴ ᴄᴏɴᴛᴀᴄᴛ:</b>\n"
            "@ALONEKINGSTARBACK\n\n"
            "<i>ʀᴇᴊᴏɪɴ ᴀʟʟ ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟs/ɢʀᴏᴜᴘs ᴀɴᴅ ᴄᴏɴᴛᴀᴄᴛ ᴛʜᴇ ᴏᴡɴᴇʀ ꜰᴏʀ ʀᴇᴠɪᴇᴡ.</i>\n\n"
            "⚠️ ᴛʜɪs ᴀᴄᴛɪᴏɴ ɪs ᴀᴜᴛᴏᴍᴀᴛɪᴄ ᴀɴᴅ ᴛʀɪɢɢᴇʀᴇᴅ ɪᴍᴍᴇᴅɪᴀᴛᴇʟʏ ᴡʜᴇɴ ᴀ ᴠɪᴏʟᴀᴛɪᴏɴ ɪs ᴅᴇᴛᴇᴄᴛᴇᴅ.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🛡 ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ 🛡", url="https://t.me/ALONEKINGSTARBACK", style="primary", icon_custom_emoji_id=5440389890787281213)]]
            )
        )
        message.stop_propagation()

    # 2. Check for Subscription (Allow /start without block, it will handle it internally)
    if message.text and message.text.startswith("/start"):
        return

    if access_status in ["fsub", "bot"]:
        await not_joined(client, message)
        message.stop_propagation()
    elif access_status == "maintenance":
        await message.reply_text("<b>⚠️ Bot is under maintenance. Please try again later.</b>")
        message.stop_propagation()
