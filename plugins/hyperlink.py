import re
from pyrogram import Client, filters
from pyrogram.types import Message
from helper_func import admin

# Temporary in-memory session store (user_id -> list of collected URLs)
HYPERLINK_SESSIONS = {}

# Custom filter to check if a user is actively in hyperlink collection mode
def is_in_hyperlink_session(_, __, message: Message):
    if not message.from_user:
        return False
    return message.from_user.id in HYPERLINK_SESSIONS

hyperlink_session_filter = filters.create(is_in_hyperlink_session)

@Client.on_message(filters.private & filters.command("hyperlink"))
async def hyperlink_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    # Initialize/Reset the independent collection session
    HYPERLINK_SESSIONS[user_id] = []

    await message.reply_text(
        "Send or forward any Telegram messages, posts, captions, or media containing hyperlinks.\n\n"
        "• You can send unlimited messages.\n"
        "• The bot will collect every hyperlink and URL.\n"
        "• When you're finished, send \"/done\".\n"
        "• Send \"/cancel\" to cancel the operation."
    )

@Client.on_message(filters.private & hyperlink_session_filter & ~filters.command(["hyperlink"]))
async def collect_hyperlinks_handler(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text or message.caption or ""
    text_stripped = text.strip().lower()

    # Handle completion command
    if text_stripped == "/done":
        urls = HYPERLINK_SESSIONS.pop(user_id, [])
        if not urls:
            await message.reply_text("No hyperlinks or URLs were found in the submitted messages.")
            return

        # De-duplicate while strictly preserving original order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        if not unique_urls:
            await message.reply_text("No hyperlinks or URLs were found in the submitted messages.")
            return

        # Join raw URLs with single line breaks, no formatting/numbering/markdown
        output_text = "\n".join(unique_urls)

        # Chunk transmission if output exceeds Telegram's 4096 character limit
        if len(output_text) > 4096:
            chunks = [output_text[i:i+4096] for i in range(0, len(output_text), 4096)]
            for chunk in chunks:
                await message.reply_text(chunk, disable_web_page_preview=True)
        else:
            await message.reply_text(output_text, disable_web_page_preview=True)
        return

    # Handle cancel command
    if text_stripped == "/cancel":
        HYPERLINK_SESSIONS.pop(user_id, None)
        await message.reply_text("Hyperlink extraction has been cancelled.")
        return

    # Extract hyperlinks and raw URLs from the message
    extracted = []

    # 1. Extract hidden text_link and raw URL entities (from message text or caption)
    entities = message.entities or message.caption_entities
    if entities:
        for entity in entities:
            if entity.type.name == "TEXT_LINK":
                if entity.url:
                    extracted.append(entity.url)
            elif entity.type.name == "URL":
                raw_text = message.text or message.caption
                if raw_text:
                    url_val = raw_text[entity.offset : entity.offset + entity.length]
                    if url_val:
                        extracted.append(url_val)

    # 2. Extract standard URLs using regex matching as a fallback
    regex_pattern = r"(https?://[^\s<>\"'()]+)"
    found_regex = re.findall(regex_pattern, text)
    if found_regex:
        for url in found_regex:
            cleaned = url.rstrip('.,;!?)]} ')
            extracted.append(cleaned)

    # Append new URLs to the user's independent session list while keeping local duplicates filtered
    for url in extracted:
        if url not in HYPERLINK_SESSIONS[user_id]:
            HYPERLINK_SESSIONS[user_id].append(url)
