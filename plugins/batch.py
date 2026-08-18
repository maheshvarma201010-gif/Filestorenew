import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import USER_REPLY_TEXT
from helper_func import check_admin, BotAdminTaskContext, get_messages, get_message_id
from core.range_parser import parse_mixed_inputs
from core.db_resolver import resolve_db_source, resolve_channel_id
from core.message_metadata import get_message_metadata
from core.batch_generator import generate_final_link
from core.formatting import format_batch_link_ui, split_blocks_into_parts, label_parts, format_bulk_summary_ui
from core.errors import format_error_message, BatchBotError, InvalidLinkError, MessageInaccessibleError

@Client.on_message(filters.private & filters.command('batch'))
async def batch(client: Client, message: Message):
    # Enforce Admin-only check
    if not await check_admin(None, client, message):
        await message.reply_text(USER_REPLY_TEXT)
        return

    async with BotAdminTaskContext(client, message.from_user.id, message):
        input_text = message.text
        has_arg = len(message.command) > 1 if message.text else False

        # Support Reply mode
        if message.reply_to_message:
            reply_text = message.reply_to_message.text or message.reply_to_message.caption or ""
            input_text = f"/batch\n{reply_text}"
        elif not has_arg:
            try:
                ask = await client.ask(
                    message.chat.id,
                    "<b>📦 Send the message link, ID, or a range to batch.</b>\n\n<i>Type /cancel to cancel.</i>",
                    filters=filters.text,
                    timeout=60
                )
                if ask.text.lower() == "/cancel":
                    await ask.reply("❌ <b>Batch Generation Cancelled.</b>")
                    return
                input_text = f"/batch\n{ask.text}"
            except asyncio.TimeoutError:
                await message.reply("⏰ <b>Timeout! Process Cancelled.</b>")
                return

        parsed_items = parse_mixed_inputs(input_text.replace("/batch", ""))
        if not parsed_items:
            await message.reply_text("❌ <b>No valid range or message ID found.</b>")
            return

        progress_msg = await message.reply_text("<b>⏳ Processing batch range(s)...</b>")

        output_blocks = []
        success_count = 0
        failed_count = 0
        failed_details = []

        for idx, item in enumerate(parsed_items, 1):
            original = item.get('original')
            try:
                chan_ref = item.get('channel')
                start = item.get('start_id')
                end = item.get('end_id')
                item_type = item.get('type')

                # Check for channel mismatches on parsed ranges
                if item_type == 'range' and 'channel_right' in item:
                    # Resolve both channels and ensure they are the same
                    cid_left = await resolve_channel_id(client, chan_ref)
                    cid_right = await resolve_channel_id(client, item['channel_right'])
                    if cid_left != cid_right:
                        raise InvalidLinkError("Range spans different channels. Both ends must be in the same channel.")

                # If only one link is provided, prompt for ending message
                if item_type == 'single' or start == end:
                    try:
                        ask_end = await client.ask(
                            message.chat.id,
                            f"🛡️ <b>Send the last message link/ID or total message count to batch (e.g. 13) for:</b>\n`{original}`\n\n<i>Type /cancel to cancel.</i>",
                            filters=filters.text,
                            timeout=60
                        )
                        if ask_end.text.lower() == "/cancel":
                            raise BatchBotError("Cancelled by user.")

                        clean_text = ask_end.text.strip()
                        # Resolve DB source of first link
                        cid, bot_username, running_client = await resolve_db_source(client, chan_ref)
                        if not cid or not running_client:
                            raise InvalidLinkError("Channel could not be resolved or is unregistered.")

                        if clean_text.isdigit():
                            val = int(clean_text)
                            if val >= start:
                                # It's an ending message ID
                                end = val
                            else:
                                # It's a count! Find exactly `val` available messages starting from `start`
                                available_ids = []
                                current_id = start
                                chunk_size = 100
                                scanned_limit = 5000
                                total_scanned = 0

                                while len(available_ids) < val and total_scanned < scanned_limit:
                                    ids_to_check = list(range(current_id, current_id + chunk_size))
                                    msgs = await get_messages(running_client, ids_to_check, chat_id=cid)
                                    msg_map = {m.id: m for m in msgs if m and not m.empty}

                                    for mid in ids_to_check:
                                        if mid in msg_map:
                                            available_ids.append(mid)
                                            if len(available_ids) == val:
                                                break

                                    current_id += chunk_size
                                    total_scanned += chunk_size

                                if available_ids:
                                    end = available_ids[-1]
                                else:
                                    end = start + val - 1
                        else:
                            # It's a link, parse it
                            end_id, end_cid = await get_message_id(running_client, ask_end)
                            if not end_id or cid != end_cid:
                                raise InvalidLinkError("Invalid last message link/ID or channel mismatch.")
                            end = end_id
                    except asyncio.TimeoutError:
                        raise BatchBotError("Timeout waiting for ending message.")

                # Ensure start <= end
                if start > end:
                    start, end = end, start

                # Resolve DB bot and target channel ID
                cid, bot_username, running_client = await resolve_db_source(client, chan_ref)
                if not cid or not running_client:
                    raise InvalidLinkError("Channel could not be resolved or is unregistered.")

                # Retrieve first and last available messages in the range
                first_msg = None
                last_msg = None

                # Find first available message starting from start ID
                first_chk_ids = list(range(start, min(end + 1, start + 100)))
                f_msgs = await get_messages(running_client, first_chk_ids, chat_id=cid)
                if f_msgs:
                    f_msgs.sort(key=lambda m: m.id)
                    first_msg = f_msgs[0]

                # Find last available message ending at end ID
                last_chk_ids = list(range(max(start, end - 100), end + 1))
                l_msgs = await get_messages(running_client, last_chk_ids, chat_id=cid)
                if l_msgs:
                    l_msgs.sort(key=lambda m: m.id)
                    last_msg = l_msgs[-1]

                if not first_msg or not last_msg:
                    # Fallback lookup
                    batch_msgs = await get_messages(running_client, [start, end], chat_id=cid)
                    if len(batch_msgs) > 0 and batch_msgs[0]:
                        first_msg = batch_msgs[0]
                    if len(batch_msgs) > 1 and batch_msgs[1]:
                        last_msg = batch_msgs[1]
                    elif len(batch_msgs) > 0 and batch_msgs[0]:
                        last_msg = batch_msgs[0]

                if not first_msg:
                    raise EmptyRangeError("No valid accessible messages found in this range.")

                # Metadata priority engine
                meta_first = get_message_metadata(first_msg)
                meta_last = get_message_metadata(last_msg or first_msg)

                # Generate final batch start link
                link = await generate_final_link(running_client, cid, start, end)

                # Format UI
                block = format_batch_link_ui(original, meta_first['filename'], meta_first['caption'], meta_last['filename'], meta_last['caption'], link)
                output_blocks.append(block)
                success_count += 1

            except Exception as e:
                failed_count += 1
                err_text = format_error_message(e)
                failed_details.append(f"{original} — {err_text}")

        try:
            await progress_msg.delete()
        except:
            pass

        # Send outputs
        if output_blocks:
            parts = split_blocks_into_parts(output_blocks)
            labeled = label_parts(parts)
            for part in labeled:
                await message.reply_text(part)

        # Show bulk summary if there were failures or multiple processed items
        if failed_count > 0 or (success_count + failed_count) > 1:
            summary = format_bulk_summary_ui(success_count, failed_count, failed_details)
            await message.reply_text(summary)
