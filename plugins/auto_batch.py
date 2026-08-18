import asyncio
import time
import uuid
import re
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified, FloodWait
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import USER_REPLY_TEXT
import config
from helper_func import check_admin, BotAdminTaskContext, get_messages, get_filename
from database.database import db

from core.range_parser import parse_mixed_inputs
from core.db_resolver import resolve_db_source, resolve_channel_id
from core.message_metadata import get_message_metadata, clean_emojis_and_html
from core.episode_detector import detect_episode, parse_season_episode_advanced
from core.batch_generator import generate_final_link, generate_list_link, get_start_link
from core.state_manager import state_manager
from core.formatting import split_blocks_into_parts, label_parts
from core.errors import format_error_message

# Quality priority for sorting
QUALITY_PRIORITY = {
    "4K": 1,
    "2160P": 2,
    "1440P": 3,
    "1080P": 4,
    "900P": 5,
    "720P": 6,
    "540P": 7,
    "480P": 8,
    "360P": 9,
    "UNKNOWN": 10
}

# In-memory FIFO tasks queues
AUTO_BATCH_QUEUES = defaultdict(list)          # bot_username -> list of task dicts (queued)
AUTO_BATCH_ACTIVE_TASKS = {}                    # bot_username -> active task dict or None
AUTO_BATCH_PUBLISH_LOCKS = defaultdict(asyncio.Lock) # bot_username -> Lock for serializing publishing

# Helper to edit messages safely without throwing MessageNotModified
async def edit_msg_safe(client, chat_id, message_id, text, reply_markup=None):
    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    except MessageNotModified:
        pass
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e):
            pass
        else:
            print(f"[EDIT ERROR] {e}")

# Helper to format progress bar
def make_progressbar(percent, length=10):
    filled = int(percent / (100 / length))
    return "█" * filled + "░" * (length - filled)

def episode_sort_key(ep):
    if isinstance(ep, (int, float)):
        return (0, ep, "")
    elif isinstance(ep, str):
        try:
            val = float(ep)
            return (0, val, "")
        except ValueError:
            return (1, 0, ep)
    return (2, 0, str(ep))

def detect_quality(text):
    text_upper = text.upper()
    for q in ["2160P", "1440P", "1080P", "900P", "720P", "540P", "480P", "360P"]:
        if q in text_upper:
            return q
    if "4K" in text_upper:
        return "4K"
    # Matches patterns like 480p, 480px264, etc. where there is no word boundary after p because of alphanumeric characters (e.g. x264)
    m_q = re.search(r'\b(\d{3,4})[pP](?:\D|$)', text)
    if m_q:
        q_val = f"{m_q.group(1)}P"
        if q_val in QUALITY_PRIORITY:
            return q_val
    return "UNKNOWN"

@Client.on_message(filters.private & filters.command(['auto_batch', 'advance_batch', 'advbatch']))
async def autobatch_and_advbatch(client: Client, message: Message):
    # Enforce Admin-only check
    if not await check_admin(None, client, message):
        await message.reply_text(USER_REPLY_TEXT)
        return

    cmd = message.command[0].lower()
    is_adv = cmd in ['advance_batch', 'advbatch']

    input_text = message.text
    has_arg = len(message.command) > 1 if message.text else False

    # Support Reply mode
    if message.reply_to_message:
        reply_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        input_text = f"/{cmd}\n{reply_text}"
    elif not has_arg:
        # Prompt mode
        try:
            ask = await client.ask(
                message.chat.id,
                f"<b>🎬 Send the range link or range token for /{cmd}.</b>\n\n<i>Type /cancel to cancel.</i>",
                filters=filters.text,
                timeout=60
            )
            if ask.text.lower() == "/cancel":
                await ask.reply("❌ <b>Process Cancelled.</b>")
                return
            input_text = f"/{cmd}\n{ask.text}"
        except asyncio.TimeoutError:
            await message.reply("⏰ <b>Timeout! Process Cancelled.</b>")
            return

    parsed_items = parse_mixed_inputs(input_text.replace(f"/{cmd}", ""))
    if not parsed_items:
        await message.reply_text("❌ <b>No valid ranges found in the input.</b>")
        return

    # Verify each range and resolve source
    validated_ranges = []
    for item in parsed_items:
        chan_ref = item.get('channel')
        start = item.get('start_id')
        end = item.get('end_id')

        cid, bot_username, running_client = await resolve_db_source(client, chan_ref)
        if not cid or not running_client:
            await message.reply_text(f"❌ <b>No configured DB bot/channel was found for:</b> <code>{item.get('original')}</code>")
            return

        validated_ranges.append({
            'cid': cid,
            'start_id': start,
            'end_id': end,
            'bot_username': bot_username,
            'original_token': item.get('original')
        })

    # Sequential Wizard Flow for each validated range
    configured_results = []
    bot_user = client.username.lower()
    admin_id = message.from_user.id

    state = state_manager.set_state(bot_user, admin_id, cmd, validated_ranges)

    try:
        for idx, item in enumerate(validated_ranges, 1):
            range_disp = f"{item['start_id']}-{item['end_id']}"

            # Step 1: Episode count (sent as new message)
            step1_text = (
                f"📦 <b>[Range {idx}/{len(validated_ranges)}] - Step 1/2</b>\n"
                f"Range: <code>{range_disp}</code>\n\n"
                f"<b>How many episodes/files should be included in total?</b>\n"
                f"Example:\n<code>12</code>\n\n"
                f"<i>Type /cancel_batch to cancel.</i>"
            )
            step1_msg = await message.reply_text(step1_text)
            last_msg_id = step1_msg.id

            episode_count = None
            while True:
                resp = await client.listen(chat_id=message.chat.id, filters=filters.text, timeout=300)
                if resp.id <= last_msg_id:
                    continue
                resp_text = resp.text.strip()
                if resp_text.lower() == "/cancel_batch":
                    state_manager.clear_state(bot_user, admin_id)
                    await message.reply_text("❌ <b>Auto Batch wizard cancelled.</b>")
                    return
                if resp_text.isdigit() and int(resp_text) > 0:
                    episode_count = int(resp_text)
                    break
                else:
                    err_msg = await message.reply_text("⚠️ <b>Invalid size! Please send a valid positive integer.</b>")
                    last_msg_id = err_msg.id

            # Step 2: Anime name (sent as new message)
            step2_text = (
                f"🎬 <b>[Range {idx}/{len(validated_ranges)}] - Step 2/2</b>\n"
                f"Range: <code>{range_disp}</code>\n"
                f"Total Episodes Requested: <code>{episode_count}</code>\n\n"
                f"<b>Send Anime Name.</b>\n\n"
                f"Examples:\n"
                f"<code>Naruto</code>\nor\n<code>Naruto, Naruto Shippuden</code>\n\n"
                f"<i>Type <code>.</code> to disable anime filtering.</i>\n\n"
                f"<i>Type /cancel_batch to cancel.</i>"
            )
            step2_msg = await message.reply_text(step2_text)
            last_msg_id = step2_msg.id

            anime_names = None
            while True:
                resp_anime = await client.listen(chat_id=message.chat.id, filters=filters.text, timeout=300)
                if resp_anime.id <= last_msg_id:
                    continue
                anime_text = resp_anime.text.strip()
                if anime_text.lower() == "/cancel_batch":
                    state_manager.clear_state(bot_user, admin_id)
                    await message.reply_text("❌ <b>Auto Batch wizard cancelled.</b>")
                    return
                if anime_text in [".", "..", "...", "-", "_", "*"]:
                    anime_names = None
                else:
                    anime_names = [n.strip() for n in anime_text.split(",") if n.strip()]
                break

            configured_results.append({
                'cid': item['cid'],
                'start_id': item['start_id'],
                'end_id': item['end_id'],
                'bot_username': item['bot_username'],
                'episode_count': episode_count,
                'anime_names': anime_names,
                'original_token': item['original_token']
            })

    except asyncio.TimeoutError:
        state_manager.clear_state(bot_user, admin_id)
        await message.reply_text("⏰ <b>Wizard timed out (5 minutes). Aborted.</b>")
        return

    # Clear temporary state
    state_manager.clear_state(bot_user, admin_id)

    # Combined Confirmation Summary
    confirm_text = f"📋 <b>Configure {'Advanced' if is_adv else 'Regular'} Auto Batch Tasks Summary:</b>\n\n"
    for idx, conf in enumerate(configured_results, 1):
        anime_disp = ", ".join(conf['anime_names']) if conf['anime_names'] else "No Anime Filter"
        confirm_text += (
            f"<b>{idx}. Range:</b> <code>{conf['original_token']}</code>\n"
            f"   <b>Target Bot:</b> @{conf['bot_username']}\n"
            f"   <b>Episodes Limit:</b> <code>{conf['episode_count']}</code>\n"
            f"   <b>Anime Filter:</b> <code>{anime_disp}</code>\n\n"
        )

    # Cache confirmation session in memory
    wizard_confirm_id = f"conf_{admin_id}_{int(time.time() * 1000)}"
    # Enforce standard session naming for callbacks
    state_manager.set_state(bot_user, wizard_confirm_id, cmd, configured_results)

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Start All", callback_data=f"ab_start_{wizard_confirm_id}_{'adv' if is_adv else 'reg'}"),
            InlineKeyboardButton("❌ Cancel", callback_data="ab_cancel_wizard")
        ]
    ])
    await message.reply_text(confirm_text, reply_markup=markup)

async def process_queue_worker(client, bot_username):
    while AUTO_BATCH_QUEUES[bot_username]:
        task = AUTO_BATCH_QUEUES[bot_username][0] # peek
        AUTO_BATCH_ACTIVE_TASKS[bot_username] = task
        task['status'] = 'running'

        loop = asyncio.get_running_loop()
        asyncio_task = loop.create_task(run_auto_batch_scan(client, task))
        task['asyncio_task'] = asyncio_task

        try:
            await asyncio_task
        except asyncio.CancelledError:
            task['status'] = 'cancelled'
            await edit_msg_safe(client, task['chat_id'], task['prompt_msg_id'], f"❌ <b>Task was cancelled.</b>")
        except Exception as e:
            task['status'] = 'failed'
            await edit_msg_safe(client, task['chat_id'], task['prompt_msg_id'], f"❌ <b>Task failed with error:</b> {e}")
        finally:
            if AUTO_BATCH_QUEUES[bot_username] and AUTO_BATCH_QUEUES[bot_username][0]['task_id'] == task['task_id']:
                AUTO_BATCH_QUEUES[bot_username].pop(0)
            AUTO_BATCH_ACTIVE_TASKS[bot_username] = None

async def run_auto_batch_scan(client, task):
    bot_username = client.username.lower()
    chat_id = task['chat_id']
    msg_id = task['prompt_msg_id']
    start_id = task['start_id']
    end_id = task['end_id']
    cid = task['cid']
    episode_limit = task['episode_count']
    anime_names = task['anime_names']
    target_bot_username = task['bot_username']
    is_adv = task.get('is_adv', False)

    anime_disp = ", ".join(anime_names) if anime_names else "No Anime Filter"

    start_time = time.time()
    scanned_count = 0
    matched_count = 0
    skipped_count = 0
    duplicate_count = 0
    error_count = 0

    # Retrieve Client of target bot (could be clone bot client)
    from bot import Bot
    target_client = Bot.instances.get(target_bot_username)
    if not target_client:
        task['status'] = 'failed'
        await edit_msg_safe(client, chat_id, msg_id, f"❌ <b>Error: Target client @{target_bot_username} is not running.</b>")
        return

    # Check for session string client (user session)
    settings = await db.get_settings(bot_username=target_bot_username)
    session_str = settings.get('session_string')
    session_client = None
    if session_str:
        try:
            from plugins.start import get_session_client
            session_client = await get_session_client(session_str)
        except Exception as e:
            print(f"[AUTO BATCH] Error fetching session client: {e}")

    total_range = list(range(start_id, end_id + 1))
    total_count = len(total_range)

    # Sort groups: season -> quality -> list of (episode, message_id, caption_or_filename)
    groups = defaultdict(lambda: defaultdict(list))
    processed_episodes = set()

    # Stage 1: Ordered, smooth chunk scanning (50 per chunk)
    chunk_size = 50
    last_update_time = 0

    for idx in range(0, len(total_range), chunk_size):
        batch_ids = total_range[idx:idx+chunk_size]
        try:
            msgs = await get_messages(session_client or target_client, batch_ids, chat_id=cid)
            msgs = [m for m in msgs if m]
            msgs.sort(key=lambda m: m.id)

            for m in msgs:
                if not m or m.empty:
                    skipped_count += 1
                    continue

                media = m.document or m.video or m.audio or m.animation
                if not media:
                    skipped_count += 1
                    continue

                caption = m.caption.html if (m.caption and hasattr(m.caption, "html")) else (m.caption or "")
                filename = get_filename(m)

                # Clean captions and filenames of HTML/emojis for matching
                caption_cleaned = clean_emojis_and_html(caption)
                filename_cleaned = clean_emojis_and_html(filename)

                # Anime Matching & Filtering
                if anime_names:
                    # Match name against caption first, then filename
                    matched = False
                    for name in anime_names:
                        cleaned_name = name.lower()
                        if cleaned_name in caption_cleaned.lower() or cleaned_name in filename_cleaned.lower():
                            matched = True
                            break
                    if not matched:
                        skipped_count += 1
                        continue

                # Episode & Season detection
                season, ep_val = detect_episode(caption, filename)
                if ep_val is None:
                    skipped_count += 1
                    continue

                # Exclude duplicate episodes/parts in the same quality
                quality = detect_quality(caption_cleaned)
                if quality == "UNKNOWN":
                    quality = detect_quality(filename_cleaned)

                ep_key = (season, ep_val, quality)
                if ep_key in processed_episodes:
                    duplicate_count += 1
                    continue

                # Auto Batch Episode limit check: If count is 12, only generate episodes <= 12
                # e.g., ep_val could be numeric
                if isinstance(ep_val, (int, float)):
                    if ep_val > episode_limit:
                        # Skip files above requested episode limit
                        continue

                processed_episodes.add(ep_key)

                # Direct assignment of first and last captions to avoid identical or duplicated caption mappings
                caption_or_filename = caption.strip() if caption and caption.strip() else filename
                groups[season][quality].append((ep_val, m.id, caption_or_filename))
                matched_count += 1

                # Small safety delay per message
                await asyncio.sleep(0.02)

            scanned_count += len(batch_ids)

            # Update progress UI rate-limited
            now = time.time()
            if now - last_update_time >= 3.5:
                last_update_time = now
                elapsed = now - start_time
                speed = round(scanned_count / elapsed, 1) if elapsed > 0 else 0
                eta_secs = int((total_count - scanned_count) / speed) if speed > 0 else 0
                eta_str = f"{eta_secs}s" if speed > 0 else "Calculating..."
                percent = int((scanned_count / total_count) * 100)
                pbar = make_progressbar(percent)

                progress_text = (
                    f"⏳ <b>Scanning Files...</b>\n"
                    f"{pbar} {percent}%\n\n"
                    f"• <b>Current Message:</b> <code>{batch_ids[-1]}</code>\n"
                    f"• <b>Anime Filter:</b> <code>{anime_disp}</code>\n"
                    f"• <b>Matched Files:</b> <code>{matched_count}</code>\n"
                    f"• <b>Skipped Files:</b> <code>{skipped_count}</code>\n"
                    f"• <b>Duplicates:</b> <code>{duplicate_count}</code>\n"
                    f"• <b>Speed:</b> <code>{speed} msgs/sec</code>\n"
                    f"• <b>ETA:</b> <code>{eta_str}</code>\n"
                    f"• <b>Elapsed Time:</b> <code>{round(elapsed, 1)}s</code>"
                )
                await edit_msg_safe(client, chat_id, msg_id, progress_text)

            # Throttling delay between chunks
            await asyncio.sleep(0.1)

        except FloodWait as e:
            await asyncio.sleep(e.value)
            error_count += len(batch_ids)
        except Exception as ex:
            print(f"[SCAN CHUNK ERROR] {ex}")
            error_count += len(batch_ids)

    # Check if any episodes detected
    if not groups:
        task['status'] = 'failed'
        await edit_msg_safe(client, chat_id, msg_id, "⚠️ <b>No valid episodes were detected in the selected range.</b>")
        return

    task['status'] = 'generating'
    await edit_msg_safe(
        client, chat_id, msg_id,
        f"🔗 <b>Batching matches and generating protected links...</b>\n\n"
        f"• <b>Total Matched:</b> {matched_count}\n"
        f"• <b>Queue Position:</b> Waiting for output serialization..."
    )

    # Sort and Generate Links per quality sequentially
    final_output_blocks = []
    total_generated_batches = 0

    # Ensure output ordering: season ascending, then quality
    for season in sorted(groups.keys()):
        qualities_dict = groups[season]

        # If it is advanced auto batch, we only generate distinct links for qualities ('480P', '720P', '1080P') sequentially
        if is_adv:
            target_qualities = ["480P", "720P", "1080P"]
        else:
            target_qualities = sorted(qualities_dict.keys(), key=lambda q: QUALITY_PRIORITY.get(q, 100))

        for q in target_qualities:
            files = qualities_dict.get(q, [])
            if files:
                files.sort(key=lambda x: episode_sort_key(x[0]))

                # Get the actual first and last detected episode numbers from matched metadata
                first_ep_detected = files[0][0]
                last_ep_detected = files[-1][0]

                # Slice mids
                mids = [f[1] for f in files]

                # Generate list-link or range link targeting clone/target client
                link = await generate_list_link(target_client, cid, mids)

                first_caption = files[0][2]
                last_caption = files[-1][2]

                block = (
                    f"🎬 <b>Quality: {q}</b>\n"
                    f"📦 <b>Range:</b> {first_ep_detected} → {last_ep_detected}\n"
                    f"<b>FIRST Caption:</b> {first_caption}\n"
                    f"<b>LAST Caption:</b> {last_caption}\n"
                    f"🔗 <b>Link:</b> <code>{link}</code>"
                )
                final_output_blocks.append(block)
                total_generated_batches += 1
            elif is_adv:
                # If target quality is not found in ADVBATCH scan, mark as 'NOT FOUND' explicitly
                final_output_blocks.append(f"<b>🎬 Quality: {q}</b>\n❌ <code>NOT FOUND</code>")

    # FIFO Output Serialization
    task['status'] = 'waiting_publish'
    async with AUTO_BATCH_PUBLISH_LOCKS[bot_username]:
        task['status'] = 'publishing'
        await edit_msg_safe(client, chat_id, msg_id, "🚀 <b>Publishing batch results to chat...</b>")

        if final_output_blocks:
            parts = split_blocks_into_parts(final_output_blocks)
            labeled = label_parts(parts)
            for part in labeled:
                await client.send_message(chat_id, part)

        # Final edit with complete stats
        total_time = round(time.time() - start_time, 1)
        completion_text = (
            f"✅ <b>Auto Batch Task Completed!</b>\n\n"
            f"• <b>Anime:</b> <code>{anime_disp}</code>\n"
            f"• <b>Matched Episodes:</b> <code>{matched_count}</code>\n"
            f"• <b>Generated Batches:</b> <code>{total_generated_batches}</code>\n"
            f"• <b>Execution Time:</b> <code>{total_time}s</code>"
        )
        await edit_msg_safe(client, chat_id, msg_id, completion_text)

    task['status'] = 'completed'


# Cancel active running auto_batch task
@Client.on_message(filters.private & filters.command(['cancel_batch', 'cancel_autobatch']))
async def cancel_batch_command(client: Client, message: Message):
    if not await check_admin(None, client, message):
        await message.reply_text(USER_REPLY_TEXT)
        return

    bot_username = client.username.lower()
    active_task = AUTO_BATCH_ACTIVE_TASKS.get(bot_username)
    if active_task:
        asyncio_task = active_task.get('asyncio_task')
        if asyncio_task:
            asyncio_task.cancel()
            active_task['status'] = 'cancelled'
            await message.reply_text("✅ <b>Running Auto Batch task successfully cancelled!</b>")
            return

    # If queued tasks exist, clear the queue
    if AUTO_BATCH_QUEUES[bot_username]:
        AUTO_BATCH_QUEUES[bot_username].clear()
        await message.reply_text("✅ <b>Cleared all queued Auto Batch tasks!</b>")
        return

    await message.reply_text("❌ <b>No running or queued Auto Batch task found to cancel.</b>")


@Client.on_callback_query(filters.regex(r"^(ab_start_|ab_cancel_wizard)"))
async def auto_batch_callbacks(client: Client, query: CallbackQuery):
    bot_username = client.username.lower()
    admin_id = query.from_user.id

    # Enforce admin privilege check
    if not await db.admin_exist(admin_id) and admin_id != config.OWNER_ID:
        await query.answer("❌ You are not authorized!", show_alert=True)
        return

    if query.data == "ab_cancel_wizard":
        await query.message.delete()
        await query.answer("Wizard cancelled.")
        return

    # Start all callback
    if query.data.startswith("ab_start_"):
        is_adv = query.data.endswith("_adv")
        # Isolate wizard_confirm_id cleanly
        wizard_confirm_id = query.data.replace("ab_start_", "")
        if is_adv:
            wizard_confirm_id = wizard_confirm_id[:-4]  # removes '_adv'
        else:
            wizard_confirm_id = wizard_confirm_id[:-4]  # removes '_reg'

        # Verify wizard session
        session_key = (bot_username, wizard_confirm_id)
        configured_results = state_manager.get_state(bot_username, wizard_confirm_id)
        if not configured_results:
            await query.answer("⚠️ Session expired! Please run the command again.", show_alert=True)
            await query.message.delete()
            return

        # configured_results.input_ranges contains the array
        results = configured_results.input_ranges
        state_manager.clear_state(bot_username, wizard_confirm_id)

        await query.message.delete()
        await query.answer("🚀 Queueing Auto Batch Tasks...")

        for idx, item in enumerate(results, 1):
            task_id = f"ab_{uuid.uuid4().hex[:8]}_{idx}"
            prompt_msg = await query.message.reply_text(f"⏳ <b>Queueing Task:</b> <code>{task_id}</code>...")

            task = {
                'task_id': task_id,
                'chat_id': query.message.chat.id,
                'admin_id': admin_id,
                'status': 'queued',
                'cid': item['cid'],
                'start_id': item['start_id'],
                'end_id': item['end_id'],
                'episode_count': item['episode_count'],
                'anime_names': item['anime_names'],
                'bot_username': item['bot_username'],
                'prompt_msg_id': prompt_msg.id,
                'is_adv': is_adv
            }

            AUTO_BATCH_QUEUES[bot_username].append(task)

        if not AUTO_BATCH_ACTIVE_TASKS.get(bot_username):
            asyncio.create_task(process_queue_worker(client, bot_username))
