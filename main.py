import proxy_manager
from bot import Bot
import pyrogram.utils
import asyncio
from database.database import db

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

async def start_clones():
    await asyncio.sleep(10) # Wait for main bot to be ready
    clones = await db.get_all_clones()
    for clone in clones:
        try:
            print(f"[CLONE] Starting bot: @{clone['username']}")
            bot = Bot(bot_token=clone['token'], name=clone['username'], db_channel_id=clone.get('channel_id'))
            await bot.start()
        except Exception as e:
            print(f"[CLONE ERROR] Failed to start @{clone.get('username')}: {e}")

async def main():
    print("[SYSTEM] Starting main bot instance...")
    main_bot = Bot()
    await main_bot.start()

    # Start clones in background
    asyncio.create_task(start_clones())

    print("[SYSTEM] All services initialized. Entering infinite loop.")
    await asyncio.Future()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
