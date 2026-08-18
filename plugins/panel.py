
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery
from helper_func import InlineKeyboardButton, random_button_style, ButtonStyle
from config import OWNER_ID, ANIME_BANNERS
from database.database import db
from helper_func import admin, get_banners, send_media
import random
import asyncio
import re
import traceback

def get_panel_caption(settings):
    cap_status = []
    if settings.get('use_recaptcha'): cap_status.append("ʀᴇᴄᴀᴘᴛᴄʜᴀ")
    if settings.get('use_turnstile'): cap_status.append("ᴛᴜʀɴsᴛɪʟᴇ")
    captcha_text = " + ".join(cap_status) if cap_status else "ᴅɪsᴀʙʟᴇᴅ 🔓"

    sys_status = "ᴏᴘᴇʀᴀᴛɪᴏɴᴀʟ ✅" if settings.get('shortener_active', True) else "ᴘᴀᴜsᴇᴅ 🛑"
    sys_status += " (ɢʟᴏʙᴀʟ ᴄᴏɴꜰɪɢ)"
    fv = "ᴏɴ 👁️" if settings.get('frontend_verify', True) else "ᴏꜰꜰ 💤"

    ver_enabled = settings.get('verification_enabled', True)
    ver_status = "ᴇɴᴀʙʟᴇᴅ 🟢" if ver_enabled else "ᴅɪsᴀʙʟᴇᴅ 🔴"
    ver_method = settings.get('verification_method', 'mini_app')
    method_display = {
        'api_url': 'ᴀᴘɪ ᴜʀʟ 🔌',
        'web_url': 'ᴡᴇʙ ᴜʀʟ 🌐',
        'mini_app': 'ᴍɪɴɪ ᴀᴘᴘ 📱',
        'browser': 'ʙʀᴏᴡsᴇʀ 📱',
        'own_browser': 'ᴏᴡɴ ʙʀᴏᴡsᴇʀ 🌐'
    }.get(ver_method, 'ᴍɪɴɪ ᴀᴘᴘ 📱')

    api_url_str = settings.get('api_url')
    api_url_text = f"<code>{api_url_str}</code>" if api_url_str else "<code>N/A</code>"

    base_url_str = settings.get('base_url')
    base_url_text = f"<code>{base_url_str}</code>" if base_url_str else "<code>N/A</code>"

    session_configured = "ᴄᴏɴꜰɪɢᴜʀᴇᴅ 🟢" if settings.get('session_string') else "ɴᴏᴛ ᴄᴏɴꜰɪɢᴜʀᴇᴅ 🔴"

    import config
    return (
        "━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ <b>˹ ᴀɴɪᴢᴏɴᴇꜰʟɪx ᴘʀᴇᴍɪᴜᴍ ᴘᴀɴᴇʟ ˼</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚀 <b>sʏsᴛᴇᴍ ᴍᴏᴅᴇ:</b> <code>{sys_status}</code>\n"
        f"🛡️ <b>ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ:</b> <code>{ver_status}</code>\n"
        f"⚙️ <b>ᴍᴇᴛʜᴏᴅ:</b> <code>{method_display}</code>\n"
        f"🛡️ <b>sᴇᴄᴜʀɪᴛʏ:</b> <code>{captcha_text}</code>\n"
        f"🌐 <b>ꜰʀᴏɴᴛᴇɴᴅ ɢᴀᴛᴇ:</b> <code>{fv}</code>\n"
        f"🔌 <b>ᴀᴘɪ ᴜʀʟ:</b> {api_url_text}\n"
        f"🌐 <b>ʙᴀsᴇ ᴜʀʟ:</b> {base_url_text}\n"
        f"🆔 <b>ᴀᴘᴘ ɪᴅ:</b> <code>{settings.get('app_id', config.APP_ID)}</code>\n"
        f"🔑 <b>ᴀᴘɪ ʜᴀsʜ:</b> <code>{settings.get('api_hash', config.API_HASH)}</code>\n"
        f"👑 <b>ᴏᴡɴᴇʀ ɪᴅ:</b> <code>{settings.get('owner_id', config.OWNER_ID)}</code>\n"
        f"⚡ <b>ᴅᴇʟɪᴠᴇʀʏ sᴇssɪᴏɴ:</b> <code>{session_configured}</code>\n\n"
        "<blockquote>💎 <b>ᴀᴅᴠᴀɴᴄᴇᴅ ꜰɪʟᴇ-ᴛᴏ-ʟɪɴᴋ sʏsᴛᴇᴍ</b>\n"
        "ᴏᴘᴛɪᴍɪᴢᴇᴅ ꜰᴏʀ ʜɪɢʜ ᴘᴇʀꜰᴏʀᴍᴀɴᴄе ᴀɴᴅ sᴇᴄᴜʀɪᴛʏ. ✨</blockquote>\n"
        "━━━━━━━━━━━━━━━━━━━"
    )

def get_panel_markup(settings):
    def get_ico(key, default=True):
        return "🟢" if settings.get(key, default) else "🔴"

    buttons = [
        [
            InlineKeyboardButton(f"🚀 sʏs: {get_ico('shortener_active')}", callback_data="tg_shortener_active", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(f"🌐 ꜰ-ɢᴀᴛᴇ: {get_ico('frontend_verify')}", callback_data="tg_frontend_verify", style=ButtonStyle.SUCCESS)
        ],
        [
            InlineKeyboardButton(f"🛡️ ʀᴇᴄᴀᴘ: {get_ico('use_recaptcha', False)}", callback_data="set_captcha_recaptcha", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(f"🛡️ ᴛᴜʀɴ: {get_ico('use_turnstile', False)}", callback_data="set_captcha_turnstile", style=ButtonStyle.SUCCESS)
        ],
        [
             InlineKeyboardButton(f"🎲 ʀᴀɴᴅᴏᴍ: {get_ico('random_mode', False)}", callback_data="tg_random_mode", style=ButtonStyle.SUCCESS),
             InlineKeyboardButton("🔌 ᴀᴘɪ ᴜʀʟ", callback_data="edit_auth_api_url", style=ButtonStyle.PRIMARY)
        ],
        [
             InlineKeyboardButton(f"🤝 ʀᴇꜰ: {get_ico('referral_active', True)}", callback_data="tg_referral_active", style=ButtonStyle.SUCCESS),
             InlineKeyboardButton("🔄 sʏɴᴄ", callback_data="refresh_panel", style=ButtonStyle.PRIMARY)
        ],
        [
            InlineKeyboardButton("🆔 ᴀᴘᴘ ɪᴅ", callback_data="edit_auth_app_id", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("🔑 ᴀᴘɪ ʜᴀsʜ", callback_data="edit_auth_api_hash", style=ButtonStyle.PRIMARY)
        ],
        [
            InlineKeyboardButton("👑 ᴏᴡɴᴇʀ ɪᴅ", callback_data="edit_auth_owner_id", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("🔑 ᴄᴏʀᴇ ᴄᴏɴꜰɪɢ", callback_data="show_auth", style=ButtonStyle.SECONDARY)
        ],
        [
            InlineKeyboardButton("📊 sᴛᴀᴛɪsᴛɪᴄs", callback_data="view_stats", style=ButtonStyle.SECONDARY),
            InlineKeyboardButton("🎬 ᴠɪᴅᴇᴏ ᴄᴏɴꜰɪɢ", callback_data="manage_videos", style=ButtonStyle.SECONDARY)
        ],
        [
            InlineKeyboardButton("🔗 sʜᴏʀᴛ ᴄᴏɴꜰɪɢ", callback_data="manage_shorteners", style=ButtonStyle.SECONDARY),
            InlineKeyboardButton("🤖 ᴄʟᴏɴᴇ ᴍᴀɴᴀɢᴇʀ", callback_data="manage_clones", style=ButtonStyle.SECONDARY)
        ],
        [
            InlineKeyboardButton("📝 ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ", callback_data="manage_custom_caption", style=ButtonStyle.SECONDARY),
            InlineKeyboardButton("🖼️ ɪᴍᴀɢᴇ ᴄᴏɴꜰɪɢ", callback_data="manage_images", style=ButtonStyle.SECONDARY)
        ],
        [
            InlineKeyboardButton("🤖 ʀᴇǫ ʙᴏᴛs", callback_data="view_fsub_bots", style=ButtonStyle.SECONDARY),
            InlineKeyboardButton("🤖 ʜᴇʟᴘᴇʀ ʙᴏᴛs", callback_data="manage_helpers", style=ButtonStyle.SECONDARY)
        ],
        [
            InlineKeyboardButton("🌐 ᴘʀᴏxɪᴇs", callback_data="manage_proxies", style=ButtonStyle.SECONDARY),
            InlineKeyboardButton("📝 ᴠᴇʀɪғʏ ʟᴏɢ", callback_data="manage_verify_log", style=ButtonStyle.SECONDARY)
        ],
        [
            InlineKeyboardButton("🛡️ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴇᴛᴛɪɴɢs", callback_data="manage_verification", style=ButtonStyle.SECONDARY)
        ],
        [
            InlineKeyboardButton("🔄 ʀᴇsᴛᴀʀᴛ", callback_data="panel_restart", style=ButtonStyle.DANGER)
        ],
        [
            InlineKeyboardButton("🔄 sʏɴᴄ", callback_data="refresh_panel", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close", style=ButtonStyle.DANGER)
        ]
    ]
    return InlineKeyboardMarkup(buttons)

async def edit_panel_message(query: CallbackQuery, text: str, markup: InlineKeyboardMarkup):
    try:
        await query.message.edit_caption(caption=text, reply_markup=markup)
    except Exception:
        try:
            await query.message.edit_text(text=text, reply_markup=markup)
        except Exception:
            pass

@Client.on_message(filters.command(['panel', 'settings']) & filters.private & admin)
async def owner_panel(client: Client, message: Message):
    settings = await db.get_settings(bot_username=client.username)
    banners = await get_banners(client)

    caption = get_panel_caption(settings)
    markup = get_panel_markup(settings)

    if banners:
        photo = random.choice(banners)
        try:
            return await send_media(
                client=client,
                chat_id=message.chat.id,
                photo=photo,
                caption=caption,
                reply_markup=markup
            )
        except Exception:
            pass

    await message.reply_text(
        text=caption,
        reply_markup=markup
    )

@Client.on_callback_query(filters.regex(r"^(tg_|refresh_panel|set_captcha_|show_auth|show_captcha_keys|show_shield_settings|edit_auth_|view_stats|set_detect_timer|add_clone|view_logs|view_fsub_bots|panel_restart|manage_clones|del_clone_|edit_clone_|manage_images|add_banner|del_banner_|manage_shorteners|add_shortener|del_short_|manage_videos|add_video_banner|del_video_banner_|conf_clone_|cset_|cbanner_|cdel_|manage_helpers|add_helper|del_helper_|manage_proxies|add_proxy_prompt|delete_proxy_list|del_proxy_act_|check_proxies_act|toggle_proxy_strategy|toggle_protect_|manage_custom_caption|toggle_custom_caption|reset_custom_caption|set_caption_prompt|delete_session_string|manage_verify_log|set_verify_log_channel|remove_verify_log_channel|del_vlog_|manage_verification|set_ver_|conf_short_|set_shmethod_)"))
async def panel_callback(client: Client, query: CallbackQuery):
    if not await db.admin_exist(query.from_user.id) and query.from_user.id != OWNER_ID:
        return await query.answer("˹ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ ˼", show_alert=True)

    data = query.data

    if not data.startswith(("refresh_panel", "panel_restart", "view_logs", "del_")):
        try: await query.answer()
        except: pass

    if data == "delete_session_string":
        await db.update_setting("session_string", "", bot_username=client.username)
        from plugins.start import SESSION_CLIENTS
        for k in list(SESSION_CLIENTS.keys()):
            try:
                await SESSION_CLIENTS[k].stop()
            except:
                pass
        SESSION_CLIENTS.clear()
        await query.answer("sᴇssɪᴏɴ sᴛʀɪɴɢ deleted & delivery feature disabled!", show_alert=True)
        query.data = "show_auth"
        return await panel_callback(client, query)

    elif data == "refresh_panel":
        await query.answer("sʏsᴛᴇᴍ sʏɴᴄᴇᴅ")
        settings = await db.get_settings(bot_username=client.username)
        return await edit_panel_message(query, get_panel_caption(settings), get_panel_markup(settings))
    elif data == "view_logs":
        logs = await db.get_recent_logs(10)
        if not logs:
            return await query.answer("No logs found.", show_alert=True)

        log_text = "📜 **Recent System Logs**\n\n"
        for log in logs:
            dt = log['timestamp'].strftime('%H:%M:%S')
            details = (log['details'][:60] + '...') if len(log['details']) > 60 else log['details']
            log_text += f"• [{dt}] **{log['event_type']}**: `{details}`\n"

        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)]])
        return await edit_panel_message(query, log_text, markup)
    elif data == "view_fsub_bots":
        bots = await db.get_fsub_bots()
        text = "🤖 **Required Bots Management**\n\n"
        if not bots:
            text += "No required bots configured.\n"
        else:
            for bot in bots:
                text += f"• `{bot['_id']}` : `{bot['token'][:10]}...`\n"

        text += "\nUse `/fsubbot` command to manage these bots."
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)]])
        return await edit_panel_message(query, text, markup)
    elif data == "panel_restart":
        await query.answer("Restarting Bot...", show_alert=True)
        # restart_bot is in plugins.admin
        from plugins.admin import restart_bot
        await restart_bot(client, query.message)
        return
    elif data == "manage_clones":
        clones = await db.get_all_clones()
        text = "🤖 **Clone Management Panel**\n\n"
        buttons = []
        if not clones:
            text += "No clone bots registered."
        else:
            for clone in clones:
                uname = clone['username']
                text += f"• @{uname} (ID: `{clone['channel_id']}`)\n"
                buttons.append([
                    InlineKeyboardButton(f"⚙️ Configure @{uname}", callback_data=f"conf_clone_{uname}", style=ButtonStyle.SECONDARY),
                    InlineKeyboardButton(f"🗑 ᴅᴇʟᴇᴛᴇ", callback_data=f"del_clone_{uname}", style=ButtonStyle.DANGER)
                ])

        buttons.append([InlineKeyboardButton("➕ ᴀᴅᴅ ɴᴇᴡ ᴄʟᴏɴᴇ", callback_data="add_clone", style=ButtonStyle.SUCCESS)])
        buttons.append([InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)])
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data.startswith("conf_clone_"):
        uname = data.replace("conf_clone_", "").strip()
        clone = await db.get_clone(uname)
        if not clone: return await query.answer(f"Clone @{uname} not found!", show_alert=True)

        text = (
            f"⚙️ **Configuration: @{uname}**\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏷️ **Name:** `{clone.get('name')}`\n"
            f"🔗 **Community:** `{clone.get('community_link')}`\n"
            f"📢 **FSUB Channels:** `{clone.get('fsub_channels')}`\n"
            f"🖼️ **Banners:** `{len(clone.get('banners', []))} uploaded`\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [InlineKeyboardButton("📝 ᴇᴅɪᴛ ɴᴀᴍᴇ", callback_data=f"cset_name_{uname}", style=ButtonStyle.PRIMARY), InlineKeyboardButton("🔗 ᴄᴏᴍᴍᴜɴɪᴛʏ ʟɪɴᴋ", callback_data=f"cset_community_link_{uname}", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("📢 ꜰsᴜʙ ᴄʜᴀɴɴᴇʟs", callback_data=f"cset_fsub_channels_{uname}", style=ButtonStyle.PRIMARY), InlineKeyboardButton("🔑 ᴛᴏᴋᴇɴ", callback_data=f"edit_clone_{uname}", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="manage_clones", style=ButtonStyle.SECONDARY)]
        ]
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data.startswith("cset_"):
        # Format: cset_field_uname
        if data.startswith("cset_name_"):
            field = "name"
            uname = data.replace("cset_name_", "").strip()
        elif data.startswith("cset_community_link_"):
            field = "community_link"
            uname = data.replace("cset_community_link_", "").strip()
        elif data.startswith("cset_fsub_channels_"):
            field = "fsub_channels"
            uname = data.replace("cset_fsub_channels_", "").strip()
        else:
            return await query.answer("Invalid Setting")

        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask_text = f"📥 **Send new value for {field.upper()} of @{uname}:**"
            if field == "fsub_channels": ask_text += "\n\n(Send Channel IDs separated by comma)"

            ask = await client.ask(query.from_user.id, ask_text, timeout=120)
            if not ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input. Text required.**")
                return
            if ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ **Cancelled.**")
            else:
                val = ask.text.strip()
                if field == "fsub_channels":
                    val = [int(i.strip()) for i in val.split(",") if i.strip().lstrip("-").isdigit()]

                await db.update_clone_setting(uname, field, val)
                await client.send_message(query.from_user.id, "✅ **Setting Updated!**")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Update Failed:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings()
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return

    elif data.startswith("cbanner_list_"):
        uname = data.replace("cbanner_list_", "").strip()
        clone = await db.get_clone(uname)
        if not clone: return await query.answer(f"Clone @{uname} not found!", show_alert=True)
        banners = clone.get('banners', [])
        text = f"🖼️ **Banners for @{uname}**\n\n"
        buttons = []
        for i, url in enumerate(banners):
            text += f"• `{i+1}`: {url[:30]}...\n"
            buttons.append([InlineKeyboardButton(f"🗑 Delete #{i+1}", callback_data=f"cdel_banner_{uname}_{i}", style=ButtonStyle.DANGER)])

        buttons.append([InlineKeyboardButton("➕ ᴀᴅᴅ ʙᴀɴɴᴇʀ", callback_data=f"cbanner_add_{uname}", style=ButtonStyle.SUCCESS)])
        buttons.append([InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data=f"conf_clone_{uname}", style=ButtonStyle.SECONDARY)])
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data.startswith("cbanner_add_"):
        uname = data.replace("cbanner_add_", "").strip()
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask = await client.ask(query.from_user.id, f"🖼️ **Send new Banner URL for @{uname}:**", timeout=120)
            if not ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input. URL required.**")
                return
            if ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ **Cancelled.**")
            else:
                clone = await db.get_clone(uname)
                if not clone:
                    await client.send_message(query.from_user.id, f"❌ **Clone @{uname} not found!**")
                    return
                banners = clone.get('banners', [])
                banners.append(ask.text.strip())
                await db.update_clone_setting(uname, "banners", banners)
                await client.send_message(query.from_user.id, "✅ **Banner Added!**")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Banner add failed:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings()
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return

    elif data.startswith("cdel_banner_"):
        # Format: cdel_banner_uname_idx
        try:
            temp = data.removeprefix("cdel_banner_")
            parts = temp.rsplit('_', 1)
            uname = parts[0].strip()
            idx = int(parts[1])
        except:
            return await query.answer("Parsing Error")

        clone = await db.get_clone(uname)
        if not clone: return await query.answer(f"Clone @{uname} not found!", show_alert=True)
        banners = clone.get('banners', [])
        if 0 <= idx < len(banners):
            banners.pop(idx)
            await db.update_clone_setting(uname, "banners", banners)
            await query.answer("Banner Removed!")

        query.data = f"cbanner_list_{uname}"
        return await panel_callback(client, query)

    elif data.startswith("del_clone_"):
        username = data.replace("del_clone_", "").strip()
        await db.del_clone(username)
        await query.answer(f"@{username} Deleted", show_alert=True)
        # Refresh the clones list
        query.data = "manage_clones"
        return await panel_callback(client, query)

    elif data.startswith("edit_clone_"):
        username = data.replace("edit_clone_", "").strip()
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask = await client.ask(query.from_user.id, f"🔑 <b>sᴇɴᴅ ɴᴇᴡ ᴛᴏᴋᴇɴ ꜰᴏʀ @{username}:</b>", timeout=60)
            if not ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input. Token required.**")
                return
            if ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ <b>ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
            else:
                await db.update_clone_token(username, ask.text.strip())
                await client.send_message(query.from_user.id, f"✅ <b>ᴛᴏᴋᴇɴ ᴜᴘᴅᴀᴛᴇᴅ ꜰᴏʀ @{username}!</b>")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Token update failed:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings()
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return

    elif data == "add_clone":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            u_ask = await client.ask(query.from_user.id, "🤖 <b>˹ ᴄʟᴏɴᴇ: sᴛᴇᴘ 1 ˼</b>\n\nsᴇɴᴅ ʙᴏᴛ <b>ᴜsᴇʀɴᴀᴍᴇ</b> (ᴡɪᴛʜᴏᴜᴛ @).", timeout=60)
            if not u_ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input.**")
                return
            if u_ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ <b>ᴄʟᴏɴɪɴɢ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
                return
            username = u_ask.text.strip().replace("@", "")
            await u_ask.reply(f"✅ <b>ᴜsᴇʀɴᴀᴍᴇ @{username} ʀᴇᴄᴏʀᴅᴇᴅ!</b>")
            await asyncio.sleep(1)

            c_ask = await client.ask(query.from_user.id, "📊 <b>˹ ᴄʟᴏɴᴇ: sᴛᴇᴘ 2 ˼</b>\n\nsᴇɴᴅ <b>ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ ɪᴅ</b>.", timeout=60)
            if not c_ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input.**")
                return
            if c_ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ <b>ᴄʟᴏɴɪɴɢ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
                return
            channel_id = c_ask.text.strip()
            if not channel_id.lstrip("-").isdigit():
                return await c_ask.reply("❌ **Invalid Channel ID! Must be a number.**")
            await c_ask.reply("✅ <b>ᴄʜᴀɴɴᴇʟ ɪᴅ ʀᴇᴄᴏʀᴅᴇᴅ!</b>")
            await asyncio.sleep(1)

            t_ask = await client.ask(query.from_user.id, "🔑 <b>˹ ᴄʟᴏɴᴇ: sᴛᴇᴘ 3 ˼</b>\n\nsᴇɴᴅ ʙᴏᴛ <b>ᴛᴏᴋᴇɴ</b>.", timeout=60)
            if not t_ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input.**")
                return
            if t_ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ <b>ᴄʟᴏɴɪɴɢ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
                return
            token = t_ask.text.strip()

            await db.add_clone(username, token, channel_id)
            await client.send_message(query.from_user.id, f"💎 <b>ᴄʟᴏɴᴇ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴄᴏɴꜰɪɢᴜʀᴇᴅ!</b>\n\nʙᴏᴛ: @{username}\n\n<i>ɪᴛ ᴡɪʟʟ ʙᴇ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴏɴ ɴᴇxᴛ sʏsᴛᴇᴍ ʙᴏᴏᴛ.</i>")
        except asyncio.TimeoutError:
            await client.send_message(query.from_user.id, "⏰ <b>sᴇssɪᴏɴ ᴛɪᴍᴇᴅ ᴏᴜᴛ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.</b>")
        except Exception as e:
            await client.send_message(query.from_user.id, f"❌ <b>ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ:</b> <code>{str(e)}</code>")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings()
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return
    elif data == "set_detect_timer":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask = await client.ask(query.from_user.id, "⏱️ <b>sᴇɴᴅ ᴅᴇᴛᴇᴄᴛ ᴛɪᴍᴇʀ ɪɴ sᴇᴄᴏɴᴅs:</b>", timeout=60)
            if not ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input.**")
                return
            if ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ <b>ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
                return
            val = int(ask.text)
            await db.update_setting("detect_timer", val)
            await client.send_message(query.from_user.id, f"✅ <b>ᴅᴇᴛᴇᴄᴛ ᴛɪᴍᴇʀ sᴇᴛ ᴛᴏ {val}s</b>")
        except asyncio.TimeoutError:
            await client.send_message(query.from_user.id, "⏰ <b>ᴛɪᴍᴇᴏᴜᴛ.</b>")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Timer set failed:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings()
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return
    elif data == "close":
        return await query.message.delete()
    elif data.startswith("tg_"):
        settings = await db.get_settings(bot_username=client.username)
        key = data.replace("tg_", "")

        # Determine default value (True or False) if key doesn't exist
        # Keys that default to False:
        f_defaults = ['random_mode', 'use_recaptcha', 'use_turnstile']
        default_val = False if key in f_defaults else True

        new_val = not settings.get(key, default_val)
        await db.update_setting(key, new_val, bot_username=client.username)
        await query.answer(f"{key.replace('_', ' ').upper()} -> {'ON' if new_val else 'OFF'}")
    elif data == "view_stats":
        stats = await db.get_stats()
        text = (
            "📊 <b>˹ ᴀᴅᴠᴀɴᴄᴇᴅ sʏsᴛᴇᴍ sᴛᴀᴛɪsᴛɪᴄs ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ <b>Total Verifications:</b> <code>{stats.get('total_verifications', 0)}</code>\n"
            f"💎 <b>Successful:</b> <code>{stats.get('successful_verifications', 0)}</code>\n"
            f"❌ <b>Failed:</b> <code>{stats.get('failed_verifications', 0)}</code>\n\n"
            f"🤝 <b>Total Referrals:</b> <code>{stats.get('total_referrals', 0)}</code>\n"
            f"🌟 <b>Success Referrals:</b> <code>{stats.get('successful_referrals', 0)}</code>\n"
            f"🚫 <b>Failed Referrals:</b> <code>{stats.get('failed_referrals', 0)}</code>\n\n"
            f"🔥 <b>Active Sessions:</b> <code>{stats.get('active_sessions', 0)}</code>\n"
            f"⏰ <b>Expired Sessions:</b> <code>{stats.get('expired_sessions', 0)}</code>\n"
            f"⚡ <b>Today's Accesses:</b> <code>{stats.get('today_access', 0)}</code>\n"
            f"🛡️ <b>Security Alerts:</b> <code>{stats.get('security_alerts', 0)}</code>\n"
            f"🚫 <b>Bypasses Blocked:</b> <code>{stats.get('total_bypasses', 0)}</code>\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)]])
        return await edit_panel_message(query, text, markup)
    elif data == "show_auth":
        settings = await db.get_settings(bot_username=client.username)
        session_configured = "ᴄᴏɴꜰɪɢᴜʀᴇᴅ 🟢" if settings.get('session_string') else "ɴᴏᴛ ᴄᴏɴꜰɪɢᴜʀᴇᴅ 🔴"
        auth_text = (
            "<b>🔑 ˹ ᴄᴏʀᴇ ᴄᴏɴꜰɪɢᴜʀᴀᴛɪᴏɴ ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌐 <b>ᴡᴇʙsɪᴛᴇ ᴜʀʟ:</b> <code>{settings.get('website_url')}</code>\n"
            f"🔌 <b>ᴀᴘɪ ᴜʀʟ:</b> <code>{settings.get('api_url', 'N/A')}</code>\n"
            f"🌐 <b>ʙᴀsᴇ ᴜʀʟ:</b> <code>{settings.get('base_url', 'N/A')}</code>\n"
            f"🕒 <b>ᴠᴇʀɪꜰʏ ᴡɪɴᴅᴏᴡ:</b> <code>{settings.get('verify_window', 86400)}s</code>\n"
            f"🔢 <b>ᴀᴄᴄᴇss ʟɪᴍɪᴛ:</b> <code>{settings.get('access_limit', 1)}</code>\n"
            f"🔑 <b>sᴇssɪᴏɴ sᴛʀɪɴɢ:</b> <code>{session_configured}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "<i>ᴛᴀᴘ ᴀ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴜᴘᴅᴀᴛᴇ sᴇᴛᴛɪɴɢs. ✨</i>"
        )
        session_row = [InlineKeyboardButton("🔑 sᴇssɪᴏɴ sᴛʀɪɴɢ", callback_data="edit_auth_session_string", style=ButtonStyle.PRIMARY)]
        if settings.get('session_string'):
            session_row.append(InlineKeyboardButton("🗑 ᴅᴇʟᴇᴛᴇ sᴇssɪᴏɴ", callback_data="delete_session_string", style=ButtonStyle.DANGER))

        buttons = [
            [InlineKeyboardButton("🌐 ᴡᴇʙ ᴜʀʟ", callback_data="edit_auth_website_url", style=ButtonStyle.PRIMARY), InlineKeyboardButton("🔌 ᴀᴘɪ ᴜʀʟ", callback_data="edit_auth_api_url", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("🌐 ʙᴀsᴇ ᴜʀʟ", callback_data="edit_auth_base_url", style=ButtonStyle.PRIMARY), InlineKeyboardButton("🕒 ᴠɪɴᴅᴏᴡ", callback_data="edit_auth_verify_window", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("🔢 ᴀᴄᴄᴇss-ʟɪᴍɪᴛ", callback_data="edit_auth_access_limit", style=ButtonStyle.PRIMARY), InlineKeyboardButton("🤖 ʙᴏᴛ ɴᴀᴍᴇ", callback_data="edit_auth_bot_name", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("🤖 ʙᴏᴛ ᴜsᴇʀɴᴀᴍᴇ", callback_data="edit_auth_bot_username", style=ButtonStyle.PRIMARY), InlineKeyboardButton("🔒 ᴘʀᴏᴛᴇᴄᴛ ᴄᴏɴᴛᴇɴᴛ", callback_data="show_shield_settings", style=ButtonStyle.SECONDARY)],
            [InlineKeyboardButton("👤 ᴏᴡɴᴇʀ ᴛᴀɢ", callback_data="edit_auth_owner_tag", style=ButtonStyle.PRIMARY), InlineKeyboardButton("💸 ᴜᴘɪ ɪᴅ", callback_data="edit_auth_upi_id", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("📦 ᴄᴅɴ ᴜʀʟ", callback_data="edit_auth_cdn_url", style=ButtonStyle.PRIMARY), InlineKeyboardButton("🛡️ ᴄᴀᴘᴛᴄʜᴀ ᴋᴇʏs", callback_data="show_captcha_keys", style=ButtonStyle.SECONDARY)],
            [*session_row],
            [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)]
        ]
        return await edit_panel_message(query, auth_text, InlineKeyboardMarkup(buttons))

    elif data == "show_captcha_keys":
        settings = await db.get_settings(bot_username=client.username)
        text = (
            "<b>🛡️ ᴄᴀᴘᴛᴄʜᴀ ᴄʀᴇᴅᴇɴᴛɪᴀʟs</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔐 <b>ʀ-sɪᴛᴇ:</b> <code>{settings.get('recaptcha_site_key', 'N/A')}</code>\n"
            f"🔐 <b>ʀ-sᴇᴄʀᴇᴛ:</b> <code>{settings.get('recaptcha_secret_key', 'N/A')}</code>\n"
            f"🔐 <b>ᴛ-sɪᴛᴇ:</b> <code>{settings.get('turnstile_site_key', 'N/A')}</code>\n"
            f"🔐 <b>ᴛ-sᴇᴄʀᴇᴛ:</b> <code>{settings.get('turnstile_secret_key', 'N/A')}</code>"
        )
        buttons = [
            [InlineKeyboardButton("ʀ-sɪᴛᴇ", callback_data="edit_auth_recaptcha_site_key", style=ButtonStyle.PRIMARY), InlineKeyboardButton("ʀ-sᴇᴄʀᴇᴛ", callback_data="edit_auth_recaptcha_secret_key", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("ᴛ-sɪᴛᴇ", callback_data="edit_auth_turnstile_site_key", style=ButtonStyle.PRIMARY), InlineKeyboardButton("ᴛ-sᴇᴄʀᴇᴛ", callback_data="edit_auth_turnstile_secret_key", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="show_auth", style=ButtonStyle.SECONDARY)]
        ]
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data == "show_shield_settings" or data.startswith("toggle_protect_"):
        settings = await db.get_settings(bot_username=client.username)

        if data.startswith("toggle_protect_"):
            key = data.replace("toggle_protect_", "")
            current_val = settings.get(key, False)
            new_val = not current_val
            await db.update_setting(key, new_val, bot_username=client.username)
            settings[key] = new_val
            await query.answer(f"Updated {key.replace('protect_content_', '').upper()} -> {'ENABLED 🟢' if new_val else 'DISABLED 🔴'}")

        def get_ico(val):
            return "Enabled 🟢" if val else "Disabled 🔴"

        protect_normal = settings.get('protect_content_normal', False)
        protect_premium = settings.get('protect_content_premium', False)
        protect_auth = settings.get('protect_content_auth', False)

        text = (
            "🔒 <b>˹ ᴘʀᴏᴛᴇᴄᴛ ᴄᴏɴᴛᴇɴᴛ sᴇᴛᴛɪɴɢs ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "Configure forwarding restrictions for different user groups:\n\n"
            f"👤 <b>Normal Users:</b> <code>{get_ico(protect_normal)}</code>\n"
            f"👑 <b>Premium Users:</b> <code>{get_ico(protect_premium)}</code>\n"
            f"👥 <b>Auth/Admins:</b> <code>{get_ico(protect_auth)}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [
                InlineKeyboardButton(f"Normal: {'🟢' if protect_normal else '🔴'}", callback_data="toggle_protect_protect_content_normal", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(f"Premium: {'🟢' if protect_premium else '🔴'}", callback_data="toggle_protect_protect_content_premium", style=ButtonStyle.PRIMARY)
            ],
            [
                InlineKeyboardButton(f"Auth/Admins: {'🟢' if protect_auth else '🔴'}", callback_data="toggle_protect_protect_content_auth", style=ButtonStyle.PRIMARY)
            ],
            [
                InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="show_auth", style=ButtonStyle.SECONDARY)
            ]
        ]
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data.startswith("edit_auth_"):
        field = data.replace("edit_auth_", "")
        try:
            await query.answer(f"ᴜᴘᴅᴀᴛɪɴɢ {field.replace('_', ' ').upper()}...", show_alert=True)
        except Exception:
            pass
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask_prompt = f"📥 <b>ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ᴠᴀʟᴜᴇ ꜰᴏʀ {field.replace('_', ' ').upper()}:</b>"
            if field == "api_url":
                ask_prompt = "«Send the API base URL.»"
            elif field == "base_url":
                ask_prompt = "«Send the Chrome-free secure Base URL.»"
            elif field == "session_string":
                ask_prompt = "📥 <b>ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ᴛᴇʟᴇɢʀᴀᴍ sᴇssɪᴏɴ sᴛʀɪɴɢ:</b>\n\nMust be a valid Pyrogram/WZGram session string. We will test it in-memory before saving."

            ask = await client.ask(query.from_user.id, ask_prompt, timeout=120)
            if not ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input.**")
                return
            if ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ <b>ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
                return

            val = ask.text.strip()
            if field in ['verify_window', 'detect_timer', 'daily_verify_limit', 'app_id', 'owner_id']:
                try: val = int(val)
                except: return await client.send_message(query.from_user.id, "❌ **Invalid Input! Please send a number.**")

            if field == "session_string":
                if val.lower() in ["/remove", "/delete", "/clear", "remove", "delete", "clear"]:
                    await db.update_setting("session_string", "", bot_username=client.username)
                    await client.send_message(query.from_user.id, "✅ <b>sᴇssɪᴏɴ sᴛʀɪɴɢ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ!</b>")
                    # Clear from cached session clients too
                    from plugins.start import SESSION_CLIENTS
                    for k in list(SESSION_CLIENTS.keys()):
                        try:
                            await SESSION_CLIENTS[k].stop()
                        except:
                            pass
                    SESSION_CLIENTS.clear()
                    return

                # Real-time validation of session string
                testing_msg = await client.send_message(query.from_user.id, "⏳ <b>ᴠᴀʟɪᴅᴀᴛɪɴɢ sᴇssɪᴏɴ sᴛʀɪɴɢ...</b>\n\nTesting connection to Telegram in-memory.")
                from pyrogram import Client as PyClient
                import config
                temp_c = PyClient(
                    name=f"test_session_{random.randint(1000, 9999)}",
                    api_id=config.APP_ID,
                    api_hash=config.API_HASH,
                    session_string=val,
                    in_memory=True
                )
                try:
                    await temp_c.start()
                    me = await temp_c.get_me()
                    await temp_c.stop()
                    await testing_msg.edit_text(f"✅ <b>sᴇssɪᴏɴ ᴠᴀʟɪᴅ!</b>\n\nConnected successfully as <b>@{me.username or me.first_name}</b>.")
                except Exception as e:
                    try: await temp_c.stop()
                    except: pass
                    await testing_msg.edit_text(f"❌ <b>ɪɴᴠᴀʟɪᴅ sᴇssɪᴏɴ sᴛʀɪɴɢ!</b>\n\nValidation failed: <code>{str(e)}</code>")
                    return

            await db.update_setting(field, val, bot_username=client.username)
            await client.send_message(query.from_user.id, f"✅ <b>{field.replace('_', ' ').replace('edit auth ', '').title()} successfully updated!</b>")
        except asyncio.TimeoutError:
            await client.send_message(query.from_user.id, "⏰ <b>Request timed out.</b>")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Edit failed:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings(bot_username=client.username)
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return
    elif data.startswith("set_captcha_"):
        cap_type = data.replace("set_captcha_", "")
        settings = await db.get_settings(bot_username=client.username)
        db_key = f"use_{cap_type}"
        new_val = not settings.get(db_key, False)
        await db.update_setting(db_key, new_val, bot_username=client.username)
        await query.answer(f"{cap_type.upper()} {'ENABLED' if new_val else 'DISABLED'}")

    elif data == "manage_images":
        settings = await db.get_settings(bot_username=client.username)
        banners = settings.get('anime_banners', ANIME_BANNERS)
        text = "🖼️ **Anime Banners Management**\n\n"
        buttons = []
        for i, url in enumerate(banners):
            text += f"• `{i+1}`: {url[:30]}...\n"
            buttons.append([InlineKeyboardButton(f"🗑 Delete #{i+1}", callback_data=f"del_banner_{i}", style=ButtonStyle.DANGER)])

        buttons.append([InlineKeyboardButton("➕ ᴀᴅᴅ ʙᴀɴɴᴇʀ ᴜʀʟ", callback_data="add_banner", style=ButtonStyle.SUCCESS)])
        buttons.append([InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)])
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data == "add_banner":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask = await client.ask(query.from_user.id, "🖼️ <b>sᴇɴᴅ ɴᴇᴡ ɪᴍᴀɢᴇ (ʙᴀɴɴᴇʀ) ᴜʀʟ (sᴜᴘᴘᴏʀᴛs sɪɴɢʟᴇ/ʙᴜʟᴋ ᴜʀʟs):</b>", timeout=60)
            if not ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input.**")
                return
            if ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ <b>ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
            else:
                raw_urls = re.split(r'[\s,\n]+', ask.text.strip())
                urls = [u.strip() for u in raw_urls if u.strip().startswith("http")]
                if not urls:
                    await client.send_message(query.from_user.id, "❌ <b>No valid URLs found. Make sure they start with http/https.</b>")
                    return
                settings = await db.get_settings(bot_username=client.username)
                banners = settings.get('anime_banners', list(ANIME_BANNERS))
                banners.extend(urls)
                await db.update_setting("anime_banners", banners, bot_username=client.username)
                await client.send_message(query.from_user.id, f"✅ <b>{len(urls)} banner(s) added successfully!</b>")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Banner add failed:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings(bot_username=client.username)
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return

    elif data.startswith("del_banner_"):
        idx = int(data.replace("del_banner_", ""))
        settings = await db.get_settings(bot_username=client.username)
        banners = settings.get('anime_banners', list(ANIME_BANNERS))
        if 0 <= idx < len(banners):
            removed = banners.pop(idx)
            await db.update_setting("anime_banners", banners, bot_username=client.username)
            await query.answer(f"Banner removed", show_alert=True)
        query.data = "manage_images"
        return await panel_callback(client, query)

    elif data == "manage_shorteners":
        settings = await db.get_settings(bot_username=client.username)
        shorteners = settings.get('shorteners', [])
        text = "🔗 <b>˹ sʜᴏʀᴛᴇɴᴇʀ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ˼</b>\n\n"
        if not shorteners:
            text += "<i>ɴᴏ ᴄᴜsᴛᴏᴍ sʜᴏʀᴛᴇɴᴇʀs ᴄᴏɴꜰɪɢᴜʀᴇᴅ.</i>\n"
        else:
            for i, short in enumerate(shorteners):
                method = short.get('verification_method', 'global')
                text += f"• <b>sʜᴏʀᴛ {i+1}</b> → <code>{short['url']}</code> (ᴍᴇᴛʜᴏᴅ: <code>{method}</code>)\n"

        buttons = []
        for i in range(len(shorteners)):
            buttons.append([
                InlineKeyboardButton(f"⚙️ sʜᴏʀᴛ {i+1}", callback_data=f"conf_short_{i}", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(f"🗑 ᴅᴇʟᴇᴛᴇ", callback_data=f"del_short_{i}", style=ButtonStyle.DANGER)
            ])

        buttons.append([InlineKeyboardButton("➕ ᴀᴅᴅ sʜᴏʀᴛᴇɴᴇʀ", callback_data="add_shortener", style=ButtonStyle.SUCCESS)])
        buttons.append([InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)])
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data.startswith("conf_short_"):
        idx = int(data.replace("conf_short_", ""))
        settings = await db.get_settings(bot_username=client.username)
        shorteners = settings.get('shorteners', [])
        if 0 <= idx < len(shorteners):
            short = shorteners[idx]
            current_method = short.get('verification_method', 'global')
            text = (
                f"⚙️ <b>˹ ᴄᴏɴꜰɪɢᴜʀᴇ sʜᴏʀᴛᴇɴᴇʀ ˼</b>\n\n"
                f"• <b>ᴜʀʟ:</b> <code>{short['url']}</code>\n"
                f"• <b>ᴄᴜʀʀᴇɴᴛ ᴍᴇᴛʜᴏᴅ:</b> <code>{current_method}</code>\n\n"
                f"<i>sᴇʟᴇᴄᴛ ᴀ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴍᴇᴛʜᴏᴅ ʙᴇʟᴏᴡ:</i>"
            )

            def get_check(m):
                return " ✅" if current_method == m else ""

            buttons = [
                [
                    InlineKeyboardButton(f"📱 Mini App{get_check('mini_app')}", callback_data=f"set_shmethod_{idx}_mini_app", style=ButtonStyle.PRIMARY),
                    InlineKeyboardButton(f"📱 Browser{get_check('browser')}", callback_data=f"set_shmethod_{idx}_browser", style=ButtonStyle.PRIMARY)
                ],
                [
                    InlineKeyboardButton(f"🔌 API URL{get_check('api_url')}", callback_data=f"set_shmethod_{idx}_api_url", style=ButtonStyle.PRIMARY),
                    InlineKeyboardButton(f"🌐 Web URL{get_check('web_url')}", callback_data=f"set_shmethod_{idx}_web_url", style=ButtonStyle.PRIMARY)
                ],
                [
                    InlineKeyboardButton(f"🌐 Own Browser{get_check('own_browser')}", callback_data=f"set_shmethod_{idx}_own_browser", style=ButtonStyle.PRIMARY),
                    InlineKeyboardButton(f"🌐 Global Fallback{get_check('global')}", callback_data=f"set_shmethod_{idx}_global", style=ButtonStyle.SECONDARY)
                ],
                [
                    InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="manage_shorteners", style=ButtonStyle.SECONDARY)
                ]
            ]
            return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data.startswith("set_shmethod_"):
        # format: set_shmethod_{idx}_{method}
        parts = data.replace("set_shmethod_", "").split("_", 1)
        idx = int(parts[0])
        method = parts[1]

        settings = await db.get_settings(bot_username=client.username)
        shorteners = settings.get('shorteners', [])
        if 0 <= idx < len(shorteners):
            shorteners[idx]['verification_method'] = method
            await db.update_setting("shorteners", shorteners, bot_username=client.username)
            await query.answer(f"Shortener method set to {method.upper()}!")

        query.data = f"conf_short_{idx}"
        return await panel_callback(client, query)

    elif data == "add_shortener":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask_text = (
                "➕ **˹ ᴀᴅᴅ sʜᴏʀᴛᴇɴᴇʀ ˼**\n\n"
                "ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ sʜᴏʀᴛᴇɴᴇʀ ᴅᴇᴛᴀɪʟs ɪɴ ᴛʜᴇ ꜰᴏʟʟᴏᴡɪɴɢ ꜰᴏʀᴍᴀᴛ:\n\n"
                "<code>url: arolinks.com\n"
                "Key: YOUR_API_KEY</code>\n\n"
                "⚠️ **ᴀᴄᴄᴇᴘᴛs ᴏɴʟʏ ᴛʜɪs ꜰᴏʀᴍᴀᴛ.**"
            )
            ask = await client.ask(query.from_user.id, ask_text, timeout=120)
            if not ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input. Format required.**")
                return
            if ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ **Cancelled.**")
            else:
                pattern = r"url:\s*(?P<url>\S+)\s*Key:\s*(?P<key>\S+)"
                match = re.search(pattern, ask.text, re.IGNORECASE | re.MULTILINE)
                if match:
                    url = match.group("url")
                    key = match.group("key")
                    await db.add_shortener(url, key, bot_username=client.username)
                    await client.send_message(query.from_user.id, "✅ **Shortener Added Successfully!**")
                else:
                    await client.send_message(query.from_user.id, "❌ **Invalid Format!**\n\nᴘʟᴇᴀsᴇ ᴜsᴇ:\nurl: domain.com\nKey: YOUR_API_KEY")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Shortener add failed:** `{e}`\n\n`{traceback.format_exc()}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings(bot_username=client.username)
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return

    elif data.startswith("del_short_"):
        idx = int(data.replace("del_short_", ""))
        if await db.del_shortener(idx, bot_username=client.username):
            await query.answer("Shortener removed", show_alert=True)
        query.data = "manage_shorteners"
        return await panel_callback(client, query)

    elif data == "manage_videos":
        settings = await db.get_settings(bot_username=client.username)
        videos = settings.get('video_banners', [])
        text = "🎬 <b>˹ ᴠɪᴅᴇᴏ ᴄᴏɴꜰɪɢ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ˼</b>\n\n"
        if not videos:
            text += "<i>ɴᴏ ᴄᴜsᴛᴏᴍ ᴠɪᴅᴇᴏs ᴄᴏɴꜰɪɢᴜʀᴇᴅ.</i>\n"
        else:
            for i, url in enumerate(videos):
                text += f"• <b>ᴠɪᴅᴇᴏ {i+1}</b> → <code>{url[:30]}...</code>\n"

        buttons = []
        for i in range(len(videos)):
            buttons.append([InlineKeyboardButton(f"🗑 ᴅᴇʟᴇᴛᴇ ᴠɪᴅᴇᴏ {i+1}", callback_data=f"del_video_banner_{i}", style=ButtonStyle.DANGER)])

        buttons.append([InlineKeyboardButton("➕ ᴀᴅᴅ ᴠɪᴅᴇᴏ ᴜʀʟ", callback_data="add_video_banner", style=ButtonStyle.SUCCESS)])
        buttons.append([InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)])
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data == "add_video_banner":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask = await client.ask(query.from_user.id, "🎬 **Send direct Video URL (supports single/bulk URLs):**", timeout=120)
            if not ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input.**")
                return
            if ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ **Cancelled.**")
            else:
                raw_urls = re.split(r'[\s,\n]+', ask.text.strip())
                urls = [u.strip() for u in raw_urls if u.strip().startswith("http")]
                if not urls:
                    await client.send_message(query.from_user.id, "❌ <b>No valid URLs found. Make sure they start with http/https.</b>")
                    return
                settings = await db.get_settings()
                videos = settings.get('video_banners', [])
                videos.extend(urls)
                await db.update_setting("video_banners", videos)
                await client.send_message(query.from_user.id, f"✅ <b>{len(urls)} video(s) added successfully!</b>")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Video add failed:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings(bot_username=client.username)
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return

    elif data.startswith("del_video_banner_"):
        idx = int(data.replace("del_video_banner_", ""))
        if await db.del_video_banner(idx, bot_username=client.username):
            await query.answer("Video removed", show_alert=True)
        query.data = "manage_videos"
        return await panel_callback(client, query)

    elif data == "manage_helpers":
        from bot import Bot
        helpers = await db.get_helper_bots()
        text = (
            "🤖 <b>˹ ʜᴇʟᴘᴇʀ ʙᴏᴛ ᴍᴀɴᴀɢᴇʀ ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 ᴛᴏᴛᴀʟ ʜᴇʟᴘᴇʀ ʙᴏᴛs: <b>{len(helpers)}</b>\n\n"
        )
        buttons = []
        if not helpers:
            text += "<i>ɴᴏ ʜᴇʟᴘᴇʀ ʙᴏᴛs ᴀᴅᴅᴇᴅ ʏᴇᴛ.</i>"
        else:
            for i, h in enumerate(helpers):
                text += f"{i+1}. @{h['username']}\n"
                # Use bot ID for deletion security instead of full token
                bot_id = h['token'].split(":")[0]
                buttons.append([InlineKeyboardButton(f"🗑 Delete @{h['username']}", callback_data=f"del_helper_{bot_id}", style=ButtonStyle.DANGER)])

        buttons.append([InlineKeyboardButton("➕ ᴀᴅᴅ ʜᴇʟᴘᴇʀ ʙᴏᴛ", callback_data="add_helper", style=ButtonStyle.SUCCESS)])
        buttons.append([InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)])
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data == "add_helper":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask = await client.ask(query.from_user.id, "🤖 <b>sᴇɴᴅ ʜᴇʟᴘᴇʀ ʙᴏᴛ ᴛᴏᴋᴇɴ:</b>", timeout=60)
            if not ask.text or ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ ᴄᴀɴᴄᴇʟʟᴇᴅ.")
            else:
                token = ask.text.strip()
                # Validate token
                from pyrogram import Client as PyClient
                temp_client = PyClient(name="temp", api_id=config.APP_ID, api_hash=config.API_HASH, bot_token=token, in_memory=True)
                try:
                    await temp_client.start()
                    me = await temp_client.get_me()
                    await temp_client.stop()

                    # Check duplicates
                    existing = await db.get_helper_bots()
                    if any(h['token'] == token for h in existing):
                        await client.send_message(query.from_user.id, "❌ ᴛʜɪs ʙᴏᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ.")
                    else:
                        await db.add_helper_bot(token, me.username)
                        from bot import Bot
                        # Find the main bot instance to call start_helper_bot
                        main_bot = next(iter(Bot.instances.values()), None)
                        if main_bot:
                            await main_bot.start_helper_bot(token)
                        await client.send_message(query.from_user.id, f"✅ ʙᴏᴛ @{me.username} ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssꜰᴜʟʟʏ!")
                except Exception as e:
                    await client.send_message(query.from_user.id, f"❌ ɪɴᴠᴀʟɪᴅ ᴛᴏᴋᴇɴ ᴏʀ ʙᴏᴛ API ᴇʀʀᴏʀ: {e}")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ ᴇʀʀᴏʀ: {e}")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings(bot_username=client.username)
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return

    elif data.startswith("del_helper_"):
        bot_id = data.replace("del_helper_", "").strip()
        helpers = await db.get_helper_bots()
        target_token = next((h['token'] for h in helpers if h['token'].startswith(f"{bot_id}:")), None)

        if target_token:
            await db.del_helper_bot(target_token)
            from bot import Bot
            main_bot = next(iter(Bot.instances.values()), None)
            if main_bot:
                await main_bot.stop_helper_bot(target_token)
            await query.answer("Helper bot removed.", show_alert=True)
        else:
            await query.answer("Helper bot not found.", show_alert=True)
        query.data = "manage_helpers"
        return await panel_callback(client, query)

    elif data == "manage_proxies":
        from proxy_manager import proxy_manager, mask_proxy
        proxies = proxy_manager.list_proxies()
        text = (
            "🌐 <b>˹ ᴘʀᴏxʏ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>ᴛᴏᴛᴀʟ sᴀᴠᴇᴅ ᴘʀᴏxɪᴇs:</b> <code>{len(proxies)}</code>\n"
            f"🔄 <b>ʀᴏᴛᴀᴛɪᴏɴ sᴛʀᴀᴛᴇɢʏ:</b> <code>{proxy_manager.rotation_strategy.replace('_', ' ').upper()}</code>\n\n"
        )
        if not proxies:
            text += "<i>ɴᴏ ᴘʀᴏxɪᴇs ᴄᴏɴꜰɪɢᴜʀᴇᴅ.</i>\n"
        else:
            for i, p in enumerate(proxies):
                masked = mask_proxy(p['proxy'])
                status = p.get('last_status') or "Not Checked 🔘"
                enabled_status = "🟢" if p.get('enabled') else "🔴"
                text += f"• <b>Proxy {i+1} {enabled_status}:</b> <code>{masked}</code>\n"
                text += f"  Status: <code>{status}</code>\n\n"

        buttons = [
            [
                InlineKeyboardButton("➕ ᴀᴅᴅ ᴘʀᴏxʏ", callback_data="add_proxy_prompt", style=ButtonStyle.SUCCESS),
                InlineKeyboardButton("🗑 ᴅᴇʟᴇᴛᴇ ᴘʀᴏxʏ", callback_data="delete_proxy_list", style=ButtonStyle.DANGER)
            ],
            [
                InlineKeyboardButton("🔄 ᴄʜᴇᴄᴋ ᴘʀᴏxɪᴇs", callback_data="check_proxies_act", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(f"⚙️ sᴛʀᴀᴛᴇɢʏ: {proxy_manager.rotation_strategy.replace('_', ' ').upper()}", callback_data="toggle_proxy_strategy", style=ButtonStyle.SECONDARY)
            ],
            [
                InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)
            ]
        ]
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data == "add_proxy_prompt":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask_text = (
                "🌐 <b>˹ ᴀᴅᴅ ᴘʀᴏxʏ ˼</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
                "Please send the proxy credentials in this format:\n"
                "<code>http://username:password@ip:port</code>\n\n"
                "Example:\n"
                "<code>http://user123:pass123@192.168.1.100:8080</code>\n\n"
                "⚠️ Must start with http://, containing username, password, host, and port."
            )
            ask = await client.ask(query.from_user.id, ask_text, timeout=120)
            if not ask.text:
                await client.send_message(query.from_user.id, "❌ **Invalid input. Text required.**")
                return
            if ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ **Cancelled.**")
            else:
                proxy_str = ask.text.strip()
                from proxy_manager import proxy_manager
                success, msg = proxy_manager.add_proxy(proxy_str)
                if success:
                    await client.send_message(query.from_user.id, f"✅ {msg}")
                else:
                    await client.send_message(query.from_user.id, f"❌ **Addition Failed:** {msg}")
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Error:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings(bot_username=client.username)
            cap = get_panel_caption(settings)
            markup = get_panel_markup(settings)
            await client.send_message(query.from_user.id, text=cap, reply_markup=markup)
            return

    elif data == "delete_proxy_list":
        from proxy_manager import proxy_manager, mask_proxy
        proxies = proxy_manager.list_proxies()
        text = (
            "🗑️ <b>˹ ᴅᴇʟᴇᴛᴇ ᴘʀᴏxʏ ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "Select a proxy below to delete it permanently:"
        )
        buttons = []
        for p in proxies:
            masked = mask_proxy(p['proxy'])
            buttons.append([InlineKeyboardButton(f"🗑️ {masked}", callback_data=f"del_proxy_act_{p['id']}", style=ButtonStyle.DANGER)])

        buttons.append([InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="manage_proxies", style=ButtonStyle.SECONDARY)])
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data.startswith("del_proxy_act_"):
        proxy_id = int(data.replace("del_proxy_act_", ""))
        from proxy_manager import proxy_manager
        success = proxy_manager.delete_proxy(proxy_id)
        if success:
            await query.answer("Proxy deleted permanently!", show_alert=True)
        else:
            await query.answer("Failed to delete proxy.", show_alert=True)
        query.data = "manage_proxies"
        return await panel_callback(client, query)

    elif data == "check_proxies_act":
        from proxy_manager import proxy_manager
        proxies = proxy_manager.list_proxies()
        if not proxies:
            return await query.answer("No proxies saved to check.", show_alert=True)

        await query.answer("Checking all proxies asynchronously... Please wait.", show_alert=True)
        tasks = [proxy_manager.check_proxy(p['proxy']) for p in proxies]
        await asyncio.gather(*tasks)
        try:
            await query.answer("Proxy check complete!", show_alert=True)
        except Exception:
            pass
        query.data = "manage_proxies"
        return await panel_callback(client, query)

    elif data == "toggle_proxy_strategy":
        from proxy_manager import proxy_manager
        current = proxy_manager.rotation_strategy
        new_strategy = "round_robin" if current == "random" else "random"
        proxy_manager.set_rotation_strategy(new_strategy)
        await query.answer(f"Rotation strategy set to: {new_strategy.replace('_', ' ').upper()}", show_alert=True)
        query.data = "manage_proxies"
        return await panel_callback(client, query)

    elif data == "manage_custom_caption":
        settings = await db.get_settings(bot_username=client.username)
        caption_active = settings.get('custom_caption_active', True)
        caption_text = settings.get('custom_caption_text', "Not Set")

        status_ico = "🟢 Enabled" if caption_active else "🔴 Disabled"

        text = (
            "📝 <b>˹ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ sᴇᴛᴛɪɴɢs ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>sᴛᴀᴛᴜs:</b> <code>{status_ico}</code>\n\n"
            f"🛡️ <b>ᴄᴜʀʀᴇɴᴛ ᴄᴀᴘᴛɪᴏɴ ᴘʀᴇᴠɪᴇᴡ:</b>\n"
            f"<blockquote>{caption_text}</blockquote>\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [
                InlineKeyboardButton("➕ sᴇᴛ / ᴇᴅɪᴛ", callback_data="set_caption_prompt", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton("🗑 ʀᴇsᴇᴛ / ᴅᴇʟᴇᴛᴇ", callback_data="reset_custom_caption", style=ButtonStyle.DANGER)
            ],
            [
                InlineKeyboardButton(f"🚀 Tᴏɢɢʟᴇ: {'🟢' if caption_active else '🔴'}", callback_data="toggle_custom_caption", style=ButtonStyle.SUCCESS)
            ],
            [
                InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)
            ]
        ]
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data == "toggle_custom_caption":
        settings = await db.get_settings(bot_username=client.username)
        new_val = not settings.get('custom_caption_active', True)
        await db.update_setting('custom_caption_active', new_val, bot_username=client.username)
        await query.answer(f"Custom Caption -> {'ENABLED 🟢' if new_val else 'DISABLED 🔴'}")
        query.data = "manage_custom_caption"
        return await panel_callback(client, query)

    elif data == "reset_custom_caption":
        await db.update_setting('custom_caption_text', "", bot_username=client.username)
        await query.answer("Custom Caption reset/deleted!", show_alert=True)
        query.data = "manage_custom_caption"
        return await panel_callback(client, query)

    elif data == "set_caption_prompt":
        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask_text = (
                "📝 <b>˹ sᴇᴛ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ˼</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
                "Please send the new custom caption exactly as you want it to appear.\n\n"
                "You can format it natively using Telegram formatting (bold, links, spoiler, etc.) or type raw HTML/Markdown tags.\n\n"
                "⚠️ Any Telegram-supported formatting is fully preserved."
            )
            ask = await client.ask(query.from_user.id, ask_text, timeout=180)
            if not ask.text and not ask.caption:
                await client.send_message(query.from_user.id, "❌ **Invalid input. Caption text is required.**")
                return
            if ask.text and ask.text.lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ **Cancelled.**")
            else:
                raw_text = ask.text or ask.caption
                html_text = ask.text.html if ask.text else ask.caption.html

                # Detect if the admin typed raw HTML tags explicitly in plain text
                html_tags = ["<b>", "</b>", "<i>", "</i>", "<code>", "</code>", "<u>", "</u>", "<s>", "</s>", "<strike>", "</strike>", "<spoiler>", "</spoiler>", "<blockquote>", "</blockquote>", "<a "]
                if any(tag in raw_text for tag in html_tags):
                    final_caption = raw_text
                else:
                    final_caption = html_text

                # Store the custom caption
                await db.update_setting('custom_caption_text', final_caption, bot_username=client.username)

                # Show confirmation with preview
                conf_text = (
                    "✅ <b>Custom Caption Saved successfully!</b>\n\n"
                    "📝 <b>Preview:</b>\n"
                    f"<blockquote>{final_caption}</blockquote>"
                )
                await client.send_message(query.from_user.id, conf_text)
        except Exception as e:
            await client.send_message(query.from_user.id, f"⚠️ **Failed to set caption:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings(bot_username=client.username)
            cap = get_panel_caption(settings)
            markup = get_panel_markup(settings)
            await client.send_message(query.from_user.id, text=cap, reply_markup=markup)
            return

    elif data == "manage_verify_log":
        dests = await db.get_verify_log_destinations()
        channel_count = sum(1 for d in dests if d.get('type') == 'channel')
        group_count = sum(1 for d in dests if d.get('type') == 'group')

        text = (
            "📝 <b>˹ ᴠᴇʀɪꜰʏ ʟᴏɢ ᴅᴇsᴛɪɴᴀᴛɪᴏɴs ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>Configured:</b> <code>{len(dests)}/4</code>\n"
            f"📢 <b>Channels:</b> <code>{channel_count}/2</code> | 👥 <b>Groups:</b> <code>{group_count}/2</code>\n\n"
        )
        buttons = []
        if not dests:
            text += "<i>No Verify Log destinations configured.</i>\n\n"
        else:
            for d in dests:
                icon = "📢" if d.get('type') == 'channel' else "👥"
                text += f"• {icon} <b>{d.get('title')}</b>\n  ID: <code>{d.get('chat_id')}</code>\n\n"
                buttons.append([InlineKeyboardButton(f"🗑 Delete {d.get('title')[:20]}", callback_data=f"del_vlog_{d.get('chat_id')}", style=ButtonStyle.DANGER)])

        if len(dests) < 4:
            buttons.append([InlineKeyboardButton("➕ Add Channel / Group", callback_data="set_verify_log_channel", style=ButtonStyle.SUCCESS)])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)])
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    elif data.startswith("del_vlog_"):
        cid = int(data.replace("del_vlog_", ""))
        await db.del_verify_log_destination(cid)
        await query.answer("Destination removed successfully!", show_alert=True)
        query.data = "manage_verify_log"
        return await panel_callback(client, query)

    elif data == "set_verify_log_channel":
        dests = await db.get_verify_log_destinations()
        if len(dests) >= 4:
            return await query.answer("Maximum 4 total destinations already configured!", show_alert=True)

        await query.message.delete()
        db.busy_admins.add(query.from_user.id)
        try:
            ask_prompt = (
                "📝 <b>˹ ᴀᴅᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ʟᴏɢ ᴅᴇsᴛɪɴᴀᴛɪᴏɴ ˼</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
                "Send Channel ID or Group ID.\n\n"
                "Example:\n"
                "<code>-1001234567890</code>\n\n"
                "⚠️ <b>Limits:</b> Max 2 Channels, Max 2 Groups (Max 4 Total).\n"
                "Main bot must be added as administrator."
            )
            ask = await client.ask(query.from_user.id, ask_prompt, timeout=120)
            if not ask.text or ask.text.strip().lower() == "/cancel":
                await client.send_message(query.from_user.id, "❌ **Action Cancelled.**")
                return

            cid_str = ask.text.strip()
            try:
                cid = int(cid_str)
            except ValueError:
                await client.send_message(query.from_user.id, "❌ **Invalid Chat ID! Must be a numeric value starting with -100.**")
                return

            from pyrogram.enums import ChatType, ChatMemberStatus
            try:
                chat = await client.get_chat(cid)
            except Exception as e:
                await client.send_message(query.from_user.id, f"❌ **Telegram API Error (Chat inaccessible):** `{e}`\n\nPlease ensure main bot @{client.username} is added to the chat.")
                return

            if chat.type == ChatType.CHANNEL:
                chat_type = "channel"
            elif chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                chat_type = "group"
            else:
                await client.send_message(query.from_user.id, f"❌ **Unsupported Chat Type:** `{chat.type}`. Must be a channel or group/supergroup.")
                return

            # Verify admin status and permissions
            try:
                member = await client.get_chat_member(cid, "me")
                if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    await client.send_message(query.from_user.id, f"❌ **Bot is not an administrator!** Main bot @{client.username} must be made an admin in `{chat.title}`.")
                    return

                if member.status == ChatMemberStatus.ADMINISTRATOR:
                    privs = member.privileges
                    if chat_type == "channel" and privs and not privs.can_post_messages:
                        await client.send_message(query.from_user.id, "❌ **Bot is missing 'can_post_messages' permission in channel!**")
                        return
                    elif chat_type == "group" and privs and not privs.can_send_messages:
                        await client.send_message(query.from_user.id, "❌ **Bot is missing 'can_send_messages' permission in group!**")
                        return
            except Exception as e:
                await client.send_message(query.from_user.id, f"❌ **Permission check failed:** `{e}`")
                return

            # Test message validation & immediate deletion
            try:
                test_msg = await client.send_message(cid, "<b>⚙️ Verify Log Test Message</b>\n\nTesting logging permissions...")
                await asyncio.sleep(0.5)
                await test_msg.delete()
            except Exception as e:
                await client.send_message(query.from_user.id, f"❌ **Test message validation failed:** `{e}`")
                return

            # Save destination
            success, msg = await db.add_verify_log_destination(cid, chat_type, chat.title or str(cid))
            if success:
                await client.send_message(
                    query.from_user.id,
                    f"✅ **Verify Log Destination Configured!**\n\n"
                    f"• <b>Title:</b> {chat.title}\n"
                    f"• <b>ID:</b> <code>{cid}</code>\n"
                    f"• <b>Type:</b> <code>{chat_type.upper()}</code>"
                )
            else:
                await client.send_message(query.from_user.id, f"❌ **Addition Failed:** {msg}")
        except Exception as e:
            await client.send_message(query.from_user.id, f"❌ **Failed to add destination:** `{e}`")
        finally:
            db.busy_admins.discard(query.from_user.id)
            settings = await db.get_settings(bot_username=client.username)
            await client.send_message(query.from_user.id, get_panel_caption(settings), reply_markup=get_panel_markup(settings))
            return

    elif data == "manage_verification" or data.startswith("set_ver_"):
        settings = await db.get_settings(bot_username=client.username)

        if data == "set_ver_toggle":
            new_val = not settings.get('verification_enabled', True)
            await db.update_setting('verification_enabled', new_val, bot_username=client.username)
            settings['verification_enabled'] = new_val
            await query.answer(f"Verification -> {'ENABLED 🟢' if new_val else 'DISABLED 🔴'}")
        elif data.startswith("set_ver_method_"):
            method = data.replace("set_ver_method_", "")
            await db.update_setting('verification_method', method, bot_username=client.username)
            settings['verification_method'] = method
            await query.answer(f"Method set to {method.upper()}")
        elif data.startswith("set_ver_obmode_"):
            obmode = data.replace("set_ver_obmode_", "")
            await db.update_setting('own_browser_mode', obmode, bot_username=client.username)
            settings['own_browser_mode'] = obmode
            await query.answer(f"Own Browser Mode set to {obmode.upper()}")
        elif data.startswith("set_ver_bmode_"):
            bmode = data.replace("set_ver_bmode_", "")
            await db.update_setting('browser_mode', bmode, bot_username=client.username)
            settings['browser_mode'] = bmode
            await query.answer(f"Browser Mode set to {bmode.upper()}")

        ver_enabled = settings.get('verification_enabled', True)
        ver_method = settings.get('verification_method', 'mini_app')
        ob_mode = settings.get('own_browser_mode', 'proxy')
        b_mode = settings.get('browser_mode', 'normal')

        status_ico = "🟢 Enabled" if ver_enabled else "🔴 Disabled"
        method_ico = {
            'api_url': '🔌 API URL',
            'web_url': '🌐 Web URL',
            'mini_app': '📱 Mini App',
            'browser': f'📱 Browser ({b_mode.upper()})',
            'own_browser': f'🌐 Own Browser ({ob_mode.upper()})'
        }.get(ver_method, '📱 Mini App')

        text = (
            "🛡️ <b>˹ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ sᴇᴛᴛɪɴɢs ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>sᴛᴀᴛᴜs:</b> <code>{status_ico}</code>\n"
            f"⚙️ <b>ᴍᴇᴛʜᴏᴅ:</b> <code>{method_ico}</code>\n\n"
            "Configure verification status and the user-facing verification gateway method:\n\n"
            "• <b>API URL:</b> Uses configured shortener API URL for routing.\n"
            "• <b>Web URL:</b> Uses main Web URL for external browser verification.\n"
            "• <b>Mini App:</b> Uses the seamless in-app Telegram Mini App interface.\n"
            "• <b>Browser:</b> Runs entirely within the Telegram Mini App and does not launch external browser.\n"
            "• <b>Own Browser:</b> Runs in a custom browser built into the Base URL independent of Telegram Mini App.\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

        def get_check(m):
            return " ✅" if ver_method == m else ""

        buttons = [
            [
                InlineKeyboardButton(f"🚀 Status: {'🟢 Enabled' if ver_enabled else '🔴 Disabled'}", callback_data="set_ver_toggle", style=ButtonStyle.SUCCESS)
            ],
            [
                InlineKeyboardButton(f"🔌 API URL{get_check('api_url')}", callback_data="set_ver_method_api_url", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(f"🌐 Web URL{get_check('web_url')}", callback_data="set_ver_method_web_url", style=ButtonStyle.PRIMARY)
            ],
            [
                InlineKeyboardButton(f"📱 Mini App{get_check('mini_app')}", callback_data="set_ver_method_mini_app", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(f"📱 Browser{get_check('browser')}", callback_data="set_ver_method_browser", style=ButtonStyle.PRIMARY)
            ],
            [
                InlineKeyboardButton(f"🌐 Own Browser{get_check('own_browser')}", callback_data="set_ver_method_own_browser", style=ButtonStyle.PRIMARY)
            ]
        ]

        if ver_method == "own_browser":
            check_proxy = " ✅" if ob_mode == "proxy" else ""
            check_normal = " ✅" if ob_mode == "normal" else ""
            buttons.append([
                InlineKeyboardButton(f"🌐 With Proxy & Iframe{check_proxy}", callback_data="set_ver_obmode_proxy", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(f"🌐 Normal{check_normal}", callback_data="set_ver_obmode_normal", style=ButtonStyle.PRIMARY)
            ])
        elif ver_method == "browser":
            check_proxy = " ✅" if b_mode == "proxy" else ""
            check_normal = " ✅" if b_mode == "normal" else ""
            buttons.append([
                InlineKeyboardButton(f"📱 With Proxy & Iframe{check_proxy}", callback_data="set_ver_bmode_proxy", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(f"📱 Normal{check_normal}", callback_data="set_ver_bmode_normal", style=ButtonStyle.PRIMARY)
            ])

        buttons.append([
            InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="refresh_panel", style=ButtonStyle.SECONDARY)
        ])
        return await edit_panel_message(query, text, InlineKeyboardMarkup(buttons))

    settings = await db.get_settings(bot_username=client.username)
    await edit_panel_message(query, get_panel_caption(settings), get_panel_markup(settings))
