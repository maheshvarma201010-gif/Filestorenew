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
from core.episode_detector import parse_metadata_universal, detect_episode, detect_quality
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

# Helper to edit messages safely without throwing MessageNotModified or crashing
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

@Client.on_message(filters.private & filters.command(['auto_batch', 'advance_batch', 'advbatch']))
async def autobatch_and_advbatch(client: Client, message: Message):
    # Enforce Admin-only check
    if not await check_admin(None, client, message):
        await message.reply_text(USER_REPLY_TEXT)
        return

    cmd = message.command[0].lower()
    is_adv = cmd in ['advance_batch', 'advbatch']

    input_text = message.text or ""
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
                f"<b>🎬 Send range link(s) or token(s) for /{cmd}.</b>\n\n<i>Supports single or multiple ranges in multi-line text. Type /cancel to cancel.</i>",
                filters=filters.text,
                timeout=120
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
        await message.reply_text("❌ <b>No valid ranges found in the input. Please check link format.</b>")
        return

    # Verify each range and resolve source safely
    validated_ranges = []
    for item in parsed_items:
        chan_ref = item.get('channel')
        start = item.get('start_id')
        end = item.get('end_id')

        try:
            cid, bot_username, running_client = await resolve_db_source(client, chan_ref)
            if not cid or not running_client:
                await message.reply_text(f"⚠️ <b>Warning: No configured DB bot/channel was found for:</b> <code>{item.get('original')}</code>")
                continue

            validated_ranges.append({
                'cid': cid,
                'start_id': start,
                'end_id': end,
                'bot_username': bot_username,
                'original_token': item.get('original')
            })
        except Exception as ex:
            print(f"[RANGE RESOLVE ERROR] {ex}")
            await message.reply_text(f"⚠️ <b>Error resolving range:</b> <code>{item.get('original')}</code>")

    if not validated_ranges:
        await message.reply_text("❌ <b>No accessible ranges could be resolved. Please verify database channel permissions.</b>")
        return

    # Sequential Wizard Flow for each validated range
    configured_results = []
    bot_user = client.username.lower()
    admin_id = message.from_user.id

    state = state_manager.set_state(bot_user, admin_id, cmd, validated_ranges)

    try:
        for idx, item in enumerate(validated_ranges, 1):
            range_disp = f"{item['start_id']}-{item['end_id']}"

            # Step 1: Format & Count
            step1_text = (
                f"📦 <b>[Range {idx}/{len(validated_ranges)}] - Step 1/2</b>\n"
                f"Range: <code>{range_disp}</code>\n\n"
                f"<b>What should be used for generating the batch — episode numbers, message range, or another supported format?</b>\n\n"
                f"<i>Send total episode/file count (e.g. <code>13</code> or <code>25</code>).</i>\n\n"
                f"<i>Type /cancel_batch to cancel.</i>"
            )
            step1_msg = await message.reply_text(step1_text)
            last_msg_id = step1_msg.id

            episode_count = 9999
            while True:
                resp = await client.listen(chat_id=message.chat.id, filters=filters.text, timeout=300)
                if resp.id <= last_msg_id:
                    continue
                resp_text = resp.text.strip()
                if resp_text.lower() == "/cancel_batch":
                    state_manager.clear_state(bot_user, admin_id)
                    await message.reply_text("❌ <b>Auto Batch wizard cancelled.</b>")
                    return

                # Check for digit or format string
                digits = re.findall(r'\d+', resp_text)
                if digits:
                    episode_count = int(digits[0])
                    break
                elif resp_text.lower() in ["all", "auto", "message", "episode", "part", "range"]:
                    episode_count = 9999
                    break
                else:
                    err_msg = await message.reply_text("⚠️ <b>Invalid input! Please send a number (e.g. 13) or 'all'.</b>")
                    last_msg_id = err_msg.id

            # Step 2: Anime Name
            step2_text = (
                f"🎬 <b>[Range {idx}/{len(validated_ranges)}] - Step 2/2</b>\n"
                f"Range: <code>{range_disp}</code>\n"
                f"Requested Count: <code>{episode_count if episode_count < 9999 else 'All Available'}</code>\n\n"
                f"<b>Send the Anime Name to search across filename and file caption.</b>\n\n"
                f"Examples:\n"
                f"<code>Naruto</code>\nor\n<code>Naruto, Naruto Shippuden</code>\n\n"
                f"<i>Type <code>.</code> to search all files without anime name filter.</i>\n\n"
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
        await message.reply_text("⏰ <b>Wizard timed out. Operation aborted. You can run /{cmd} again anytime.</b>")
        return
    except Exception as ex:
        print(f"[WIZARD ERROR] {ex}")
        state_manager.clear_state(bot_user, admin_id)
        await message.reply_text(f"⚠️ <b>Wizard encountered an error:</b> `{ex}`")
        return

    # Clear temporary state
    state_manager.clear_state(bot_user, admin_id)

    # Combined Confirmation Summary
    confirm_text = f"📋 <b>Configure {'Advanced' if is_adv else 'Regular'} Auto Batch Tasks Summary:</b>\n\n"
    for idx, conf in enumerate(configured_results, 1):
        anime_disp = ", ".join(conf['anime_names']) if conf['anime_names'] else "No Anime Filter"
        count_disp = conf['episode_count'] if conf['episode_count'] < 9999 else 'All Available'
        confirm_text += (
            f"<b>{idx}. Range:</b> <code>{conf['original_token']}</code>\n"
            f"   <b>Target Bot:</b> @{conf['bot_username']}\n"
            f"   <b>Requested Count:</b> <code>{count_disp}</code>\n"
            f"   <b>Anime Filter:</b> <code>{anime_disp}</code>\n\n"
        )

    # Cache confirmation session in memory
    wizard_confirm_id = f"conf_{admin_id}_{int(time.time() * 1000)}"
    state_manager.set_state(bot_user, wizard_confirm_id, cmd, configured_results)

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Start All", callback_data=f"ab_start_{wizard_confirm_id}_{'adv' if is_adv else 'reg'}", style="success"),
            InlineKeyboardButton("❌ Cancel", callback_data="ab_cancel_wizard", style="danger")
        ]
    ])
    await message.reply_text(confirm_text, reply_markup=markup)

async def process_queue_worker(client, bot_username):
    while AUTO_BATCH_QUEUES[bot_username]:
        task = AUTO_BATCH_QUEUES[bot_username][0] # peek
        AUTO_BATCH_ACTIVE_TASKS[bot_username] = task
        task['status'] = 'running'

        try:
            loop = asyncio.get_running_loop()
            asyncio_task = loop.create_task(run_auto_batch_scan(client, task))
            task['asyncio_task'] = asyncio_task
            await asyncio_task
        except asyncio.CancelledError:
            task['status'] = 'cancelled'
            await edit_msg_safe(client, task['chat_id'], task['prompt_msg_id'], f"❌ <b>Task was cancelled.</b>")
        except Exception as e:
            task['status'] = 'failed'
            print(f"[WORKER TASK EXCEPTION] {e}")
            await edit_msg_safe(client, task['chat_id'], task['prompt_msg_id'], f"⚠️ <b>Task finished with note:</b> {e}\n\n<i>The bot remains active. You can retry anytime.</i>")
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

    try:
        from bot import Bot
        target_client = Bot.instances.get(target_bot_username) or client

        settings = await db.get_settings(bot_username=target_bot_username)
        session_str = settings.get('session_string')
        session_client = None
        if session_str:
            try:
                from plugins.start import get_session_client
                session_client = await get_session_client(session_str)
            except Exception as e:
                print(f"[AUTO BATCH] Error fetching session client: {e}")

        total_range = list(range(start_id, end_id + 1)) if start_id <= end_id else list(range(start_id, end_id - 1, -1))
        total_count = len(total_range)

        # Structure: season -> quality -> list of (number, num_type, message_id, caption_or_filename)
        groups = defaultdict(lambda: defaultdict(list))
        processed_keys = set()

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

                    caption_cleaned = clean_emojis_and_html(caption)
                    filename_cleaned = clean_emojis_and_html(filename)

                    # Search BOTH filename AND file caption for anime name
                    if anime_names:
                        matched = False
                        combined_text = f"{caption_cleaned} {filename_cleaned}".lower()
                        for name in anime_names:
                            cleaned_name = name.lower().strip()
                            if cleaned_name in combined_text:
                                matched = True
                                break
                        if not matched:
                            skipped_count += 1
                            continue

                    # Universal Season, Episode, Part detection
                    season_cap, ep_cap, type_cap = parse_metadata_universal(caption_cleaned)
                    season_fn, ep_fn, type_fn = parse_metadata_universal(filename_cleaned)

                    season = season_cap if ep_cap is not None else season_fn
                    num_val = ep_cap if ep_cap is not None else ep_fn
                    num_type = type_cap if type_cap != 'unknown' else type_fn

                    quality = detect_quality(caption_cleaned)
                    if quality == "UNKNOWN":
                        quality = detect_quality(filename_cleaned)

                    ep_key = (season, num_val, num_type, quality)
                    if ep_key in processed_keys:
                        duplicate_count += 1
                        continue

                    processed_keys.add(ep_key)

                    caption_or_filename = caption.strip() if caption and caption.strip() else filename
                    groups[season][quality].append((num_val, num_type, m.id, caption_or_filename))
                    matched_count += 1

                    await asyncio.sleep(0.01)

                scanned_count += len(batch_ids)

                now = time.time()
                if now - last_update_time >= 3.5:
                    last_update_time = now
                    elapsed = now - start_time
                    speed = round(scanned_count / elapsed, 1) if elapsed > 0 else 0
                    eta_secs = int((total_count - scanned_count) / speed) if speed > 0 else 0
                    eta_str = f"{eta_secs}s" if speed > 0 else "Calculating..."
                    percent = int((scanned_count / total_count) * 100) if total_count > 0 else 100
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
                        f"• <b>ETA:</b> <code>{eta_str}</code>"
                    )
                    await edit_msg_safe(client, chat_id, msg_id, progress_text)

                await asyncio.sleep(0.05)

            except FloodWait as e:
                await asyncio.sleep(e.value)
                error_count += len(batch_ids)
            except Exception as ex:
                print(f"[SCAN CHUNK ERROR] {ex}")
                error_count += len(batch_ids)

        # Check if any matching files found
        if not groups:
            task['status'] = 'failed'
            await edit_msg_safe(
                client, chat_id, msg_id,
                f"⚠️ <b>No matching files were found in this range.</b>\n\n"
                f"• <b>Search Name:</b> <code>{anime_disp}</code>\n"
                f"• <b>Range:</b> <code>{start_id}-{end_id}</code>\n\n"
                f"<i>Please verify the anime name / range and try again.</i>"
            )
            return

        task['status'] = 'generating'
        await edit_msg_safe(
            client, chat_id, msg_id,
            f"🔗 <b>Batching matches and generating protected links...</b>\n\n"
            f"• <b>Total Matched:</b> {matched_count}\n"
            f"• <b>Queue Position:</b> Publishing..."
        )

        final_output_blocks = []
        total_generated_batches = 0

        for season in sorted(groups.keys()):
            qualities_dict = groups[season]

            if is_adv:
                target_qualities = ["480P", "720P", "1080P"]
            else:
                target_qualities = sorted(qualities_dict.keys(), key=lambda q: QUALITY_PRIORITY.get(q, 100))

            for q in target_qualities:
                files = qualities_dict.get(q, [])
                if files:
                    files.sort(key=lambda x: episode_sort_key(x[0]))

                    # Honor requested count limit on actual available matched files
                    if episode_limit < len(files):
                        files = files[:episode_limit]

                    mids = [f[2] for f in files]
                    link = await generate_list_link(target_client, cid, mids, bot_username=target_bot_username)

                    first_num = files[0][0]
                    last_num = files[-1][0]
                    num_type = files[0][1]

                    type_label = "Part" if num_type == 'part' else "Episode" if num_type == 'episode' else "File"

                    range_label = f"{first_num} → {last_num}" if (first_num is not None and last_num is not None) else f"Season {season}"

                    first_caption = files[0][3]
                    last_caption = files[-1][3]

                    block = (
                        f"🎬 <b>Quality: {q}</b>\n"
                        f"📦 <b>{type_label} Range:</b> {range_label}\n"
                        f"<b>FIRST Caption:</b> {first_caption}\n"
                        f"<b>LAST Caption:</b> {last_caption}\n"
                        f"🔗 <b>Link:</b> <code>{link}</code>"
                    )
                    final_output_blocks.append(block)
                    total_generated_batches += 1
                elif is_adv:
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

            total_time = round(time.time() - start_time, 1)
            completion_text = (
                f"✅ <b>Auto Batch Task Completed!</b>\n\n"
                f"• <b>Anime:</b> <code>{anime_disp}</code>\n"
                f"• <b>Matched Files:</b> <code>{matched_count}</code>\n"
                f"• <b>Generated Batches:</b> <code>{total_generated_batches}</code>\n"
                f"• <b>Execution Time:</b> <code>{total_time}s</code>"
            )
            await edit_msg_safe(client, chat_id, msg_id, completion_text)

        task['status'] = 'completed'

    except Exception as e:
        task['status'] = 'failed'
        print(f"[RUN AUTO BATCH SCAN ERROR] {e}")
        await edit_msg_safe(
            client, chat_id, msg_id,
            f"⚠️ <b>Auto Batch Scan Completed with note:</b> `{e}`\n\n"
            f"<i>The bot remains active and stable.</i>"
        )


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

    if AUTO_BATCH_QUEUES[bot_username]:
        AUTO_BATCH_QUEUES[bot_username].clear()
        await message.reply_text("✅ <b>Cleared all queued Auto Batch tasks!</b>")
        return

    await message.reply_text("❌ <b>No running or queued Auto Batch task found to cancel.</b>")


@Client.on_callback_query(filters.regex(r"^(ab_start_|ab_cancel_wizard)"))
async def auto_batch_callbacks(client: Client, query: CallbackQuery):
    bot_username = client.username.lower()
    admin_id = query.from_user.id

    if not await db.admin_exist(admin_id) and admin_id != config.OWNER_ID:
        await query.answer("❌ You are not authorized!", show_alert=True)
        return

    if query.data == "ab_cancel_wizard":
        await query.message.delete()
        await query.answer("Wizard cancelled.")
        return

    if query.data.startswith("ab_start_"):
        is_adv = query.data.endswith("_adv")
        wizard_confirm_id = query.data.replace("ab_start_", "")
        if is_adv:
            wizard_confirm_id = wizard_confirm_id[:-4]
        else:
            wizard_confirm_id = wizard_confirm_id[:-4]

        configured_results = state_manager.get_state(bot_username, wizard_confirm_id)
        if not configured_results:
            await query.answer("⚠️ Session expired! Please run the command again.", show_alert=True)
            await query.message.delete()
            return

        results = configured_results.input_ranges
        state_manager.clear_state(bot_username, wizard_confirm_id)

        await query.message.delete()
        await query.answer("🚀 Queueing Auto Batch Tasks...")

        for idx, item in enumerate(results, 1):
            task_id = f"ab_{uuid.uuid4().hex[:8]}_{idx}"
            prompt_msg = await query.message.reply_text(f"⏳ <b>Queueing Task {idx}/{len(results)}:</b> <code>{task_id}</code>...")

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
