import re
import unicodedata
from helper_func import get_filename

def clean_emojis_and_html(text):
    if not text:
        return ""
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Strip emojis and symbols using unicodedata category checks
    cleaned_chars = []
    for char in text:
        category = unicodedata.category(char)
        if category.startswith('S') or category.startswith('C'):
            cleaned_chars.append(' ')
        else:
            cleaned_chars.append(char)

    text = "".join(cleaned_chars)
    return " ".join(text.split())

def determine_filename(msg):
    """
    Determines filename with priority:
    1. File caption
    2. Telegram document/video/audio filename
    3. Message media filename
    4. Fallback filename
    """
    # 1. File caption
    if msg.caption:
        caption_cleaned = clean_emojis_and_html(msg.caption)
        if caption_cleaned:
            return caption_cleaned

    # 2. Telegram document/video/audio filename
    if msg.document and msg.document.file_name:
        return msg.document.file_name
    if msg.video and msg.video.file_name:
        return msg.video.file_name
    if msg.audio and msg.audio.file_name:
        return msg.audio.file_name

    # 3. Message media filename
    media = msg.document or msg.video or msg.audio or msg.animation
    if media and getattr(media, "file_name", None):
        return media.file_name

    # 4. Fallback filename
    return "File"

def determine_caption(msg):
    """
    Caption priority: Use complete original file caption whenever available.
    Do NOT truncate the caption unnecessarily. If no caption exists, N/A.
    """
    if msg.caption:
        return msg.caption.html if hasattr(msg.caption, "html") else msg.caption
    return "N/A"

def get_message_metadata(msg):
    """
    Extracts filename and caption details from a Telegram Message.
    """
    if not msg or msg.empty:
        return {
            'filename': 'File',
            'caption': 'N/A',
            'has_media': False
        }

    filename = determine_filename(msg)
    caption = determine_caption(msg)
    has_media = bool(msg.document or msg.video or msg.audio or msg.animation or msg.photo)

    return {
        'filename': filename,
        'caption': caption,
        'has_media': has_media
    }
