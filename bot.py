
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

import uvicorn
import asyncio
try:
    import pyromod
except ImportError:
    import pyromod.listen
from pyrogram import Client
from pyrogram.types import BotCommand
from pyrogram.enums import ParseMode
import sys
import pytz
from datetime import datetime
#ᴀɴɪᴢᴏɴᴇꜰʟɪx on ᴛɢ
from config import *
from database.db_premium import *
from database.database import *
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

# Suppress APScheduler logs below WARNING level
logging.getLogger("apscheduler").setLevel(logging.WARNING)

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
scheduler.add_job(remove_expired_users, "interval", seconds=10)

# Reset verify count for all users daily at 00:00 IST
async def daily_reset_task():
    try:
        await db.reset_all_verify_counts()
    except Exception:
        pass

async def token_cleanup_task():
    try:
        await db.cleanup_strict_verifications()
    except Exception:
        pass

scheduler.add_job(daily_reset_task, "cron", hour=0, minute=0)
scheduler.add_job(token_cleanup_task, "interval", hours=1)
# scheduler.start() is called inside Bot.start() to ensure an active event loop


def get_indian_time():
    """Returns the current time in IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)


name = """
 BY AniZoneFlix BOTS
"""

class Bot(Client):
    instances = {}
    helper_clients = {} # token -> Client
    helper_stats = {} # token -> active_tasks_count

    def __init__(self, bot_token=TG_BOT_TOKEN, name="Bot", db_channel_id=CHANNEL_ID):
        super().__init__(
            name=name,
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=bot_token,
            in_memory=True
        )
        self.LOGGER = LOGGER
        self.db_channel_id = db_channel_id

    async def start(self):
        # Start Web Server immediately to satisfy Railway/cloud health checks and bind to PORT
        if self.name == "Bot":
            print("[STARTUP] Initializing FastAPI Web Server (Priority)...")
            from web_server import web_server
            app = await web_server(self)

            config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
            self.server = uvicorn.Server(config)

            # Run uvicorn in background
            asyncio.create_task(self.server.serve())
            print(f"[STARTUP] FastAPI Web Server running on port {PORT}")

        print(f"[STARTUP] Initializing Bot: {self.name}...")
        await super().start()
        print(f"[STARTUP] Pyrogram super().start() successful for {self.name}.")
        usr_bot_me = await self.get_me()
        self.username = usr_bot_me.username.lower()
        Bot.instances[self.username] = self

        # Continue with other initialization in background or subsequently
        asyncio.create_task(self.initialize_heavy_tasks())

        self.uptime = get_indian_time()
        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Bot @{self.username} is initializing background tasks...")

    async def initialize_heavy_tasks(self):
        """Perform slow initialization tasks in the background."""
        await db.create_indexes()

        # Load helper bots
        helpers = await db.get_helper_bots()
        for h in helpers:
            asyncio.create_task(self.start_helper_bot(h['token']))

        if not scheduler.running:
            scheduler.start()

        try:
            await db.clear_all_bans()
        except: pass

        # Set Bot Commands
        try:
            await self.set_bot_commands([
                BotCommand("start", "🚀 Ignite the Bot 🔥"),
                BotCommand("ping", "🏓 Check Connection Speed ⚡"),
                BotCommand("myplan", "🎖️ Check Premium Status 💎"),
                BotCommand("about", "🛡️ Discover Our Legacy"),
                BotCommand("help", "✨ Seek Guidance"),
                BotCommand("commands", "⚙️ Admin Core Control (Admin)"),
                BotCommand("auto_delete", "🕒 Set Auto-Delete Timer (Admin)"),
                BotCommand("check_auto_delete", "🔍 Check Auto-Delete Timer (Admin)"),
                BotCommand("batch", "📦 Create Batch Link (Admin)"),
                BotCommand("auto_batch", "📦 Auto Batch Files by Quality (Admin)"),
                BotCommand("cbatch", "📦 Create multiple custom range batches (Admin)"),
                BotCommand("gencode", "🎁 Generate premium redeem codes (Admin)"),
                BotCommand("genlink", "🔗 Generate Single Link (Admin)"),
                BotCommand("save", "📤 System Backup & Restore (Admin)"),
                BotCommand("panel", "🛠️ Security Control Panel (Admin)"),
                BotCommand("restart", "🔄 Reboot System (Admin)"),
                BotCommand("stats", "📊 System Insights (Admin)"),
                BotCommand("ban", "🚫 Ban a User (Admin)"),
                BotCommand("unban", "🔓 Unban a User (Admin)"),
                BotCommand("addchnl", "🔗 Add Force Sub Channel (Admin)"),
                BotCommand("delchnl", "❌ Remove Force Sub Channel (Admin)"),
                BotCommand("listchnl", "📋 List All Force Sub Channels (Admin)"),
                BotCommand("fsub_mode", "⚙️ Toggle Force Sub Mode (Admin)"),
                BotCommand("dbroadcast", "📢 Media Broadcast (Admin)"),
                BotCommand("addpremium", "💎 Grant Premium Access (Admin)"),
                BotCommand("premium_users", "⭐ Show Elite Users (Admin)"),
                BotCommand("count", "📈 Today's Verification Stats (Admin)"),
                BotCommand("info", "📊 Check User FSUB Status (Admin)"),
                BotCommand("fsubbot", "🤖 Manage Required Bots (Owner)"),
                BotCommand("dbchnl", "📋 Manage DB Channels (Admin)")
            ])
        except: pass

        try:
            self.db_channel = await self.get_chat(self.db_channel_id)
        except: pass

        # Validate verify log destinations on startup
        if self.name == "Bot":
            asyncio.create_task(self.validate_verify_log_destinations())

        # Resume interrupted tasks upon startup
        asyncio.create_task(self.resume_interrupted_tasks())

        try: await self.send_message(OWNER_ID, text = f"<b><blockquote> Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ by @AniZoneFlix</blockquote></b>")
        except: pass
        print(f"[STARTUP] Background initialization complete for {self.username}")

    async def validate_verify_log_destinations(self):
        if self.name != "Bot":
            return
        dests = await db.get_verify_log_destinations()
        if not dests:
            return

        print(f"[VERIFY LOG] Validating {len(dests)} configured destinations on startup...")
        invalid_reports = []

        for d in dests:
            cid = d['chat_id']
            title = d.get('title', str(cid))
            try:
                chat = await self.get_chat(cid)
                member = await self.get_chat_member(cid, "me")
                from pyrogram.enums import ChatMemberStatus
                if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    invalid_reports.append(f"• <b>{title}</b> (<code>{cid}</code>): Bot @{self.username} is no longer an administrator.")
                    continue

                test_msg = await self.send_message(cid, "<b>⚙️ Verify Log Startup Validation</b>\n\nTesting logging capabilities on startup...")
                await asyncio.sleep(0.5)
                await test_msg.delete()
            except Exception as e:
                invalid_reports.append(f"• <b>{title}</b> (<code>{cid}</code>): `{e}`")

        if invalid_reports:
            report_text = (
                "⚠️ <b>˹ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ʟᴏɢ STARTUP WARNING ˼</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "The following configured Verify Log destinations failed validation on startup:\n\n"
                + "\n".join(invalid_reports) +
                "\n\n━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            print(f"[VERIFY LOG WARNING] {report_text}")
            try:
                await self.send_message(OWNER_ID, report_text)
            except Exception:
                pass

    async def resume_interrupted_tasks(self):
        """Query and resume interrupted broadcasts or other tasks from active_tasks collection."""
        try:
            running_tasks = await db.database['active_tasks'].find({"status": "running"}).to_list(length=None)
            if running_tasks:
                print(f"[RESUME] Found {len(running_tasks)} active tasks to resume.")
                from plugins.broadcast import resume_broadcast
                from plugins.start import resume_delivery
                for task in running_tasks:
                    print(f"[RESUME] Resuming task: {task['_id']}")
                    task_type = task.get("type")
                    if task_type == "broadcast":
                        asyncio.create_task(resume_broadcast(self, task))
                    elif task_type == "delivery":
                        asyncio.create_task(resume_delivery(self, task))
        except Exception as e:
            print(f"[RESUME ERROR] Failed to resume tasks: {e}")

    async def start_helper_bot(self, token):
        if token in Bot.helper_clients:
            return

        try:
            client = Client(
                name=f"helper_{token.split(':')[0]}",
                api_id=APP_ID,
                api_hash=API_HASH,
                bot_token=token,
                in_memory=True
            )
            await client.start()
            Bot.helper_clients[token] = client
            Bot.helper_stats[token] = 0
            print(f"[HELPER] Bot @{(await client.get_me()).username} started.")
        except Exception as e:
            print(f"[HELPER] Failed to start bot with token {token[:10]}... : {e}")

    async def stop_helper_bot(self, token):
        client = Bot.helper_clients.pop(token, None)
        Bot.helper_stats.pop(token, None)
        if client:
            try:
                await client.stop()
                print(f"[HELPER] Bot stopped.")
            except: pass

    async def stop(self, *args):
        if self.name == "Bot" and hasattr(self, 'server'):
            await self.server.shutdown()

        # Stop all helpers
        for token in list(Bot.helper_clients.keys()):
            await self.stop_helper_bot(token)

        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        """Run the bot with global event loop safeguard."""
        print("[STARTUP] Entering loop.run_forever()...")
        loop = asyncio.get_event_loop()

        def global_exception_handler(loop, context):
            exception = context.get('exception')
            msg = context.get('message')
            print(f"[EVENT LOOP SAFEGUARD] Intercepted unhandled exception: {exception or msg}")

        loop.set_exception_handler(global_exception_handler)

        loop.run_until_complete(self.start())
        self.LOGGER(__name__).info("Bot is now running. Thanks to @AniZoneFlix")
        print("[STARTUP] Bot is fully operational.")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Shutting down...")
        finally:
            loop.run_until_complete(self.stop())

#
# Copyright (C) 2025 by AniZoneFlix@AniZoneFlix, < https://github.com/AniZoneFlix >.
#
# This file is part of < https://t.me/AniZoneFlix > project,
# and is released under the MIT License.
# Please see < https://t.me/AniZoneFlix/blob/master/LICENSE >
#
# All rights reserved.