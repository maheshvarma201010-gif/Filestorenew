import uuid
import time
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio, InputMediaAnimation
)
from database.database import db
from helper_func import get_messages, get_filename

async def create_carousel_session(user_id, cid, ids, bot_username, base64_string=None):
    """
    Create a new carousel session in MongoDB to paginate messages.
    """
    session_id = str(uuid.uuid4()).replace("-", "")
    session = {
        "_id": session_id,
        "user_id": user_id,
        "cid": cid,
        "ids": ids,
        "bot_username": bot_username,
        "base64_string": base64_string,
        "created_at": time.time()
    }
    await db.database['carousels'].insert_one(session)
    return session_id

def get_input_media(msg, caption, parse_mode="html"):
    """
    Construct input media from message type.
    """
    if msg.photo:
        return InputMediaPhoto(msg.photo.file_id, caption=caption, parse_mode=parse_mode)
    elif msg.video:
        return InputMediaVideo(msg.video.file_id, caption=caption, parse_mode=parse_mode)
    elif msg.document:
        return InputMediaDocument(msg.document.file_id, caption=caption, parse_mode=parse_mode)
    elif msg.audio:
        return InputMediaAudio(msg.audio.file_id, caption=caption, parse_mode=parse_mode)
    elif msg.animation:
        return InputMediaAnimation(msg.animation.file_id, caption=caption, parse_mode=parse_mode)
    return None

async def render_carousel_page(client, session_id, page_idx):
    """
    Renders input media and pagination controls for a given page.
    """
    session = await db.database['carousels'].find_one({"_id": session_id})
    if not session:
        return None, None

    ids = session["ids"]
    cid = session["cid"]
    total = len(ids)

    if total == 0:
        return None, None

    page_idx = max(0, min(page_idx, total - 1))

    # Fetch the specific message for this page
    msg_id = ids[page_idx]
    msgs = await get_messages(client, [msg_id], chat_id=cid)
    if not msgs or not msgs[0]:
        return None, None

    msg = msgs[0]

    # Custom caption logic formatting
    settings_caption = await db.get_settings(bot_username=client.username)
    caption_active = settings_caption.get('custom_caption_active', True)
    custom_caption = settings_caption.get('custom_caption_text', "") if caption_active else ""

    original_caption = msg.caption.html if (msg.caption and hasattr(msg.caption, "html")) else (msg.caption or "")
    if not original_caption:
        original_caption = f"<b>{get_filename(msg)}</b>"

    # Enforce premium RichText layout formatting
    from utils.formatter import RichText
    header = RichText.format_heading("Carousel Content Delivery", level=2)
    quote = RichText.format_quote(original_caption, expandable=True)

    caption = f"{header}\n\n{quote}"
    if custom_caption:
        caption += f"\n\n{custom_caption}"
    caption += f"\n\n🎬 <b>Page {page_idx+1}/{total}</b>"

    # Build pagination keyboard
    buttons = []
    nav_row = []

    if total > 1:
        prev_idx = (page_idx - 1) % total
        next_idx = (page_idx + 1) % total

        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"car_idx:{session_id}:{prev_idx}"))
        nav_row.append(InlineKeyboardButton(f"Page {page_idx+1}/{total}", callback_data=f"car_info:{page_idx}"))
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"car_idx:{session_id}:{next_idx}"))

    if nav_row:
        buttons.append(nav_row)

    markup = InlineKeyboardMarkup(buttons)
    input_media = get_input_media(msg, caption)
    return input_media, markup
