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
import sys
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from helper_func import InlineKeyboardButton, random_button_style
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from config import *
from helper_func import *
from database.database import *



#BAN-USER-SYSTEM
@Client.on_message(filters.command('ban') & filters.private & admin)
async def ban_user_cmd(client: Client, message: Message):
    pro = await message.reply("⏳ <b><i>˹ ᴘʀᴏᴄᴇssɪɴɢ ʙᴀɴ... ˼</i></b>", quote=True)
    banuser_ids = await db.get_ban_users()

    # Support both space and comma separation
    raw_users = message.text.split(maxsplit=1)[1:]
    if not raw_users:
        return await pro.edit(
            "⚠️ <b>˹ ᴍɪssɪɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ˼</b>\n\n"
            "ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴜsᴇʀ ɪᴅ(s) ᴛᴏ ᴇxᴇᴄᴜᴛᴇ ʙᴀɴ.\n\n"
            "📜 <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/ban [ɪᴅ1] [ɪᴅ2]</code>\n"
            "• <code>/ban [ɪᴅ1],[ɪᴅ2]</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔒 ᴄʟᴏsᴇ", callback_data="close", style="danger", icon_custom_emoji_id=5354968347094046619)]])
        )

    banusers = raw_users[0].replace(",", " ").split()

    report, success_count = "", 0
    for uid in banusers:
        try:
            uid_int = int(uid.strip())
        except:
            report += f"⚠️ Iɴᴠᴀʟɪᴅ ID: <code>{uid}</code>\n"
            continue

        if uid_int in await db.get_all_admins() or uid_int == OWNER_ID:
            report += f"⛔ Sᴋɪᴘᴘᴇᴅ ᴀᴅᴍɪɴ: <code>{uid_int}</code>\n"
            continue

        if uid_int in banuser_ids:
            report += f"⚠️ Aʟʀᴇᴀᴅʏ : <code>{uid_int}</code>\n"
            continue

        await db.add_ban_user(uid_int, reason="Banned by Administrator.")
        report += f"✅ Bᴀɴɴᴇᴅ: <code>{uid_int}</code>\n"
        success_count += 1

    await pro.edit(f"📊 **Bᴀɴ Rᴇᴘᴏʀᴛ:**\n\n{report}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close", style="danger", icon_custom_emoji_id=5354968347094046619)]]))

@Client.on_message(filters.command('unban') & filters.private & admin)
async def unban_user_cmd(client: Client, message: Message):
    pro = await message.reply("⏳ <b><i>˹ ᴘʀᴏᴄᴇssɪɴɢ ᴜɴʙᴀɴ... ˼</i></b>", quote=True)
    banuser_ids = await db.get_ban_users()

    raw_users = message.text.split(maxsplit=1)[1:]
    if not raw_users:
        return await pro.edit(
            "⚠️ <b>˹ ᴍɪssɪɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ˼</b>\n\n"
            "ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴜsᴇʀ ɪᴅ(s) ᴛᴏ ʀᴇᴠᴏᴋᴇ ʙᴀɴ.\n\n"
            "📜 <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/unban [ɪᴅ1],[ɪᴅ2]</code>\n"
            "• <code>/unban all</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔒 ᴄʟᴏsᴇ", callback_data="close", style="danger", icon_custom_emoji_id=5354968347094046619)]])
        )

    if raw_users[0].lower() == "all":
        if not banuser_ids:
            return await pro.edit("<b>✨ ˹ ʙᴀɴ ʟɪsᴛ ᴇᴍᴘᴛʏ ˼</b>")
        for uid in banuser_ids:
            await db.del_ban_user(uid)
        return await pro.edit(f"<b>🚫 Cʟᴇᴀʀᴇᴅ Bᴀɴ Lɪsᴛ ({len(banuser_ids)} users).</b>")

    banusers = raw_users[0].replace(",", " ").split()
    report = ""
    for uid in banusers:
        try:
            uid_int = int(uid.strip())
            if uid_int in banuser_ids:
                await db.del_ban_user(uid_int)
                report += f"✅ Uɴʙᴀɴɴᴇᴅ: <code>{uid_int}</code>\n"
            else:
                report += f"⚠️ Nᴏᴛ ɪɴ ʙᴀɴ ʟɪsᴛ: <code>{uid_int}</code>\n"
        except:
            report += f"⚠️ Iɴᴠᴀʟɪᴅ ID: <code>{uid}</code>\n"

    await pro.edit(f"📊 **Uɴʙᴀɴ Rᴇᴘᴏʀᴛ:**\n\n{report}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close", style="danger", icon_custom_emoji_id=5354968347094046619)]]))

@Client.on_message(filters.command('banlist') & filters.private & admin)
async def ban_list_cmd(client: Client, message: Message):
    pro = await message.reply("⏳ <b><i>˹ ꜰᴇᴛᴄʜɪɴɢ ʙᴀɴ ʟɪsᴛ... ˼</i></b>", quote=True)
    banuser_ids = await db.get_ban_users()

    if not banuser_ids:
        return await pro.edit("✨ <b>˹ ʙᴀɴ ʟɪsᴛ ᴇᴍᴘᴛʏ ˼</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔒 ᴄʟᴏsᴇ", callback_data="close", style="danger", icon_custom_emoji_id=5354968347094046619)]]))

    result = "🚫 <b>˹ ʙᴀɴɴᴇᴅ ᴜsᴇʀs ˼</b>\n\n"
    for uid in banuser_ids:
        await message.reply_chat_action(ChatAction.TYPING)
        try:
            user = await client.get_users(uid)
            user_link = f'<a href="tg://user?id={uid}">{user.first_name}</a>'
            result += f"• {user_link} — <code>{uid}</code>\n"
        except:
            result += f"• <code>{uid}</code> — <i>Could not fetch name</i>\n"

    await pro.edit(result, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close", style="danger", icon_custom_emoji_id=5354968347094046619)]]))

@Client.on_message(filters.command('banned_users') & filters.private & admin)
async def banned_users_list_cmd(client: Client, message: Message):
    pro = await message.reply("⏳ <b><i>˹ ꜰᴇᴛᴄʜɪɴɢ ʙᴀɴ ᴅᴀᴛᴀ... ˼</i></b>", quote=True)
    banned_users = await db.get_all_banned_users()

    if not banned_users:
        return await pro.edit("✨ <b>˹ ʙᴀɴ ʟɪsᴛ ᴇᴍᴘᴛʏ ˼</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔒 ᴄʟᴏsᴇ", callback_data="close", style="danger", icon_custom_emoji_id=5354968347094046619)]]))

    result = "🚫 <b>˹ ʙᴀɴɴᴇᴅ ᴜsᴇʀs ᴅᴀᴛᴀ ˼</b>\n\n"
    for i, user_data in enumerate(banned_users, 1):
        uid = user_data['_id']
        reason = user_data.get('reason', 'No Reason Provided')
        username = "N/A"
        try:
            user = await client.get_users(uid)
            username = f"@{user.username}" if user.username else user.first_name
        except:
            pass

        result += f"{i}. <b>USERNAME:</b> {username}\n"
        result += f"   <b>USER ID :</b> <code>{uid}</code>\n"
        result += f"   <b>REASON:</b> <code>{reason}</code>\n\n"

        if len(result) > 3800:
            await message.reply(result, disable_web_page_preview=True)
            result = ""

    if result:
        await pro.edit(result, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close", style="danger", icon_custom_emoji_id=5354968347094046619)]]))
    else:
        await pro.delete()

@Client.on_message(filters.command('auto_ban') & filters.private & admin)
async def toggle_auto_ban(client: Client, message: Message):
    settings = await db.get_settings()

    if len(message.command) < 2:
        status = "ON" if settings.get('auto_ban', True) else "OFF"
        return await message.reply(f"🛡️ <b>Auto-Ban Status:</b> <code>{status}</code>\n\nUsage: <code>/auto_ban on/off</code>")

    choice = message.command[1].lower()
    if choice == "on":
        await db.update_setting("auto_ban", True)
        await message.reply("✅ <b>Auto-Ban has been ENABLED.</b> Users leaving FSUB channels will be banned.")
    elif choice == "off":
        await db.update_setting("auto_ban", False)
        await message.reply("⚠️ <b>Auto-Ban has been DISABLED.</b>")
    else:
        await message.reply("❌ Invalid choice. Use 'on' or 'off'.")
