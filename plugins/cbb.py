#
# Copyright (C) 2025 by AniZoneFlix@AniZoneFlix, < https://github.com/AniZoneFlix >.
#
# This file is part of < https://t.me/AniZoneFlix > project,
# and is released under the MIT License.
# Please see < https://t.me/AniZoneFlix/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram import Client 
from config import *
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery
from database.database import *
from helper_func import *
from helper_func import InlineKeyboardButton, random_button_style, get_banners, send_media
from utils.formatter import RichText

@Client.on_callback_query(filters.regex(r"^(help|about|start|premium|close|fsub_back|ck|rfs_|car_idx:|car_dl_all:)"))
async def cb_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if await db.is_user_banned(user_id):
        return await query.answer("🚫 ACCESS DENIED: You are permanently banned for policy violations.", show_alert=True)

    data = query.data

    # Allow non-content callbacks to proceed without sub check
    if any(data.startswith(x) for x in ["help", "about", "start", "premium", "close", "ck", "car_idx", "car_dl_all"]):
        pass
    elif not await is_subscribed(client, user_id):
        return await query.answer("⚠️ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʀᴇǫᴜɪʀᴇᴅ! Join all channels first.", show_alert=True)

    if data == "help":
        # REWRITTEN HELP MENU
        text = (
            "━━━━━━━━━━━━━━━━━━━\n"
            "💎 <b>˹ ᴀɴɪᴢᴏɴᴇꜰʟɪx sᴜᴘᴘᴏʀᴛ ˼</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>ʜᴏᴡ ᴛᴏ ᴜsᴇ:</b>\n"
            "<blockquote>1. sᴇɴᴅ ᴀɴʏ ꜰɪʟᴇ ᴛᴏ ᴛʜᴇ ʙᴏᴛ. 📁\n"
            "2. ɢᴇᴛ ʏᴏᴜʀ ᴘʀᴏᴛᴇᴄᴛᴇᴅ ʟɪɴᴋ. 🔗\n"
            "3. sʜᴀʀᴇ ᴡɪᴛʜ ʏᴏᴜʀ ᴀᴜᴅɪᴇɴᴄᴇ! 🚀</blockquote>\n\n"
            "🛠 <b>ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:</b>\n"
            "• /batch — ᴄʀᴇᴀᴛᴇ ʙᴜʟᴋ ʟɪɴᴋs 📦\n"
            "• /panel — ᴄᴏɴꜰɪɢᴜʀᴇ sᴇᴄᴜʀɪᴛʏ ⚙️\n"
            "• /stats — sʏsᴛᴇᴍ ʜᴇᴀʟᴛʜ 📊\n\n"
            "✨ <i>sɪᴍᴘʟᴇ. ꜰᴀsᴛ. sᴇᴄᴜʀᴇ.</i>\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [InlineKeyboardButton('🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ', callback_data='start', style="primary")],
            [InlineKeyboardButton('🛡️ ᴄʟᴏsᴇ ᴍᴇɴᴜ', callback_data='close', style="danger")]
        ]
        try:
            await query.message.edit_caption(caption=text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "about":
        try:
            await query.message.edit_caption(
                caption=ABOUT_TXT,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start', style="primary"),
                     InlineKeyboardButton('ᴄʟᴏꜱᴇ', callback_data='close', style="danger")]
                ])
            )
        except Exception:
            await query.message.edit_text(
                text=ABOUT_TXT,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start', style="primary"),
                     InlineKeyboardButton('ᴄʟᴏsᴇ', callback_data='close', style="danger")]
                ])
            )

    elif data == "start":
        # Premium Start Buttons
        buttons = [
            [InlineKeyboardButton("📢 NAME: JOIN OUR COMMUNITY", url="https://t.me/AniZoneFlix", style="primary")],
            [
                InlineKeyboardButton("⚙️ ˹ ᴀʙᴏᴜᴛ ˼", callback_data="about", style="primary"),
                InlineKeyboardButton("✨ ˹ ʜᴇʟᴘ ˼", callback_data="help", style="primary")
            ],
            [
                InlineKeyboardButton("💎 ˹ ᴘʀᴇᴍɪᴜᴍ ˼", callback_data="premium", style="success")
            ]
        ]
        try:
            await query.message.edit_caption(
                caption=START_MSG.format(mention=query.from_user.mention),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            await query.message.edit_text(
                text=START_MSG.format(mention=query.from_user.mention),
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(buttons)
            )


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


    elif data == "premium":
        await query.message.delete()
        caption = (
            "━━━━━━━━━━━━━━━━━━━\n"
            "💎 <b>ᴀɴɪᴢᴏɴᴇꜰʟɪx ᴘʀᴇᴍɪᴜᴍ ᴍᴇᴍʙᴇʀsʜɪᴘ</b> 💎\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Benefits:</b>\n"
            "• Direct File Access (No Shortener)\n"
            "• High-Speed Priority Delivery\n"
            "• Ad-Free Experience\n"
            "• Access to Exclusive Content\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🎖️ <b>Available Plans:</b>\n"
            f"⚡ 7 Dᴀʏs: <code>{PRICE1}</code>\n"
            f"⚡ 1 Mᴏɴᴛʜ: <code>{PRICE2}</code>\n"
            f"⚡ 3 Mᴏɴᴛʜs: <code>{PRICE3}</code>\n"
            f"⚡ 6 Mᴏɴᴛʜs: <code>{PRICE4}</code>\n"
            f"⚡ 1 Yᴇᴀʀ: <code>{PRICE5}</code>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "💳 <b>UPI ID:</b> <code>{UPI_ID}</code>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ <i>Must send screenshot after payment for instant activation.</i>"
        )
        banners = await get_banners(client)
        photo = random.choice(banners) if banners else None
        await send_media(
            client=client,
            chat_id=query.message.chat.id,
            photo=photo,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("💬 Cᴏɴᴛᴀᴄᴛ Aᴅᴍɪɴ", url=SCREENSHOT_URL, style="primary")],
                    [InlineKeyboardButton("🔒 Cʟᴏsᴇ", callback_data="close", style="danger")]
                ]
            )
        )



    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass

    elif data.startswith("rfs_ch_"):
        cid = int(data.split("_")[2])
        try:
            chat = await client.get_chat(cid)
            mode = await db.get_channel_mode(cid)
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏғғ"
            new_mode = "ᴏғғ" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}", style="primary")],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back", style="primary")]
            ]
            await query.message.edit_text(
                f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            await query.answer("Failed to fetch channel info", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        cid, action = data.split("_")[2:]
        cid = int(cid)
        mode = "on" if action == "on" else "off"

        await db.set_channel_mode(cid, mode)
        await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")

        # Refresh the same channel's mode view
        chat = await client.get_chat(cid)
        status = "🟢 ON" if mode == "on" else "🔴 OFF"
        new_mode = "off" if mode == "on" else "on"
        buttons = [
            [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}", style="primary")],
            [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back", style="primary")]
        ]
        await query.message.edit_text(
            f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "fsub_back":
        channels = await db.show_channels()
        buttons = []
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                mode = await db.get_channel_mode(cid)
                status = "🟢" if mode == "on" else "🔴"
                buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}", style="primary")])
            except:
                continue

        await query.message.edit_text(
            "sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("ck"):
        user_id = query.from_user.id

        access_status = await check_user_access(client, user_id)

        if access_status == "granted":
            await query.answer("ᴀᴄᴄᴇss ɢʀᴀɴᴛᴇᴅ! Processing...", show_alert=False)
            await query.message.delete()

            parts = data.split("_", 1)
            # Ensure the message's from_user is the person who clicked the button
            query.message.from_user = query.from_user

            if len(parts) > 1:
                payload = parts[1]
                from plugins.start import handle_payload
                await handle_payload(client, query.message, payload)
            else:
                from plugins.start import start_command
                query.message.text = "/start"
                await start_command(client, query.message)
        else:
            await query.answer("ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘᴇɴᴅɪɴɢ! Please join all resources.", show_alert=True)

            payload = None
            parts = data.split("_", 1)
            if len(parts) > 1: payload = parts[1]

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
                warning_msg = "⚠️ Please join our channels/groups and start the required bots before accessing content."
            elif missing_fsub:
                warning_msg = "⚠️ You must join all required channels/groups before accessing content."
            elif missing_bots:
                warning_msg = "⚠️ Please start the required bot first."
            else:
                warning_msg = "⚠️ Access Denied. Please complete verification."

            reply_markup = await get_fsub_buttons(client, user_id, payload)

            caption = (
                "━━━━━━━━━━━━━━━━━━━\n"
                "✨ ˹ ʜᴇʏ sᴀᴍᴀ × ᴀɴɪᴢᴏɴᴇꜰʟɪx ˼ ✨\n\n"
                "🎉 <b>˹ ᴀɴɪᴍᴇ ꜰɪʟᴇs ᴀʀᴇ ʀᴇᴀᴅʏ ˼ !!</b>\n\n"
                f"{warning_msg}\n\n"
                "━━━━━━━━━━━━━━━━━━━"
            )

            # Edit the message to show updated status
            try:
                await query.message.edit_caption(
                    caption=caption,
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"Error editing fsub message: {e}")

    elif data.startswith("car_idx:"):
        parts = data.split(":")
        session_id = parts[1]
        page_idx = int(parts[2])

        from utils.carousel import render_carousel_page
        from utils.formatter import check_client_compatibility

        input_media, markup = await render_carousel_page(client, session_id, page_idx)
        if input_media and markup:
            buttons = list(markup.inline_keyboard)
            buttons.append([InlineKeyboardButton("📥 Download All", callback_data=f"car_dl_all:{session_id}")])
            markup = InlineKeyboardMarkup(buttons)

            is_legacy = not await check_client_compatibility(query)
            caption = RichText.clean_unsupported(input_media.caption, is_legacy=is_legacy)
            input_media.caption = caption

            try:
                await query.message.edit_media(media=input_media, reply_markup=markup)
            except Exception as e:
                # If editing media type fails (e.g. Photo to Video), delete old and send new message
                try:
                    await query.message.delete()
                except:
                    pass

                from plugins.start import get_protect_content_for_user
                protect_val = await get_protect_content_for_user(user_id, client.username)
                session = await db.database['carousels'].find_one({"_id": session_id})
                if session:
                    ids = session["ids"]
                    cid = session["cid"]
                    msg_id = ids[page_idx]
                    msgs = await get_messages(client, [msg_id], chat_id=cid)
                    if msgs and msgs[0]:
                        msg = msgs[0]
                        if msg.photo:
                            await client.send_photo(chat_id=user_id, photo=msg.photo.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                        elif msg.video:
                            await client.send_video(chat_id=user_id, video=msg.video.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                        elif msg.document:
                            await client.send_document(chat_id=user_id, document=msg.document.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                        elif msg.audio:
                            await client.send_audio(chat_id=user_id, audio=msg.audio.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                        elif msg.animation:
                            await client.send_animation(chat_id=user_id, animation=msg.animation.file_id, caption=caption, reply_markup=markup, protect_content=protect_val)
                else:
                    await query.answer("Could not load page. Try again.", show_alert=True)
        else:
            await query.answer("Carousel session expired or messages unavailable.", show_alert=True)

    elif data.startswith("car_dl_all:"):
        session_id = data.split(":")[1]
        session = await db.database['carousels'].find_one({"_id": session_id})
        if session:
            await query.answer("Downloading all files sequentially...", show_alert=False)
            try:
                await query.message.delete()
            except: pass

            from plugins.start import send_files
            base_str = session.get("base_string") or session.get("base64_string") or ""

            if base_str:
                try:
                    await send_files(client, user_id, base_str, force_sequential=True)
                except Exception as e:
                    print(f"Error in send_files: {e}")
                    base_str = "" # trigger fallback

            if not base_str:
                # Fallback: Send files sequentially using direct copy from session ids list
                ids = session.get("ids", [])
                cid = session.get("cid")
                if ids and cid:
                    settings = await db.get_settings(bot_username=client.username)
                    session_str = settings.get('session_string')
                    session_client = None
                    if session_str:
                        try:
                            from plugins.start import get_session_client
                            session_client = await get_session_client(session_str)
                        except Exception:
                            pass

                    current_client = session_client or client
                    for msg_id in ids:
                        try:
                            await current_client.copy_message(
                                chat_id=user_id,
                                from_chat_id=cid,
                                message_id=msg_id
                            )
                        except Exception as e:
                            print(f"Error copying carousel file: {e}")
        else:
            await query.answer("Carousel session expired or invalid.", show_alert=True)


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
