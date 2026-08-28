import pyrogram
import pyrogram.types
from pyrogram.raw import types as raw_types
import re

# Monkeypatch InlineKeyboardButton.__init__ and write for custom styles & hashtag styling
original_init = pyrogram.types.InlineKeyboardButton.__init__

def patched_init(self, *args, style=None, **kwargs):
    original_init(self, *args, **kwargs)
    self.style = style

pyrogram.types.InlineKeyboardButton.__init__ = patched_init

original_write = pyrogram.types.InlineKeyboardButton.write

def patched_write(self, client):
    style_type = getattr(self, "style", None)
    text = self.text
    if text and "#" in text:
        for keyword, s_type in [("#primary", "primary"), ("#danger", "danger"), ("#success", "success"), ("#succes", "success")]:
            if keyword in text.lower():
                style_type = s_type
                self.style = s_type
                self.text = re.sub(re.escape(keyword), "", text, flags=re.IGNORECASE).strip()
                break

    res_btn = original_write(self, client)

    if style_type and hasattr(raw_types, "KeyboardButtonStyle"):
        bg_primary = style_type == "primary"
        bg_danger = style_type == "danger"
        bg_success = style_type == "success"
        res_btn.style = raw_types.KeyboardButtonStyle(
            bg_primary=bg_primary or None,
            bg_danger=bg_danger or None,
            bg_success=bg_success or None
        )
    return res_btn

pyrogram.types.InlineKeyboardButton.write = patched_write

# Monkeypatch Parser.handle_starttag for expandable blockquote support
from pyrogram.parser.html import Parser

original_handle_starttag = Parser.handle_starttag

def patched_handle_starttag(self, tag, attrs):
    original_handle_starttag(self, tag, attrs)
    if tag == "blockquote" and "expandable" in dict(attrs):
        if tag in self.tag_entities and self.tag_entities[tag]:
            self.tag_entities[tag][-1].collapsed = True

Parser.handle_starttag = patched_handle_starttag

# Patch to support message effects (e.g. fire effect) across Client & Message methods
from pyrogram.types import Message
import contextvars

_current_message_effect_id_var = contextvars.ContextVar("current_message_effect_id", default=None)

original_invoke = pyrogram.Client.invoke

async def patched_invoke(self, query, *args, **kwargs):
    effect_id = _current_message_effect_id_var.get()
    if effect_id is not None:
        if hasattr(query, "effect"):
            query.effect = int(effect_id)
    return await original_invoke(self, query, *args, **kwargs)

pyrogram.Client.invoke = patched_invoke

original_send_photo = pyrogram.Client.send_photo
async def patched_send_photo(self, *args, **kwargs):
    effect_id = kwargs.pop("message_effect_id", None)
    token = _current_message_effect_id_var.set(effect_id) if effect_id is not None else None
    try:
        return await original_send_photo(self, *args, **kwargs)
    finally:
        if token is not None:
            _current_message_effect_id_var.reset(token)

pyrogram.Client.send_photo = patched_send_photo

original_send_message = pyrogram.Client.send_message
async def patched_send_message(self, *args, **kwargs):
    effect_id = kwargs.pop("message_effect_id", None)
    token = _current_message_effect_id_var.set(effect_id) if effect_id is not None else None
    try:
        return await original_send_message(self, *args, **kwargs)
    finally:
        if token is not None:
            _current_message_effect_id_var.reset(token)

pyrogram.Client.send_message = patched_send_message

original_reply_photo = Message.reply_photo
async def patched_reply_photo(self, photo, *args, message_effect_id=None, **kwargs):
    token = _current_message_effect_id_var.set(message_effect_id) if message_effect_id is not None else None
    try:
        return await original_reply_photo(self, photo, *args, **kwargs)
    finally:
        if token is not None:
            _current_message_effect_id_var.reset(token)

Message.reply_photo = patched_reply_photo

original_reply = Message.reply
async def patched_reply(self, text, *args, message_effect_id=None, **kwargs):
    token = _current_message_effect_id_var.set(message_effect_id) if message_effect_id is not None else None
    try:
        return await original_reply(self, text, *args, **kwargs)
    finally:
        if token is not None:
            _current_message_effect_id_var.reset(token)

Message.reply = patched_reply

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
