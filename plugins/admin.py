import asyncio
import os
import random
import sys
import time
import aiohttp
import json
from helper_func import admin
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus, ChatType
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, ChatMemberUpdated, ChatPermissions
from helper_func import InlineKeyboardButton, random_button_style, ButtonStyle
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, InviteHashEmpty, ChatAdminRequired, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from config import *
from helper_func import *
from database.database import *
from helper_func import get_sub_status



# Commands for adding admins
@Client.on_message(filters.command('add_admin') & filters.private & admin)
async def add_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>˹ ᴘʀᴏᴄᴇssɪɴɢ... ˼</i></b>", quote=True)
    admin_ids = await db.get_all_admins()
    raw_admins = message.text.split(maxsplit=1)[1:]

    if not raw_admins:
        return await pro.edit(
            "⚠️ <b>˹ ᴍɪssɪɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ˼</b>\n\n"
            "ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴜsᴇʀ ɪᴅ(s) ᴛᴏ ɢʀᴀɴᴛ ᴀᴅᴍɪɴ ᴘʀɪᴠɪʟᴇɢᴇs.\n\n"
            "📜 <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/add_admin [ɪᴅ1] [ɪᴅ2]</code>\n"
            "• <code>/add_admin [ɪᴅ1],[ɪᴅ2]</code>"
        )

    admins = raw_admins[0].replace(",", " ").split()
    report = ""
    for aid in admins:
        try:
            id = int(aid.strip())
            if id in admin_ids:
                report += f"⚠️ `{id}`: Already admin.\n"
                continue
            await db.add_admin(id)
            await db.log_event(message.from_user.id, "ADMIN_ADDED", f"Added user {id} as admin.")
            report += f"✅ `{id}`: Added.\n"
        except:
            report += f"❌ `{aid}`: Invalid ID.\n"

    await pro.edit(f"📊 **ᴀᴅᴍɪɴ ᴀᴅᴅ ʀᴇᴘᴏʀᴛ:**\n\n{report}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close", style=ButtonStyle.DANGER)]]))

@Client.on_message(filters.command('deladmin') & filters.private & admin)
async def delete_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>˹ ᴘʀᴏᴄᴇssɪɴɢ... ˼</i></b>", quote=True)
    admin_ids = await db.get_all_admins()
    raw_admins = message.text.split(maxsplit=1)[1:]

    if not raw_admins:
        return await pro.edit(
            "⚠️ <b>˹ ᴍɪssɪɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ˼</b>\n\n"
            "ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴠᴀʟɪᴅ ᴀᴅᴍɪɴ ɪᴅ(s) ᴛᴏ ʀᴇᴠᴏᴋᴇ ᴀᴄᴄᴇss.\n\n"
            "📜 <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/deladmin [ɪᴅ1],[ɪᴅ2]</code>\n"
            "• <code>/deladmin all</code>"
        )

    if raw_admins[0].lower() == "all":
        for aid in admin_ids:
            await db.del_admin(aid)
        return await pro.edit(f"✅ **Cleared all admins ({len(admin_ids)}).**")

    admins = raw_admins[0].replace(",", " ").split()
    report = ""
    for aid in admins:
        try:
            id = int(aid.strip())
            if id in admin_ids:
                await db.del_admin(id)
                await db.log_event(message.from_user.id, "ADMIN_REMOVED", f"Removed user {id} from admins.")
                report += f"✅ `{id}`: Removed.\n"
            else:
                report += f"⚠️ `{id}`: Not an admin.\n"
        except:
            report += f"❌ `{aid}`: Invalid ID.\n"

    await pro.edit(f"📊 **ᴀᴅᴍɪɴ ʀᴇᴍᴏᴠᴀʟ ʀᴇᴘᴏʀᴛ:**\n\n{report}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close", style=ButtonStyle.DANGER)]]))


@Client.on_message(filters.command('admins') & filters.private & admin)
async def get_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    admin_ids = await db.get_all_admins()

    if not admin_ids:
        admin_list = "<b><blockquote>❌ No admins found.</blockquote></b>"
    else:
        admin_list = "\n".join(f"<b><blockquote>ID: <code>{id}</code></blockquote></b>" for id in admin_ids)

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close", style=ButtonStyle.DANGER)]])
    await pro.edit(f"<b>⚡ Current Admin List:</b>\n\n{admin_list}", reply_markup=reply_markup)

@Client.on_message(filters.command('stats') & filters.private & admin)
async def stats(client: Client, message: Message):
    from datetime import datetime
    import pytz
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    delta = now - client.uptime
    uptime = get_readable_time(delta.total_seconds())
    await message.reply(BOT_STATS_TEXT.format(uptime=uptime), quote=True)

@Client.on_message(filters.command('users') & filters.private & admin)
async def get_users(client: Client, message: Message):
    msg = await message.reply("<b>🔍 Fᴇᴛᴄʜɪɴɢ Usᴇʀ Sᴛᴀᴛɪsᴛɪᴄs...</b>", quote=True)
    users = await db.full_userbase()
    await msg.edit(f"<b>📊 Tᴏᴛᴀʟ Usᴇʀs:</b> <code>{len(users)}</code>")


@Client.on_message(filters.command('restart') & filters.private & admin)
async def restart_bot(client: Client, message: Message):
    try:
        ask = await client.ask(
            message.chat.id,
            "<b>🔄 Are you sure you want to restart the bot?</b>\n\nReply <code>yes</code> to confirm or <code>/cancel</code> to abort.",
            filters=filters.text,
            timeout=60
        )
        if ask.text.lower().strip() not in ["yes", "y", "confirm"]:
            await ask.reply("❌ <b>Restart Cancelled.</b>")
            return
    except asyncio.TimeoutError:
        await message.reply("⏰ <b>Restart Prompt Timed Out.</b>")
        return

    msg = await message.reply("<b>🔄 ˹ ʀᴇsᴛᴀʀᴛɪɴɢ sʏsᴛᴇᴍ... ˼</b>")

    # Log the restart event
    await db.log_event(message.from_user.id, "SYSTEM_RESTART", "Bot restart initiated by admin.")

    await asyncio.sleep(2)
    await msg.edit("<b>✅ Bot restarted successfully.</b>")

    # Using python -m main to ensure all modules are reloaded correctly
    # This completely replaces the current process, reloading everything.
    os.execl(sys.executable, sys.executable, "-m", "main")

@Client.on_message(filters.command('access_limit') & filters.private & admin)
async def set_access_limit(client: Client, message: Message):
    if len(message.command) < 2:
        settings = await db.get_settings(bot_username=client.username)
        current_limit = settings.get('access_limit', 1)
        return await message.reply_text(
            f"<b>🔢 ˹ ᴄᴜʀʀᴇɴᴛ ᴀᴄᴄᴇss ʟɪᴍɪᴛ ˼ :</b> <code>{current_limit}</code>\n\n"
            "✨ <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/access_limit [ɴᴜᴍʙᴇʀ]</code> — sᴇᴛ ʜᴏᴡ ᴍᴀɴʏ ᴛɪᴍᴇs ᴀ ᴜsᴇʀ ᴄᴀɴ ᴀᴄᴄᴇss ᴄᴏɴᴛᴇɴᴛ ᴀꜰᴛᴇʀ ᴏɴᴇ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ. 🚀"
        )

    try:
        val = int(message.command[1])
        if val < -1:
            return await message.reply_text("❌ <b>ɪɴᴠᴀʟɪᴅ ʟɪᴍɪᴛ!</b> ᴜsᴇ -1 ꜰᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴏʀ ᴀ ᴘᴏsɪᴛɪᴠᴇ ɴᴜᴍʙᴇʀ. 🛡️")

        await db.update_setting('access_limit', val, bot_username=client.username)
        await message.reply_text(f"✅ <b>ᴀᴄᴄᴇss ʟɪᴍɪᴛ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ:</b> <code>{val if val != -1 else 'ᴜɴʟɪᴍɪᴛᴇᴅ'}</code> 💎")
        await db.log_event(message.from_user.id, "ACCESS_LIMIT_UPDATED", f"Set access limit to {val}")
    except ValueError:
        await message.reply_text("❌ <b>ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ.</b> ⚠️")

@Client.on_message(filters.command('validity') & filters.private & admin)
async def set_validity(client: Client, message: Message):
    if len(message.command) < 2:
        settings = await db.get_settings(bot_username=client.username)
        current_val = settings.get('verify_window', 86400)
        return await message.reply_text(
            f"<b>🕒 ˹ ᴄᴜʀʀᴇɴᴛ ᴠᴀʟɪᴅɪᴛʏ ˼ :</b> <code>{current_val} sᴇᴄᴏɴᴅs</code>\n\n"
            "✨ <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/validity [sᴇᴄᴏɴᴅs]</code> — sᴇᴛ ʜᴏᴡ ʟᴏɴɢ ᴀ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ sᴇssɪᴏɴ ʀᴇᴍᴀɪɴs ᴠᴀʟɪᴅ. ⏳\n"
            "• <i>ᴇxᴀᴍᴘʟᴇ: /validity 3600 (1 ʜᴏᴜʀ)</i> 🕒"
        )

    try:
        val = int(message.command[1])
        if val < 60:
            return await message.reply_text("❌ <b>ᴛᴏᴏ sʜᴏʀᴛ!</b> ᴠᴀʟɪᴅɪᴛʏ ᴍᴜsᴛ ʙᴇ ᴀᴛ ʟᴇᴀsᴛ 60 sᴇᴄᴏɴᴅs. 🛡️")

        await db.update_setting('verify_window', val, bot_username=client.username)
        await message.reply_text(f"✅ <b>ᴠᴀʟɪᴅɪᴛʏ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ:</b> <code>{val} sᴇᴄᴏɴᴅs</code> 💎")
        await db.log_event(message.from_user.id, "VALIDITY_UPDATED", f"Set verification window to {val}s")
    except ValueError:
        await message.reply_text("❌ <b>ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ᴏꜰ sᴇᴄᴏɴᴅs.</b> ⚠️")

@Client.on_message(filters.command(['shortner', 'shortener']) & filters.private & admin)
async def shortner_toggle(client: Client, message: Message):
    # Credentials are global, status is bot-specific
    settings = await db.get_settings(bot_username=client.username)

    if len(message.command) < 2:
        status = "ENABLED" if settings.get('shortener_active') else "DISABLED"
        url = settings.get('shortener_url', 'Not Set')
        api = settings.get('shortener_api', 'Not Set')
        return await message.reply(
            f"<b>📊 [@{client.username}] Shortener Status:</b> <code>{status}</code>\n"
            f"<b>🔗 Global Domain:</b> <code>{url}</code>\n"
            f"<b>🔑 Global API Key:</b> <code>{api}</code>\n\n"
            "<b>Usage:</b>\n"
            "• <code>/shortener on</code> - Enable for this bot\n"
            "• <code>/shortener off</code> - Disable for this bot\n"
            "<i>(Config uses main bot credentials)</i>"
        )

    choice = message.command[1].lower()

    if choice == "off":
        await db.update_setting("shortener_active", False, bot_username=client.username)
        return await message.reply(f"✅ <b>Shortener disabled for @{client.username}. Users will receive files directly.</b>")

    elif choice == "on":
        # Check if global credentials already exist
        if settings.get('shortener_url') and settings.get('shortener_api'):
            await db.update_setting("shortener_active", True, bot_username=client.username)
            return await message.reply(f"✅ <b>Shortener enabled for @{client.username} using global credentials!</b>")

        # If not, owner must configure them on main bot first (standardize flow)
        if message.from_user.id != OWNER_ID:
            return await message.reply("❌ <b>Shortener credentials not set. Please contact the owner to configure global settings.</b>")

        db.busy_admins.add(message.from_user.id)
        try:
            # Step 1: Ask for Shortener URL
            url_msg = await client.ask(
                chat_id=message.chat.id,
                text="<b>Send the Shortener Domain URL.</b>\n(Example: <code>arolinks.com</code>)",
                filters=filters.text,
                timeout=60
            )
            if url_msg.text.startswith("/"):
                return await message.reply("❌ <b>Action Cancelled.</b>")

            # Clean and normalize input
            shortener_url = url_msg.text.strip().lower().rstrip('/')
            if not shortener_url.startswith(("http://", "https://")):
                shortener_url = "https://" + shortener_url

            # Step 2: Ask for API Key
            api_msg = await client.ask(
                chat_id=message.chat.id,
                text="<b>Send your API Key for this shortener.</b>",
                filters=filters.text,
                timeout=60
            )
            if api_msg.text.startswith("/"):
                return await message.reply("❌ <b>Action Cancelled.</b>")
            shortener_api = api_msg.text.strip()

            # Update GLOBAL credentials but only enable for CURRENT bot
            await db.update_settings({
                "shortener_url": shortener_url,
                "shortener_api": shortener_api
            })
            await db.update_setting("shortener_active", True, bot_username=client.username)

            await message.reply(
                f"✅ <b>Shortener credentials updated and enabled for @{client.username}!</b>\n\n"
                f"<b>🔗 Domain:</b> <code>{shortener_url}</code>\n"
                f"<b>🔑 API Key:</b> <code>{shortener_api[:5]}***</code>"
            )

        except asyncio.TimeoutError:
            await message.reply("❌ <b>Request Timed Out.</b>")
        except Exception as e:
            await message.reply(f"❌ <b>Error:</b> <code>{e}</code>")
        finally:
            db.busy_admins.discard(message.from_user.id)
    else:
        await message.reply("<b>Invalid choice! Use <code>on</code> or <code>off</code>.</b>")

@Client.on_message(filters.command('fsubbot') & filters.private & admin)
async def fsub_bot_manager(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return

    bots = await db.get_fsub_bots()
    text = "🤖 **˹ ʀᴇǫᴜɪʀᴇᴅ ʙᴏᴛs ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ˼**\n\n"
    buttons = []
    if not bots:
        text += "<blockquote>❌ ɴᴏ ʀᴇǫᴜɪʀᴇᴅ ʙᴏᴛs ᴄᴏɴꜰɪɢᴜʀᴇᴅ.</blockquote>\n"
    else:
        for bot in bots:
            text += f"<b>• {bot['name']}</b> (@{bot['username']})\n<code>ID: {bot['_id']}</code>\n\n"
            buttons.append([InlineKeyboardButton(f"🗑 Delete {bot['name']}", callback_data=f"dfbot_{bot['_id']}", style=ButtonStyle.DANGER)])

    buttons.append([InlineKeyboardButton("➕ Add New Bot", callback_data="afbot", style=ButtonStyle.SUCCESS)])
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close", style=ButtonStyle.DANGER)])

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^(dfbot_|afbot)"))
async def fsub_bot_callbacks(client: Client, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer("OWNER ONLY", show_alert=True)

    data = query.data

    if data.startswith("dfbot_"):
        bot_id = int(data.split("_")[1])
        await db.del_fsub_bot(bot_id)
        await query.answer("Bot removed successfully", show_alert=True)
        # Refresh the list
        bots = await db.get_fsub_bots()
        text = "🤖 **˹ ʀᴇǫᴜɪʀᴇᴅ ʙᴏᴛs ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ˼**\n\n"
        buttons = []
        if not bots:
            text += "<blockquote>❌ ɴᴏ ʀᴇǫᴜɪʀᴇᴅ ʙᴏᴛs ᴄᴏɴꜰɪɢᴜʀᴇᴅ.</blockquote>\n"
        else:
            for bot in bots:
                text += f"<b>• {bot['name']}</b> (@{bot['username']})\n<code>ID: {bot['_id']}</code>\n\n"
                buttons.append([InlineKeyboardButton(f"🗑 Delete {bot['name']}", callback_data=f"dfbot_{bot['_id']}", style=ButtonStyle.DANGER)])
        buttons.append([InlineKeyboardButton("➕ Add New Bot", callback_data="afbot", style=ButtonStyle.SUCCESS)])
        buttons.append([InlineKeyboardButton("❌ Close", callback_data="close", style=ButtonStyle.DANGER)])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "afbot":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask = await client.ask(query.from_user.id, "🔑 **˹ ᴀᴅᴅ ʙᴏᴛ: sᴛᴇᴘ 1 ˼**\n\nsᴇɴᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏᴋᴇɴ ꜰʀᴏᴍ @BotFather.", timeout=60)
            if not ask.text or ask.text.startswith("/"):
                await client.send_message(query.from_user.id, "❌ **Cancelled.**")
                return

            token = ask.text.strip()
            # We need to get bot info from token
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.telegram.org/bot{token}/getMe") as resp:
                    if resp.status != 200:
                        await client.send_message(query.from_user.id, "❌ **Invalid Token!**")
                        return
                    bot_data = await resp.json()
                    bot_info = bot_data['result']
                    name = bot_info['first_name']
                    username = bot_info['username']

            await db.add_fsub_bot(token, name, username)
            await client.send_message(query.from_user.id, f"✅ **Bot @{username} added successfully!**")
        except Exception as e:
            await client.send_message(query.from_user.id, f"❌ **Error:** <code>{e}</code>")
        finally:
            db.busy_admins.discard(query.from_user.id)
            # Re-show the manager
            class FakeMsg:
                def __init__(self, from_user, chat):
                    self.from_user = from_user
                    self.chat = chat
                async def reply_text(self, text, reply_markup=None):
                    return await client.send_message(self.chat.id, text, reply_markup=reply_markup)

            await fsub_bot_manager(client, FakeMsg(query.from_user, query.message.chat))


@Client.on_message(filters.command('reset') & filters.private & admin)
async def reset_verification(client: Client, message: Message):
    pro = await message.reply("⏳ <b><i>˹ ᴘʀᴏᴄᴇssɪɴɢ ʀᴇsᴇᴛ... ˼</i></b>", quote=True)

    args = message.text.split(maxsplit=1)[1:]
    if not args:
        return await pro.edit(
            "⚠️ <b>˹ ᴍɪssɪɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ˼</b>\n\n"
            "ʏᴏᴜ ᴍᴜsᴛ ᴘʀᴏᴠɪᴅᴇ ᴜsᴇʀ ɪᴅs ᴛᴏ ʀᴇsᴇᴛ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ sᴛᴀᴛᴜs.\n\n"
            "📜 <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/reset [ɪᴅ1] [ɪᴅ2]</code>\n"
            "• <code>/reset all</code>\n\n"
            "<i>ᴛʜɪs ᴀᴄᴛɪᴏɴ ᴇxᴘɪʀᴇs ᴀʟʟ ᴀᴄᴛɪᴠᴇ sᴇssɪᴏɴs ꜰᴏʀ ᴛʜᴇ sᴘᴇᴄɪꜰɪᴇᴅ ᴜsᴇʀs.</i>"
        )

    arg_str = args[0].strip()
    if arg_str.lower() == "all":
        try:
            total_users = await db.user_data.count_documents({})
            total_admins = len(await db.get_all_admins())
            total_sessions = await db.sessions.count_documents({})

            # Reset all user verification fields globally
            await db.user_data.update_many(
                {},
                {'$set': {
                    'verified': False,
                    'verified_at': 0,
                    'expires_at': 0,
                    'remaining_access': 0,
                    'verification_token': '',
                    'verification_method': '',
                    'last_verified': 0,
                    'last_access': 0,
                    'access_credits': 0,
                    'bot_verifications': {}
                }}
            )

            # Clear all active sessions
            await db.sessions.delete_many({})
            await db.database["verifications_history"].delete_many({})

            # Drop all worker-specific verification collections
            collections = await db.database.list_collection_names()
            for coll in collections:
                if coll.startswith("bot_") and coll.endswith("_verify"):
                    await db.database[coll].drop()

            report = (
                "📊 **RESET REPORT**\n\n"
                f"✅ Users Reset : {total_users}\n"
                f"✅ Admins Reset : {total_admins}\n"
                f"✅ Sessions Cleared : {total_sessions + total_users}\n"
                "✅ Status : Success"
            )
            return await pro.edit(report, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close", callback_data="close", style=ButtonStyle.DANGER)]]))
        except Exception as e:
            return await pro.edit(f"❌ **Reset Error:** `{e}`")

    # Handle specific user ID list
    user_ids = arg_str.replace(",", " ").split()
    report = ""
    for uid in user_ids:
        try:
            user_id = int(uid.strip())
            # Expire session in user document
            await db.user_data.update_one(
                {'_id': user_id},
                {'$set': {
                    'verified': False,
                    'verified_at': 0,
                    'expires_at': 0,
                    'remaining_access': 0,
                    'verification_token': '',
                    'verification_method': '',
                    'last_verified': 0,
                    'last_access': 0,
                    'access_credits': 0,
                    'bot_verifications': {}
                }}
            )
            # Delete active sessions from sessions collection
            await db.sessions.delete_many({'user_id': str(user_id)})
            await db.database["verifications_history"].delete_many({'user_id': user_id})
            # Delete from worker-specific verification collections
            collections = await db.database.list_collection_names()
            for coll in collections:
                if coll.startswith("bot_") and coll.endswith("_verify"):
                    await db.database[coll].delete_one({'_id': user_id})

            report += f"✅ `{user_id}`: Reset successful.\n"
        except Exception as e:
            report += f"❌ `{uid}`: {e}\n"

    await pro.edit(f"📊 **ʀᴇsᴇᴛ ʀᴇᴘᴏʀᴛ:**\n\n{report}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close", callback_data="close", style=ButtonStyle.DANGER)]]))

@Client.on_message(filters.command('redirect') & filters.private & admin)
async def check_redirects_cmd(client: Client, message: Message):
    pro = await message.reply("⏳ <b><i>˹ ᴀɴᴀʟʏᴢɪɴɢ ʀᴇᴅɪʀᴇᴄᴛs... ˼</i></b>", quote=True)

    # Check for sources of URLs
    urls = []

    # 1. Check if replied to a .txt file
    if message.reply_to_message and message.reply_to_message.document:
        if message.reply_to_message.document.file_name.endswith(".txt"):
            file_path = await client.download_media(message.reply_to_message)
            with open(file_path, "r") as f:
                urls = [line.strip() for line in f if line.strip()]
            os.remove(file_path)

    # 2. Check entities in replied message (Hyperlinks/URLs)
    if not urls and message.reply_to_message:
        urls = extract_urls(message.reply_to_message)

    # 3. Check entities in command message
    if not urls:
        urls = extract_urls(message)

    # 4. Fallback: Manual text splitting (Backward compatibility)
    if not urls:
        raw_text = message.text.split(maxsplit=1)[1:]
        if raw_text:
            urls = raw_text[0].replace(",", " ").split()

    if not urls:
        return await pro.edit(
            "<b>❗ Yᴏᴜ ᴍᴜsᴛ ᴘʀᴏᴠɪᴅᴇ ᴀ ʟɪɴᴋ, ʜʏᴘᴇʀʟɪɴᴋ ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ .ᴛxᴛ ꜰɪʟᴇ.</b>\n\n"
            "<b>📌 Usᴀɢᴇ:</b>\n"
            "• <code>/redirect [ʟɪɴᴋ/ʜʏᴘᴇʀʟɪɴᴋ]</code>\n"
            "• Reply <code>/redirect</code> to a message or file."
        )

    report = ""
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        for url in urls:
            if not url.startswith("http"):
                url = "https://" + url

            try:
                async with session.get(url, allow_redirects=True, timeout=30) as resp:
                    chain = []
                    # Add history hops
                    for i, r in enumerate(resp.history, 1):
                        chain.append(f"{i}. [{r.status}] <code>{r.url}</code>")
                    # Add final destination
                    chain.append(f"{len(resp.history)+1}. [{resp.status}] <code>{resp.url}</code>")

                    report += f"🔗 **Redirect Chain for:**\n`{url}`\n\n" + "\n".join(chain) + "\n\n"
            except Exception as e:
                report += f"🔗 **Redirect Chain for:**\n`{url}`\n"
                report += f"❌ **Error:** <code>{str(e)}</code>\n\n"

            if len(report) > 3500:
                await message.reply(report, disable_web_page_preview=True)
                report = ""

    if report:
        await pro.edit(report, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close", style=ButtonStyle.DANGER)]]))
    else:
        await pro.delete()

@Client.on_message(filters.command('auto_delete') & filters.private & admin)
async def set_auto_delete(client: Client, message: Message):
    if len(message.command) < 2:
        current = await db.get_del_timer()
        return await message.reply_text(
            f"🕒 <b>˹ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ ˼ :</b> <code>{get_exp_time(current)}</code>\n\n"
            "📜 <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/auto_delete [sᴇᴄᴏɴᴅs]</code> — sᴇᴛ ꜰɪʟᴇ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴅᴜʀᴀᴛɪᴏɴ.\n"
            "• <i>ᴇxᴀᴍᴘʟᴇ: /auto_delete 600 (10 ᴍɪɴs)</i>"
        )
    try:
        val = int(message.command[1])
        await db.set_del_timer(val)
        await message.reply_text(f"✅ <b>ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ sᴇᴛ ᴛᴏ:</b> <code>{get_exp_time(val)}</code> 💎")
    except:
        await message.reply_text("❌ <b>ɪɴᴠᴀʟɪᴅ ɪɴᴘᴜᴛ! ᴘʟᴇᴀsᴇ sᴇɴᴅ sᴇᴄᴏɴᴅs.</b>")

@Client.on_message(filters.command('check_auto_delete') & filters.private & admin)
async def check_auto_delete(client: Client, message: Message):
    current = await db.get_del_timer()
    await message.reply_text(f"🔍 <b>˹ ᴄᴜʀʀᴇɴᴛ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ sᴇᴛᴛɪɴɢ ˼</b>\n\n🕒 <code>{get_exp_time(current)}</code>")

@Client.on_message(filters.command('save') & filters.private & admin)
async def save_command(client: Client, message: Message):
    if getattr(client, "name", "Bot") != "Bot":
        return await message.reply("❌ **This command is only available on the main bot.**")

    buttons = [
        [
            InlineKeyboardButton("Backup", callback_data="system_backup", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton("Restore", callback_data="system_restore", style=ButtonStyle.SUCCESS)
        ],
        [InlineKeyboardButton("Close", callback_data="close", style=ButtonStyle.DANGER)]
    ]
    await message.reply_text(
        "🛠️ **System Maintenance**\n\n"
        "Choose an option below to backup or restore the entire database and settings.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_message(filters.command('info') & filters.private & admin)
async def user_info_cmd(client: Client, message: Message):
    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply_text("<b>Usage:</b> <code>/info [USER_ID]</code> or reply to a user.")

    user_id = None
    if len(message.command) >= 2:
        try:
            user_id = int(message.command[1])
        except ValueError:
            return await message.reply_text("❌ **Invalid User ID!**")
    elif message.reply_to_message:
        user_id = message.reply_to_message.from_user.id

    if not user_id:
        return await message.reply_text("❌ **Could not resolve User ID.**")

    pro = await message.reply_text("⏳ **˹ ᴀɴᴀʟʏᴢɪɴɢ ᴜsᴇʀ sᴛᴀᴛᴜs... ˼**")

    try:
        user = await client.get_users(user_id)
        mention = user.mention
    except:
        mention = f"User `{user_id}`"

    status_list = await get_sub_status(client, user_id)

    report = f"📊 **˹ ᴜsᴇʀ ꜰsᴜʙ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ˼**\n\n"
    report += f"👤 **User:** {mention}\n"
    report += f"🆔 **ID:** <code>{user_id}</code>\n\n"

    missing_channels = []
    for s in status_list:
        status_icon = "✅" if s['is_joined'] else "❌"
        report += f"{status_icon} **{s['name']}**\n"
        if not s['is_joined']:
            missing_channels.append(s)

    await pro.edit_text(report)

    if missing_channels:
        owner_msg = f"📢 **˹ ꜰsᴜʙ ᴀʟᴇʀᴛ ˼**\n\n"
        owner_msg += f"👤 **Admin:** {message.from_user.mention}\n"
        owner_msg += f"🔍 **Checking:** {mention} (<code>{user_id}</code>)\n\n"
        owner_msg += "⚠️ **User is missing from these channels:**\n\n"

        for ch in missing_channels:
            owner_msg += f"• **{ch['name']}**\n🔗 [Invite Link]({ch['link']})\n\n"

        try:
            await client.send_message(OWNER_ID, owner_msg, disable_web_page_preview=True)
        except:
            pass

@Client.on_message(filters.command('dbchnl') & filters.private & admin)
async def db_channel_manager(client: Client, message: Message):
    channels = await db.get_all_db_channels(client.username)
    text = f"📋 **˹ [@{client.username}] ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ˼**\n\n"
    buttons = []

    if not channels:
        text += "<blockquote>❌ ɴᴏ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ᴄᴏɴꜰɪɢᴜʀᴇᴅ.</blockquote>\n"
    else:
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                text += f"<b>• {chat.title}</b>\n<code>ID: {cid}</code>\n\n"
            except:
                text += f"<b>• Unknown Channel</b>\n<code>ID: {cid}</code>\n\n"
            buttons.append([InlineKeyboardButton(f"🗑 Delete {cid}", callback_data=f"ddbch_{cid}", style=ButtonStyle.DANGER)])

    buttons.append([InlineKeyboardButton("➕ Add DB Channel", callback_data="adbch", style=ButtonStyle.SUCCESS)])
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close", style=ButtonStyle.DANGER)])

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^(system_backup|system_restore)"))
async def backup_restore_callbacks(client: Client, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer("OWNER ONLY", show_alert=True)

    data = query.data
    import shutil
    import zipfile

    if data == "system_backup":
        await query.answer("Generating backup...", show_alert=True)
        backup_dir = "backup_temp"
        if os.path.exists(backup_dir): shutil.rmtree(backup_dir)
        os.makedirs(backup_dir)

        try:
            # 1. Export DB
            await db.export_data(os.path.join(backup_dir, "database"))

            # 2. Copy Config/Critical files
            critical_files = ["config.py", ".env"] # Add others if needed
            for f in critical_files:
                if os.path.exists(f):
                    shutil.copy(f, backup_dir)

            # 3. Zip everything
            zip_path = "data.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(backup_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file),
                                   os.path.relpath(os.path.join(root, file), backup_dir))

            await query.message.reply_document(
                document=zip_path,
                caption="💎 **System Backup Complete**\n\nThis file contains the entire bot data. Keep it safe."
            )
            os.remove(zip_path)
        except Exception as e:
            await query.message.reply_text(f"❌ **Backup Failed:** `{e}`")
        finally:
            if os.path.exists(backup_dir): shutil.rmtree(backup_dir)

    elif data == "system_restore":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask = await client.ask(query.from_user.id, "📥 **System Restore**\n\nPlease upload the `data.zip` file.", timeout=300)
            if not ask.document or ask.document.file_name != "data.zip":
                await client.send_message(query.from_user.id, "❌ **Invalid file! Please upload exactly `data.zip`.**")
                return

            path = await client.download_media(ask)
            restore_dir = "restore_temp"
            if os.path.exists(restore_dir): shutil.rmtree(restore_dir)
            os.makedirs(restore_dir)

            # Validate ZIP file structure
            if not zipfile.is_zipfile(path):
                await client.send_message(query.from_user.id, "❌ **Failed to restore: The uploaded file is not a valid ZIP archive.**")
                os.remove(path)
                return

            with zipfile.ZipFile(path, 'r') as zip_ref:
                namelist = zip_ref.namelist()
                if not any(name.startswith("database/") for name in namelist):
                    await client.send_message(query.from_user.id, "❌ **Failed to restore: Invalid backup structure. Could not find database entries.**")
                    os.remove(path)
                    return
                zip_ref.extractall(restore_dir)

            # 1. Restore DB
            db_dir = os.path.join(restore_dir, "database")
            if os.path.exists(db_dir):
                await db.import_data(db_dir)

            # 2. Restore Files
            for f in os.listdir(restore_dir):
                if os.path.isfile(os.path.join(restore_dir, f)):
                    shutil.copy(os.path.join(restore_dir, f), ".")

            await client.send_message(query.from_user.id, "✅ **System restored successfully! Restarting...**")
            os.remove(path)
            # Trigger Restart
            os.execl(sys.executable, sys.executable, "-m", "main")

        except asyncio.TimeoutError:
            await client.send_message(query.from_user.id, "⏰ **Session Timed Out.**")
        except Exception as e:
            await client.send_message(query.from_user.id, f"❌ **Restore Failed:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            if os.path.exists("restore_temp"): shutil.rmtree("restore_temp")

@Client.on_callback_query(filters.regex(r"^(ddbch_|adbch)"))
async def db_channel_callbacks(client: Client, query: CallbackQuery):
    if not await db.admin_exist(query.from_user.id) and query.from_user.id != OWNER_ID:
        return await query.answer("ADMIN ONLY", show_alert=True)

    data = query.data

    if data.startswith("ddbch_"):
        cid = int(data.split("_")[1])
        await db.del_db_channel(cid, client.username)
        await query.answer("DB Channel removed successfully", show_alert=True)
        # Refresh the list
        channels = await db.get_all_db_channels(client.username)
        text = f"📋 **˹ [@{client.username}] ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ˼**\n\n"
        buttons = []
        if not channels:
            text += "<blockquote>❌ ɴᴏ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs ᴄᴏɴꜰɪɢᴜʀᴇᴅ.</blockquote>\n"
        else:
            for chid in channels:
                try:
                    chat = await client.get_chat(chid)
                    text += f"<b>• {chat.title}</b>\n<code>ID: {chid}</code>\n\n"
                except:
                    text += f"<b>• Unknown Channel</b>\n<code>ID: {chid}</code>\n\n"
                buttons.append([InlineKeyboardButton(f"🗑 Delete {chid}", callback_data=f"ddbch_{chid}", style=ButtonStyle.DANGER)])
        buttons.append([InlineKeyboardButton("➕ Add DB Channel", callback_data="adbch", style=ButtonStyle.SUCCESS)])
        buttons.append([InlineKeyboardButton("❌ Close", callback_data="close", style=ButtonStyle.DANGER)])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "adbch":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask = await client.ask(query.from_user.id, "📊 **˹ ᴀᴅᴅ ᴅʙ ᴄʜᴀɴɴᴇʟ ˼**\n\nsᴇɴᴅ ᴛʜᴇ **ᴄʜᴀɴɴᴇʟ ɪᴅ**.", timeout=60)
            if not ask.text or ask.text.startswith("/"):
                await client.send_message(query.from_user.id, "❌ **Cancelled.**")
                return

            try:
                cid = int(ask.text.strip())
                # Verify bot is admin in the channel
                chat = await client.get_chat(cid)
                bot_member = await client.get_chat_member(chat.id, "me")
                if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    await client.send_message(query.from_user.id, "❌ **Bot not admin in this channel!**")
                    return

                await db.add_db_channel(cid, client.username)
                await client.send_message(query.from_user.id, f"✅ **Channel '{chat.title}' added for @{client.username}!**")
            except ValueError:
                await client.send_message(query.from_user.id, "❌ **Invalid Channel ID!**")
            except Exception as e:
                await client.send_message(query.from_user.id, f"❌ **Error:** <code>{e}</code>")
        except Exception as e:
            await client.send_message(query.from_user.id, f"❌ **Error:** <code>{e}</code>")
        finally:
            db.busy_admins.discard(query.from_user.id)
            # Re-show the manager
            class FakeMsg:
                def __init__(self, from_user, chat):
                    self.from_user = from_user
                    self.chat = chat
                async def reply_text(self, text, reply_markup=None):
                    return await client.send_message(self.chat.id, text, reply_markup=reply_markup)

            await db_channel_manager(client, FakeMsg(query.from_user, query.message.chat))


@Client.on_message(filters.command('logs') & filters.private & admin)
async def view_logs_cmd(client: Client, message: Message):
    # Parse command arguments
    args = message.text.split()
    user_id = None
    if len(args) > 1:
        user_id_str = args[1].strip()
        if user_id_str.isdigit() or (user_id_str.startswith("-") and user_id_str[1:].isdigit()):
            user_id = int(user_id_str)
        else:
            return await message.reply_text("❌ **Invalid User ID! Must be a numeric value.**")

    if user_id:
        logs = await db.get_user_logs(user_id, 30)
        title = f"📋 **System Logs for User** `{(user_id)}`"
    else:
        logs = await db.get_recent_logs(30)
        title = "📋 **Recent System Logs**"

    if not logs:
        return await message.reply_text(f"❌ **No logs found{' for this user' if user_id else ''}.**")

    log_text = f"{title}\n\n"
    for log in logs:
        dt = log['timestamp'].strftime('%H:%M:%S')
        details = (log['details'][:60] + '...') if len(log['details']) > 60 else log['details']
        if user_id:
            log_text += f"• [{dt}] **{log['event_type']}**: `{details}`\n"
        else:
            log_text += f"• [{dt}] (User: `{log['user_id']}`) **{log['event_type']}**: `{details}`\n"

    # Telegram messages have a length limit of 4096 characters, truncate if needed
    if len(log_text) > 4096:
        log_text = log_text[:4090] + "..."

    await message.reply_text(log_text)

@Client.on_message(filters.command('api_url') & filters.private & admin)
async def set_api_url_command(client: Client, message: Message):
    if len(message.command) < 2:
        settings = await db.get_settings(bot_username=client.username)
        current_api = settings.get('api_url', 'N/A')
        return await message.reply_text(
            f"🔌 <b>˹ ᴄᴜʀʀᴇɴᴛ ᴀᴘɪ ᴜʀʟ ˼ :</b> <code>{current_api}</code>\n\n"
            "✨ <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/api_url [ᴜʀʟ]</code> — sᴇᴛ ᴛʜᴇ ɴᴇᴡ ᴀᴘɪ ʙᴀsᴇ ᴜʀʟ. 🔌"
        )

    val = message.text.split(None, 1)[1].strip()
    await db.update_setting('api_url', val, bot_username=client.username)
    await message.reply_text(f"✅ <b>ᴀᴘɪ ᴜʀʟ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ:</b> <code>{val}</code> 💎")
    await db.log_event(message.from_user.id, "API_URL_UPDATED", f"Set API URL to {val}")

@Client.on_message(filters.command('web_url') & filters.private & admin)
async def set_web_url_command(client: Client, message: Message):
    if len(message.command) < 2:
        settings = await db.get_settings(bot_username=client.username)
        current_web = settings.get('website_url', 'N/A')
        return await message.reply_text(
            f"🌐 <b>˹ ᴄᴜʀʀᴇɴᴛ ᴡᴇʙsɪᴛᴇ ᴜʀʟ ˼ :</b> <code>{current_web}</code>\n\n"
            "✨ <b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/web_url [ᴜʀʟ]</code> — sᴇᴛ ᴛʜᴇ ɴᴇᴡ ᴡᴇʙsɪᴛᴇ ᴜʀʟ. 🌐"
        )

    val = message.text.split(None, 1)[1].strip()
    await db.update_setting('website_url', val, bot_username=client.username)
    await message.reply_text(f"✅ <b>ᴡᴇʙsɪᴛᴇ ᴜʀʟ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ:</b> <code>{val}</code> 💎")
    await db.log_event(message.from_user.id, "WEBSITE_URL_UPDATED", f"Set Website URL to {val}")
