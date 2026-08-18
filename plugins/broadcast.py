import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup
from helper_func import InlineKeyboardButton, random_button_style, ButtonStyle, admin, get_readable_time
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from config import *
from database.database import db
from utils.formatter import RichText

# Progress bar helper
def make_progress_bar(percentage: int) -> str:
    completed = percentage // 10
    remaining = 10 - completed
    return "█" * completed + "░" * remaining

# Active Task Queue and Runner
async def run_broadcast_task(client: Client, task: dict):
    task_id = task["_id"]
    subtype = task["subtype"]
    broadcast_msg_id = task["message_id"]
    from_chat_id = task["chat_id"]
    duration = task.get("duration", 0)
    user_ids = task["user_ids"]
    current_index = task.get("current_index", 0)

    # Initialize / retrieve counters
    successful = task.get("successful", 0)
    failed = task.get("failed", 0)
    blocked = task.get("blocked", 0)
    deleted = task.get("deleted", 0)

    admin_chat_id = task["admin_chat_id"]
    admin_message_id = task["admin_message_id"]
    start_time = task.get("start_time", time.time())

    total_users = len(user_ids)
    remaining_users = total_users - current_index

    # Try fetching the original message
    try:
        broadcast_msg = await client.get_messages(from_chat_id, broadcast_msg_id)
        if not broadcast_msg or broadcast_msg.empty:
            raise Exception("Original broadcast message not found or empty.")
    except Exception as e:
        print(f"[BROADCAST ERROR] Original message fetch failed: {e}")
        await db.database['active_tasks'].update_one(
            {"_id": task_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        try:
            await client.send_message(admin_chat_id, f"❌ **Broadcast Failed:** Original message not found.")
        except: pass
        return

    # Try retrieving status message to edit
    status_msg = None
    try:
        status_msg = await client.get_messages(admin_chat_id, admin_message_id)
    except:
        pass

    # Concurrent worker queue setup
    queue = asyncio.Queue()
    for uid in user_ids[current_index:]:
        await queue.put(uid)

    # Concurrency limit (15 parallel workers)
    CONCURRENCY = 15

    # Counters wrapped in a dict/list for reference in parallel workers
    stats = {
        "successful": successful,
        "failed": failed,
        "blocked": blocked,
        "deleted": deleted,
        "processed": current_index,
        "last_db_save": time.time(),
        "last_ui_update": time.time()
    }

    async def worker():
        while not queue.empty():
            chat_id = await queue.get()
            try:
                sent_msg = None

                is_legacy = False
                try:
                    user_doc = await db.user_data.find_one({"_id": chat_id})
                    if user_doc and user_doc.get("legacy_client") is True:
                        is_legacy = True
                except: pass

                original_caption = broadcast_msg.caption.html if (broadcast_msg.caption and hasattr(broadcast_msg.caption, "html")) else (broadcast_msg.caption or "")
                caption = RichText.clean_unsupported(original_caption, is_legacy=is_legacy) if original_caption else None

                # Handle dbroadcast vs pbroadcast vs broadcast
                # Prefer forward_messages to ensure the forward tag and inline keyboard buttons are preserved
                try:
                    sent_msg = await client.forward_messages(chat_id, broadcast_msg.chat.id, broadcast_msg.id)
                except Exception:
                    if caption:
                        sent_msg = await client.copy_message(chat_id, broadcast_msg.chat.id, broadcast_msg.id, caption=caption)
                    else:
                        sent_msg = await broadcast_msg.copy(chat_id)

                if subtype == "pin" and sent_msg:
                    try:
                        await client.pin_chat_message(chat_id=chat_id, message_id=sent_msg.id, both_sides=True)
                    except: pass
                elif subtype == "auto_delete" and sent_msg:
                    # Run background deletion task
                    async def delayed_delete(msg, wait_time):
                        try:
                            await asyncio.sleep(wait_time)
                            await msg.delete()
                        except: pass
                    asyncio.create_task(delayed_delete(sent_msg, duration))

                stats["successful"] += 1
                await asyncio.sleep(0.1) # Safe rate-limiting delay between sends
            except FloodWait as e:
                # Automatic backoff and retry on FloodWait
                await asyncio.sleep(e.value + 1)
                try:
                    try:
                        sent_msg = await client.forward_messages(chat_id, broadcast_msg.chat.id, broadcast_msg.id)
                    except Exception:
                        if caption:
                            sent_msg = await client.copy_message(chat_id, broadcast_msg.chat.id, broadcast_msg.id, caption=caption)
                        else:
                            sent_msg = await broadcast_msg.copy(chat_id)

                    if subtype == "pin" and sent_msg:
                        try:
                            await client.pin_chat_message(chat_id=chat_id, message_id=sent_msg.id, both_sides=True)
                        except: pass
                    elif subtype == "auto_delete" and sent_msg:
                        async def delayed_delete(msg, wait_time):
                            try:
                                await asyncio.sleep(wait_time)
                                await msg.delete()
                            except: pass
                        asyncio.create_task(delayed_delete(sent_msg, duration))

                    stats["successful"] += 1
                    await asyncio.sleep(0.1) # Safe rate-limiting delay between sends
                except UserIsBlocked:
                    await db.del_user(chat_id)
                    stats["blocked"] += 1
                except InputUserDeactivated:
                    await db.del_user(chat_id)
                    stats["deleted"] += 1
                except Exception:
                    stats["failed"] += 1
            except UserIsBlocked:
                await db.del_user(chat_id)
                stats["blocked"] += 1
            except InputUserDeactivated:
                await db.del_user(chat_id)
                stats["deleted"] += 1
            except Exception:
                stats["failed"] += 1

            stats["processed"] += 1
            queue.task_done()

            # Dynamic persistence to MongoDB (every 20 users or 5 seconds)
            now = time.time()
            if stats["processed"] % 20 == 0 or now - stats["last_db_save"] > 5:
                stats["last_db_save"] = now
                await db.database['active_tasks'].update_one(
                    {"_id": task_id},
                    {"$set": {
                        "current_index": stats["processed"],
                        "successful": stats["successful"],
                        "failed": stats["failed"],
                        "blocked": stats["blocked"],
                        "deleted": stats["deleted"]
                    }}
                )

            # Progressive UI updates with safe 3-second rate limit
            if status_msg and (stats["processed"] % 10 == 0 or now - stats["last_ui_update"] > 3):
                stats["last_ui_update"] = now
                pct = int((stats["processed"] / total_users) * 100)
                bar = make_progress_bar(pct)
                elapsed = now - start_time
                speed = round(stats["processed"] / elapsed, 1) if elapsed > 0 else 0
                remaining = total_users - stats["processed"]
                eta_secs = int(remaining / speed) if speed > 0 else 0
                eta = get_readable_time(eta_secs) if speed > 0 else "00:00:00"

                try:
                    await status_msg.edit_text(
                        "📢 <b>Broadcasting...</b>\n\n"
                        f"{bar}\n\n"
                        f"<b>Progress:</b> <code>{pct}%</code>\n\n"
                        f"✅ <b>Success:</b> <code>{stats['successful']}</code>\n"
                        f"❌ <b>Failed:</b> <code>{stats['failed']}</code>\n"
                        f"🚫 <b>Blocked:</b> <code>{stats['blocked']}</code>\n"
                        f"⚠️ <b>Deleted:</b> <code>{stats['deleted']}</code>\n"
                        f"⏳ <b>Remaining:</b> <code>{remaining}</code>\n"
                        f"⚡ <b>Speed:</b> <code>{speed} users/sec</code>\n"
                        f"🕒 <b>ETA:</b> <code>{eta}</code>"
                    )
                except Exception:
                    pass

    # Start parallel workers
    workers_tasks = [asyncio.create_task(worker()) for _ in range(min(CONCURRENCY, remaining_users or 1))]
    await asyncio.gather(*workers_tasks)

    # Save final completed task status
    await db.database['active_tasks'].update_one(
        {"_id": task_id},
        {"$set": {
            "status": "completed",
            "current_index": stats["processed"],
            "successful": stats["successful"],
            "failed": stats["failed"],
            "blocked": stats["blocked"],
            "deleted": stats["deleted"]
        }}
    )

    # Final report to admin
    final_report = (
        "✨ <b>˹ ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ˼</b>\n\n"
        f"👤 <b>ᴛᴏᴛᴀʟ ᴜsᴇʀs:</b> <code>{total_users}</code>\n"
        f"✅ <b>sᴜᴄᴄᴇssꜰᴜʟ:</b> <code>{stats['successful']}</code>\n"
        f"🚫 <b>ʙʟᴏᴄᴋᴇᴅ:</b> <code>{stats['blocked']}</code>\n"
        f"❌ <b>ᴅᴇʟᴇᴛᴇᴅ:</b> <code>{stats['deleted']}</code>\n"
        f"⚠️ <b>ꜰᴀɪʟᴇᴅ:</b> <code>{stats['failed']}</code>"
    )

    if status_msg:
        try:
            await status_msg.edit_text(final_report)
        except:
            try:
                await client.send_message(admin_chat_id, final_report)
            except: pass
    else:
        try:
            await client.send_message(admin_chat_id, final_report)
        except: pass


# Startup resume task function
async def resume_broadcast(client: Client, task: dict):
    try:
        await run_broadcast_task(client, task)
    except Exception as e:
        print(f"[RESUME ERROR] Task {task['_id']} failed: {e}")


# Command entry points
async def start_broadcast_flow(client: Client, message: Message, subtype: str, duration: int = 0):
    if not message.reply_to_message:
        return await message.reply("`Reply to a message to broadcast it.`")

    query = await db.full_userbase()
    if not query:
        return await message.reply("❌ No users found in database to broadcast to.")

    status_msg = await message.reply("⏳ <b><i>˹ ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴɪᴛɪᴀᴛɪɴɢ... ˼</i></b>")

    # Save active task inside MongoDB to survive restart
    import uuid
    task_id = str(uuid.uuid4())
    task = {
        "_id": task_id,
        "type": "broadcast",
        "subtype": subtype,
        "status": "running",
        "message_id": message.reply_to_message.id,
        "chat_id": message.reply_to_message.chat.id,
        "duration": duration,
        "user_ids": query,
        "current_index": 0,
        "successful": 0,
        "failed": 0,
        "blocked": 0,
        "deleted": 0,
        "admin_chat_id": message.chat.id,
        "admin_message_id": status_msg.id,
        "start_time": time.time()
    }

    await db.database['active_tasks'].insert_one(task)

    # Run the broadcast task
    asyncio.create_task(run_broadcast_task(client, task))


@Client.on_message(filters.private & filters.command('pbroadcast') & admin)
async def pbroadcast_handler(client: Client, message: Message):
    await start_broadcast_flow(client, message, "pin")


@Client.on_message(filters.private & filters.command('broadcast') & admin)
async def broadcast_handler(client: Client, message: Message):
    await start_broadcast_flow(client, message, "normal")


@Client.on_message(filters.command("dbroadcast") & admin & filters.private)
async def dbroadcast_handler(client: Client, message: Message):
    try:
        duration = int(message.command[1])  # Get duration in seconds
    except (IndexError, ValueError):
        return await message.reply("<b>Pʟᴇᴀsᴇ ᴜsᴇ ᴀ ᴠᴀʟɪᴅ ᴅᴜʀᴀᴛɪᴏɴ ɪɴ sᴇᴄᴏɴᴅs.</b> Usᴀɢᴇ: /dbroadcast {duration}")

    await start_broadcast_flow(client, message, "auto_delete", duration)