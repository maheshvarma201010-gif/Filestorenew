import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import USER_REPLY_TEXT
from helper_func import check_admin, BotAdminTaskContext, get_messages
from core.range_parser import parse_mixed_inputs
from core.db_resolver import resolve_db_source
from core.message_metadata import get_message_metadata
from core.batch_generator import generate_final_link
from core.formatting import format_single_link_ui, split_blocks_into_parts, label_parts, format_bulk_summary_ui
from core.errors import format_error_message, BatchBotError, InvalidLinkError, MessageInaccessibleError

@Client.on_message(filters.private & filters.command(['genlink', 'gen_link']))
async def genlink(client: Client, message: Message):
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
            input_text = f"/genlink\n{reply_text}"
        elif not has_arg:
            # Prompt Mode
            try:
                ask = await client.ask(
                    message.chat.id,
                    "<b>🔗 Send the message link or ID.</b>\n\n<i>Type /cancel to cancel.</i>",
                    filters=filters.text,
                    timeout=60
                )
                if ask.text.lower() == "/cancel":
                    await ask.reply("❌ <b>Cancelled.</b>")
                    return
                input_text = f"/genlink\n{ask.text}"
            except asyncio.TimeoutError:
                await message.reply("⏰ <b>Timeout! Process Cancelled.</b>")
                return

        # Parse inputs
        parsed_items = parse_mixed_inputs(input_text.replace("/genlink", "").replace("/gen_link", ""))
        if not parsed_items:
            await message.reply_text("❌ <b>Invalid input! Please provide a valid message link or ID.</b>")
            return

        progress_msg = await message.reply_text("<b>⏳ Generating link(s)...</b>")

        output_blocks = []
        success_count = 0
        failed_count = 0
        failed_details = []

        for idx, item in enumerate(parsed_items, 1):
            original_url = item.get('original')
            try:
                chan_ref = item.get('channel')
                start_id = item.get('start_id')

                # Resolve DB bot and target channel ID
                cid, bot_username, running_client = await resolve_db_source(client, chan_ref)
                if not cid or not running_client:
                    raise InvalidLinkError("Channel could not be resolved or is unregistered.")

                # Fetch Telegram message using resolved client
                msgs = await get_messages(running_client, [start_id], chat_id=cid)
                if not msgs or not msgs[0]:
                    raise MessageInaccessibleError("Message is deleted, restricted, or inaccessible.")

                msg = msgs[0]

                # Extract priority metadata
                meta = get_message_metadata(msg)

                # Generate link
                gen_url = await generate_final_link(running_client, cid, start_id)

                # Format UI
                block = format_single_link_ui(original_url, meta['filename'], meta['caption'], gen_url)
                output_blocks.append(block)
                success_count += 1

            except Exception as e:
                failed_count += 1
                err_text = format_error_message(e)
                failed_details.append(f"{original_url} — {err_text}")
                # We do not stop the entire bulk operation because one item fails

        try:
            await progress_msg.delete()
        except:
            pass

        # Reply with generated links
        if output_blocks:
            parts = split_blocks_into_parts(output_blocks)
            labeled = label_parts(parts)
            for part in labeled:
                await message.reply_text(part)

        # Show bulk summary if there were any failures, or if multiple items were processed
        if failed_count > 0 or (success_count + failed_count) > 1:
            summary = format_bulk_summary_ui(success_count, failed_count, failed_details)
            await message.reply_text(summary)
