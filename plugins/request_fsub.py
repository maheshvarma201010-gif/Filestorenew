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
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus, ChatType
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, ChatMemberUpdated, ChatPermissions
from helper_func import InlineKeyboardButton, random_button_style
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, InviteHashEmpty, ChatAdminRequired, PeerIdInvalid, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from config import *
from helper_func import *
from database.database import *

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

#Request force sub mode commad,,,,,,
@Client.on_message(filters.command('fsub_mode') & filters.private & admin)
async def change_force_sub_mode(client: Client, message: Message):
    temp = await message.reply("⏳ <b><i>˹ ᴘʀᴏᴄᴇssɪɴɢ... ˼</i></b>", quote=True)
    channels = await db.show_channels()

    if not channels:
        return await temp.edit("❌ <b>˹ ɴᴏ ᴄʜᴀɴɴᴇʟs ꜰᴏᴜɴᴅ ˼</b>")

    buttons = []
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            mode = await db.get_channel_mode(ch_id)
            status = "🟢" if mode == "on" else "🔴"
            title = f"{status} {chat.title}"
            buttons.append([InlineKeyboardButton(title, callback_data=f"rfs_ch_{ch_id}", style="primary")])
        except:
            buttons.append([InlineKeyboardButton(f"⚠️ {ch_id} (ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ)", callback_data=f"rfs_ch_{ch_id}", style="primary")])

    buttons.append([InlineKeyboardButton("🔒 ᴄʟᴏsᴇ", callback_data="close", style="danger")])

    await temp.edit(
        "⚡ <b>˹ ᴛᴏɢɢʟᴇ ꜰᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ ˼</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

# This handler captures membership updates (like when a user leaves, banned)
@Client.on_chat_member_updated()
async def handle_Chatmembers(client: Client, chat_member_updated: ChatMemberUpdated):
    chat_id = chat_member_updated.chat.id

    # Check if the chat is one of our FSUB channels
    channels = await db.show_channels()
    if chat_id not in channels:
        return

    old_member = chat_member_updated.old_chat_member
    new_member = chat_member_updated.new_chat_member

    if not old_member or not new_member:
        return

    user_id = new_member.user.id

    # Detect if user left or was removed
    if old_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and \
       new_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED, ChatMemberStatus.BANNED]:

        # Auto Ban Removed. We only cleanup request list if they leave.
        if await db.req_user_exist(chat_id, user_id):
            await db.del_req_user(chat_id, user_id)


# This handler will capture any join request to the channel/group where the bot is an admin
@Client.on_chat_join_request()
async def handle_join_request(client: Client, chat_join_request):
    chat_id = chat_join_request.chat.id
    user_id = chat_join_request.from_user.id

    #print(f"[JOIN REQUEST] User {user_id} sent join request to {chat_id}")

    # Print the result of db.reqChannel_exist to check if the channel exists
    channel_exists = await db.reqChannel_exist(chat_id)
    #print(f"Channel {chat_id} exists in the database: {channel_exists}")

    if channel_exists:
        if not await db.req_user_exist(chat_id, user_id):
            await db.req_user(chat_id, user_id)
            #print(f"Added user {user_id} to request list for {chat_id}")

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

# Add channel
@Client.on_message(filters.command('addchnl') & filters.private & admin)
async def add_force_sub(client: Client, message: Message):
    temp = await message.reply("⏳ <b><i>˹ ᴘʀᴏᴄᴇssɪɴɢ... ˼</i></b>", quote=True)
    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        return await temp.edit(
            "⚠️ <b>˹ ᴍɪssɪɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ˼</b>\n\nᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴄʜᴀɴɴᴇʟ ɪᴅ(s).\n\n📜 <b>ᴜsᴀɢᴇ:</b>\n<code>/addchnl -100xxxx,-100yyyy</code>"
        )

    ids = args[1].split(",")
    report = ""
    for raw_id in ids:
        try:
            chat_id = int(raw_id.strip())
            all_chats = await db.show_channels()
            if chat_id in [c if isinstance(c, int) else c[0] for c in all_chats]:
                report += f"⚠️ `{chat_id}`: Already exists.\n"
                continue

            chat = await client.get_chat(chat_id)
            bot_member = await client.get_chat_member(chat.id, "me")
            if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                report += f"❌ `{chat_id}`: Bot not admin.\n"
                continue

            await db.add_channel(chat_id)
            report += f"✅ `{chat_id}`: Added ({chat.title})\n"
        except Exception as e:
            report += f"❌ `{raw_id}`: {e}\n"

    await temp.edit(f"📊 **ᴄʜᴀɴɴᴇʟ ᴀᴅᴅ ʀᴇᴘᴏʀᴛ:**\n\n{report}")
        


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

# Delete channel
@Client.on_message(filters.command('delchnl') & filters.private & admin)
async def del_force_sub(client: Client, message: Message):
    temp = await message.reply("⏳ <b><i>˹ ᴘʀᴏᴄᴇssɪɴɢ... ˼</i></b>", quote=True)
    args = message.text.split(maxsplit=1)
    all_channels = await db.show_channels()

    if len(args) != 2:
        return await temp.edit("⚠️ <b>˹ ᴍɪssɪɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ˼</b>\n\n📜 <b>ᴜsᴀɢᴇ:</b> <code>/delchnl ɪᴅ1,ɪᴅ2 ᴏʀ ᴀʟʟ</code>")

    if args[1].lower() == "all":
        if not all_channels:
            return await temp.edit("❌ <b>˹ ɴᴏ ᴄʜᴀɴɴᴇʟs ꜰᴏᴜɴᴅ ˼</b>")
        for ch_id in all_channels:
            await db.rem_channel(ch_id)
        return await temp.edit("<b>✅ All force-sub channels have been removed.</b>")

    ids = args[1].split(",")
    report = ""
    for raw_id in ids:
        try:
            ch_id = int(raw_id.strip())
            if ch_id in all_channels:
                await db.rem_channel(ch_id)
                report += f"✅ `{ch_id}`: Removed.\n"
            else:
                report += f"⚠️ `{ch_id}`: Not in list.\n"
        except Exception as e:
            report += f"❌ `{raw_id}`: {e}\n"

    await temp.edit(f"📊 **ᴄʜᴀɴɴᴇʟ ʀᴇᴍᴏᴠᴀʟ ʀᴇᴘᴏʀᴛ:**\n\n{report}")

# View all channels
@Client.on_message(filters.command('listchnl') & filters.private & admin)
async def list_force_sub_channels(client: Client, message: Message):
    temp = await message.reply("⏳ <b><i>˹ ꜰᴇᴛᴄʜɪɴɢ ᴄʜᴀɴɴᴇʟs... ˼</i></b>", quote=True)
    channels = await db.show_channels()

    if not channels:
        return await temp.edit("❌ <b>˹ ɴᴏ ᴄʜᴀɴɴᴇʟs ꜰᴏᴜɴᴅ ˼</b>")

    result = "⚡ <b>˹ ꜰᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟs ˼</b>\n\n"
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            link = chat.invite_link or await client.export_chat_invite_link(chat.id)
            result += f"<b>•</b> <a href='{link}'>{chat.title}</a> [<code>{ch_id}</code>]\n"
        except Exception:
            result += f"<b>•</b> <code>{ch_id}</code> — <i>Unavailable</i>\n"

    await temp.edit(result, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close ✖️", callback_data="close", style="danger")]]))

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


@Client.on_message(filters.command("delreq") & admin & filters.private)
async def del_req(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Usᴀɢᴇ: `/delreq <channel_id>`", quote=True)

    try:
        channel_id = int(message.command[1])
    except ValueError:
        return await message.reply("❌ Iɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ID.", quote=True)

    # Get channel request data
    channel_data = await db.rqst_fsub_Channel_data.find_one({'_id': channel_id})
    if not channel_data:
        return await message.reply("ℹ️ Nᴏ ʀᴇǫᴜᴇsᴛ ᴄʜᴀɴɴᴇʟ ғᴏᴜɴᴅ ғᴏʀ ᴛʜɪs ᴄʜᴀɴɴᴇʟ.", quote=True)

    user_ids = channel_data.get("user_ids", [])
    if not user_ids:
        return await message.reply("✅ Nᴏ ᴜsᴇʀs ᴛᴏ ᴘʀᴏᴄᴇss.", quote=True)

    removed = 0
    skipped = 0
    left_users = 0

    for user_id in user_ids:
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER
            ):
                skipped += 1  # Still a participant, and in req list
                continue
            else:
                await db.del_req_user(channel_id, user_id)
                left_users += 1
        except UserNotParticipant:
            await db.del_req_user(channel_id, user_id)
            left_users += 1
        except Exception as e:
            print(f"[!] Error checking user {user_id}: {e}")
            skipped += 1

    for user_id in user_ids:
        if not await db.req_user_exist(channel_id, user_id):
            await db.del_req_user(channel_id, user_id)
            removed += 1

    return await message.reply(
        f"✅ Cʟᴇᴀɴᴜᴘ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ғᴏʀ ᴄʜᴀɴɴᴇʟ `{channel_id}`\n\n"
        f"👤 Rᴇᴍᴏᴠᴇᴅ ᴜsᴇʀs ɴᴏᴛ ɪɴ ᴄʜᴀɴɴᴇʟ: `{left_users}`\n"
        f"🗑️ Rᴇᴍᴏᴠᴇᴅ ʟᴇғᴛᴏᴠᴇʀ ɴᴏɴ-ʀᴇǫᴜᴇsᴛ ᴜsᴇʀs: `{removed}`\n"
        f"✅ Sᴛɪʟʟ ᴍᴇᴍʙᴇʀs: `{skipped}`",
        quote=True
    )
