import re

def parse_telegram_link(link: str):
    """
    Parses a telegram link and returns a tuple (channel_id_or_username, message_id).
    Supports t.me, telegram.me, telegram.dog, both public and private link formats.
    Returns None if the link is invalid.
    """
    link = link.strip()
    # Normalize link (remove spaces)
    link = re.sub(r'\s+', '', link)

    # Match patterns for t.me, telegram.me, telegram.dog
    pattern = r'(?:https?://)?(?:t\.me|telegram\.(?:me|dog))/(?:c/)?([a-zA-Z0-9_-]+)/(\d+)'
    match = re.match(pattern, link, re.IGNORECASE)
    if not match:
        return None

    channel, msg_id = match.groups()
    msg_id = int(msg_id)

    # If the channel is a numeric string (private channel ID)
    if channel.isdigit() or (channel.startswith('-') and channel[1:].isdigit()):
        val = int(channel)
        # Ensure it has standard -100 prefix internally
        val_str = str(val)
        if not val_str.startswith("-100"):
            if val_str.startswith("-"):
                val = int("-100" + val_str[1:])
            else:
                val = int("-100" + val_str)
        return val, msg_id

    return channel, msg_id

def normalize_telegram_url(channel, msg_id):
    """
    Generates a normalized telegram link for internal or external output.
    Ensures that every generated URL has a valid https:// protocol and never returns invalid formats.
    """
    if isinstance(channel, int):
        # Numeric private channel ID
        # Strip -100 for the URL format
        clean_id = str(channel).replace("-100", "").replace("-", "")
        return f"https://t.me/c/{clean_id}/{msg_id}"

    return f"https://t.me/{channel}/{msg_id}"
