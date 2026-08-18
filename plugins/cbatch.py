import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from config import USER_REPLY_TEXT
from helper_func import check_admin, BotAdminTaskContext, get_messages, get_filename
from core.range_parser import parse_mixed_inputs
from core.db_resolver import resolve_db_source, resolve_channel_id
from core.message_metadata import get_message_metadata
from core.batch_generator import generate_final_link
from core.formatting import format_batch_link_ui, split_blocks_into_parts, label_parts, format_bulk_summary_ui
from core.errors import format_error_message, BatchBotError, InvalidLinkError, MessageInaccessibleError

@Client.on_message(filters.private & filters.command('cbatch'))
async def cbatch(client: Client, message: Message):
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
            input_text = f"/cbatch\n{reply_text}"
        elif not has_arg:
            try:
                ask = await client.ask(
                    message.chat.id,
                    "<b>📦 Send the message range to cbatch.</b>\n\n<i>Type /cancel to cancel.</i>",
                    filters=filters.text,
                    timeout=60
                )
                if ask.text.lower() == "/cancel":
                    await ask.reply("❌ <b>cbatch Cancelled.</b>")
                    return
                input_text = f"/cbatch\n{ask.text}"
            except asyncio.TimeoutError:
                await message.reply("⏰ <b>Timeout! Process Cancelled.</b>")
                return

        parsed_items = parse_mixed_inputs(input_text.replace("/cbatch", ""))
        if not parsed_items:
            await message.reply_text("❌ <b>No valid message range found.</b>")
            return

        # Prompt for custom ranges for EACH range
        collected_tasks = []
        try:
            for idx, item in enumerate(parsed_items, 1):
                original = item.get('original')

                # Check for channel mismatches on parsed ranges
                item_type = item.get('type')
                chan_ref = item.get('channel')

                cid, bot_username, running_client = await resolve_db_source(client, chan_ref)
                if not cid or not running_client:
                    await message.reply_text(f"❌ <b>No configured DB bot/channel was found for range:</b> <code>{original}</code>")
                    return

                # Prompt for custom ranges
                prompt_text = (
                    f"📦 <b>[Range {idx}/{len(parsed_items)}]</b>\n"
                    f"Range: <code>{original}</code>\n\n"
                    f"<b>Send custom ranges in this format:</b>\n"
                    f"<code>1-12,13-79</code>\n\n"
                    f"<i>Type /cancel to cancel.</i>"
                )
                prompt_msg = await message.reply_text(prompt_text)
                last_msg_id = prompt_msg.id

                custom_ranges = []
                while True:
                    resp = await client.listen(chat_id=message.chat.id, filters=filters.text, timeout=120)
                    if resp.id <= last_msg_id:
                        continue

                    resp_text = resp.text.strip()
                    if resp_text.lower() == "/cancel":
                        await message.reply_text("❌ <b>cbatch Cancelled.</b>")
                        return

                    # Parse custom ranges like 1-12,13-79
                    parts = [x.strip() for x in resp_text.split(",") if x.strip()]
                    is_valid = True
                    temp_ranges = []
                    for p in parts:
                        if "-" in p:
                            r_parts = [r.strip() for r in p.split("-")]
                            if len(r_parts) == 2 and r_parts[0].isdigit() and r_parts[1].isdigit():
                                r_start = int(r_parts[0])
                                r_end = int(r_parts[1])
                                if r_start > 0 and r_end > 0:
                                    temp_ranges.append((r_start, r_end))
                                    continue
                        is_valid = False
                        break

                    if is_valid and temp_ranges:
                        custom_ranges = temp_ranges
                        break
                    else:
                        err_msg = await message.reply_text("❌ <b>Invalid format! Use START-END separated by commas (e.g. 1-12,13-79). Try again:</b>")
                        last_msg_id = err_msg.id

                collected_tasks.append({
                    'original': original,
                    'cid': cid,
                    'running_client': running_client,
                    'custom_ranges': custom_ranges
                })

        except asyncio.TimeoutError:
            await message.reply_text("⏰ <b>Timeout waiting for response. Aborted.</b>")
            return

        progress_msg = await message.reply_text("<b>⏳ Generating custom batches...</b>")

        output_blocks = []
        success_count = 0
        failed_count = 0
        failed_details = []

        # Process each collected range
        for idx, task in enumerate(collected_tasks, 1):
            original = task['original']
            cid = task['cid']
            running_client = task['running_client']
            custom_ranges = task['custom_ranges']

            for c_idx, (r_start, r_end) in enumerate(custom_ranges, 1):
                try:
                    # Retrieve first and last available messages in the custom range
                    first_msg = None
                    last_msg = None

                    # Find first available message starting from r_start
                    first_chk_ids = list(range(r_start, min(r_end + 1, r_start + 100)))
                    f_msgs = await get_messages(running_client, first_chk_ids, chat_id=cid)
                    if f_msgs:
                        f_msgs.sort(key=lambda m: m.id)
                        first_msg = f_msgs[0]

                    # Find last available message ending at r_end
                    last_chk_ids = list(range(max(r_start, r_end - 100), r_end + 1))
                    l_msgs = await get_messages(running_client, last_chk_ids, chat_id=cid)
                    if l_msgs:
                        l_msgs.sort(key=lambda m: m.id)
                        last_msg = l_msgs[-1]

                    if not first_msg:
                        # Fallback
                        batch_msgs = await get_messages(running_client, [r_start, r_end], chat_id=cid)
                        if len(batch_msgs) > 0 and batch_msgs[0]:
                            first_msg = batch_msgs[0]
                        if len(batch_msgs) > 1 and batch_msgs[1]:
                            last_msg = batch_msgs[1]
                        elif len(batch_msgs) > 0 and batch_msgs[0]:
                            last_msg = batch_msgs[0]

                    if not first_msg:
                        raise EmptyRangeError("No valid accessible messages found in this custom range.")

                    meta_first = get_message_metadata(first_msg)
                    meta_last = get_message_metadata(last_msg or first_msg)

                    # Generate batch link
                    link = await generate_final_link(running_client, cid, r_start, r_end)

                    # Output block
                    block = format_batch_link_ui(f"{original} ({r_start}-{r_end})", meta_first['filename'], meta_first['caption'], meta_last['filename'], meta_last['caption'], link)
                    output_blocks.append(block)
                    success_count += 1

                except Exception as e:
                    failed_count += 1
                    err_text = format_error_message(e)
                    failed_details.append(f"{original} [{r_start}-{r_end}] — {err_text}")

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

        # Show summary if failures or multiple items exist
        if failed_count > 0 or (success_count + failed_count) > 1:
            summary = format_bulk_summary_ui(success_count, failed_count, failed_details)
            await message.reply_text(summary)
