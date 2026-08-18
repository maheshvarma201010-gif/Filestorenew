import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from helper_func import admin, BotAdminTaskContext
from database.database import db

def parse_duration(duration_str):
    m = re.match(r'^(\d+)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours|d|day|days|y|yr|year|years)$', duration_str.strip().lower())
    if not m:
        return None
    val = int(m.group(1))
    unit_str = m.group(2)
    if unit_str.startswith('s'):
        unit = 's'
    elif unit_str.startswith('m'):
        unit = 'm'
    elif unit_str.startswith('h'):
        unit = 'h'
    elif unit_str.startswith('d'):
        unit = 'd'
    elif unit_str.startswith('y'):
        unit = 'y'
    else:
        return None
    return val, unit

def get_duration_seconds(time_val, time_unit):
    if time_unit == 's':
        return time_val
    elif time_unit == 'm':
        return time_val * 60
    elif time_unit == 'h':
        return time_val * 3600
    elif time_unit == 'd':
        return time_val * 86400
    elif time_unit == 'y':
        return time_val * 31536000
    return 0

@Client.on_message(filters.private & admin & filters.command('gencode'))
async def gencode_cmd(client: Client, message: Message):
    async with BotAdminTaskContext(client, message.from_user.id, message):
        # Step 2: Ask for code name
        code_name = None
        while True:
            try:
                ask_name = await client.ask(message.chat.id, "<b>Enter the code name.</b>\n\nExample:\n<code>hemanth</code>\n\nType /cancel to cancel.", filters=filters.text, timeout=60)
                if ask_name.text.lower() == "/cancel":
                    await ask_name.reply("❌ <b>Generation Cancelled.</b>")
                    return
                candidate = ask_name.text.strip()
                if not candidate or "/" in candidate or " " in candidate:
                    await ask_name.reply("❌ <b>Invalid code name! Code name must not contain spaces or slashes. Please enter again or send /cancel.</b>")
                    continue
                code_name = candidate
                break
            except asyncio.TimeoutError:
                await message.reply("⏰ <b>Timeout! Process Cancelled.</b>")
                return

        # Step 4: Ask for premium validity duration
        val_value, val_unit = None, None
        validity_prompt = (
            "<b>Enter the premium validity for users who redeem this code.</b>\n\n"
            "Supported formats:\n"
            "• <code>1d</code> or <code>1day</code> (Days)\n"
            "• <code>12h</code> or <code>12hours</code> (Hours)\n"
            "• <code>30m</code> or <code>30minutes</code> (Minutes)\n"
            "• <code>45s</code> or <code>45seconds</code> (Seconds)\n\n"
            "Type /cancel to cancel."
        )
        while True:
            try:
                ask_validity = await client.ask(message.chat.id, validity_prompt, filters=filters.text, timeout=60)
                if ask_validity.text.lower() == "/cancel":
                    await ask_validity.reply("❌ <b>Generation Cancelled.</b>")
                    return

                parsed_validity = parse_duration(ask_validity.text)
                if not parsed_validity:
                    await ask_validity.reply("❌ <b>Invalid format! Please use a valid format (e.g., 1d, 12h, 30m) or send /cancel.</b>")
                    continue
                val_value, val_unit = parsed_validity
                break
            except asyncio.TimeoutError:
                await message.reply("⏰ <b>Timeout! Process Cancelled.</b>")
                return

        # Step 6: Ask for claim limit
        claim_limit = None
        while True:
            try:
                ask_limit = await client.ask(message.chat.id, "<b>How many users can claim this code?</b>\n\nExample:\n<code>100</code>\n\nType /cancel to cancel.", filters=filters.text, timeout=60)
                if ask_limit.text.lower() == "/cancel":
                    await ask_limit.reply("❌ <b>Generation Cancelled.</b>")
                    return

                clean_limit = ask_limit.text.strip()
                if not clean_limit.isdigit() or int(clean_limit) <= 0:
                    await ask_limit.reply("❌ <b>Invalid limit! Please send a valid positive number or send /cancel.</b>")
                    continue
                claim_limit = int(clean_limit)
                break
            except asyncio.TimeoutError:
                await message.reply("⏰ <b>Timeout! Process Cancelled.</b>")
                return

        # Step 8: Ask for code expiry duration
        exp_value, exp_unit = None, None
        expiry_prompt = (
            "<b>How long should this redeem code remain active before it expires?</b>\n\n"
            "Supported formats:\n"
            "• <code>5d</code> or <code>5days</code> (Days)\n"
            "• <code>12h</code> (Hours)\n"
            "• <code>30m</code> (Minutes)\n\n"
            "Type /cancel to cancel."
        )
        while True:
            try:
                ask_expiry = await client.ask(message.chat.id, expiry_prompt, filters=filters.text, timeout=60)
                if ask_expiry.text.lower() == "/cancel":
                    await ask_expiry.reply("❌ <b>Generation Cancelled.</b>")
                    return

                parsed_expiry = parse_duration(ask_expiry.text)
                if not parsed_expiry:
                    await ask_expiry.reply("❌ <b>Invalid format! Please use a valid format (e.g., 5d, 12h, 30m) or send /cancel.</b>")
                    continue
                exp_value, exp_unit = parsed_expiry
                break
            except asyncio.TimeoutError:
                await message.reply("⏰ <b>Timeout! Process Cancelled.</b>")
                return

        # Calculate absolute code expiry timestamp
        seconds_active = get_duration_seconds(exp_value, exp_unit)
        expires_at_timestamp = time.time() + seconds_active

        # Save redeem code permanently in MongoDB
        doc_id = code_name.strip().lower()
        code_data = {
            "_id": doc_id,
            "code": code_name,
            "validity_value": val_value,
            "validity_unit": val_unit,
            "claim_limit": claim_limit,
            "claim_count": 0,
            "claimed_users": [],
            "expires_at": expires_at_timestamp
        }
        await db.database['redeem_codes'].update_one(
            {"_id": doc_id},
            {"$set": code_data},
            upsert=True
        )

        redeem_link = f"https://t.me/{client.username}?start=redeem_{code_name}"
        success_text = (
            "<b>━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎁 ˹ ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ ɢᴇɴᴇʀᴀᴛᴇᴅ ˼ 🎁\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"◈ 📝 <b>Code Name:</b> <code>{code_name}</code>\n"
            f"◈ 👑 <b>Premium Validity:</b> <code>{val_value} {val_unit}</code>\n"
            f"◈ 👥 <b>Claim Limit:</b> <code>{claim_limit} users</code>\n"
            f"◈ ⏳ <b>Code Active For:</b> <code>{exp_value} {exp_unit}</code>\n\n"
            f"🔗 <b>Redeem Link:</b>\n<code>{redeem_link}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await message.reply_text(success_text)
