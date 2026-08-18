import config
from database.database import db

# Cache for chat lookups to avoid redundant API hits
chat_cache = {}

async def resolve_channel_id(client, channel_ref):
    """
    Given a channel ID (int or str) or public username, resolves it to the absolute integer ID (e.g. -100123456789).
    """
    if not channel_ref:
        return None

    if isinstance(channel_ref, int):
        return channel_ref

    ref_str = str(channel_ref).strip()
    if ref_str.startswith("-100") and ref_str[4:].isdigit():
        return int(ref_str)
    if ref_str.isdigit():
        return int("-100" + ref_str)

    # Check cache
    ref_lower = ref_str.lower().replace("@", "")
    if ref_lower in chat_cache:
        return chat_cache[ref_lower]

    # Resolve via Telegram
    try:
        chat = await client.get_chat(channel_ref)
        chat_cache[ref_lower] = chat.id
        chat_cache[str(chat.id)] = chat.id
        if chat.username:
            chat_cache[chat.username.lower()] = chat.id
        return chat.id
    except Exception as e:
        print(f"[RESOLVER] Failed to resolve channel {channel_ref}: {e}")
        return None

async def find_channel_owner(channel_id: int):
    """
    Checks the database to find which bot/clone owns this channel_id.
    Returns the bot's username (lowercase) or None.
    """
    # 1. Check in channels collection
    doc = await db.channel_data.find_one({"channel_id": channel_id})
    if doc:
        return doc["bot_username"].lower()

    # 2. Check in clones collection
    clone_doc = await db.clones.find_one({"channel_id": channel_id})
    if clone_doc:
        return clone_doc["username"].lower()

    # 3. Check if it matches main bot's channel
    if abs(channel_id) == abs(config.CHANNEL_ID):
        return config.BOT_USERNAME.lower()

    return None

async def resolve_db_source(client, channel_ref):
    """
    Resolves the channel_id, the associated bot's username, and the running client.
    Supports fallback to the current client's default DB channel if channel_ref is None.
    """
    if not channel_ref:
        # Fallback to current client's default DB channel
        bot_username = client.username.lower()
        db_channels = await db.get_all_db_channels(client.username)
        channel_id = None
        if db_channels:
            channel_id = db_channels[0]
        else:
            if hasattr(client, 'db_channel_id') and client.db_channel_id:
                channel_id = client.db_channel_id
            elif hasattr(client, 'db_channel') and client.db_channel:
                channel_id = client.db_channel.id

        if channel_id:
            return channel_id, bot_username, client
        return None, None, None

    channel_id = await resolve_channel_id(client, channel_ref)
    if not channel_id:
        return None, None, None

    bot_username = await find_channel_owner(channel_id)
    if not bot_username:
        # Fall back to current client's username
        bot_username = client.username.lower()

    from bot import Bot
    running_client = Bot.instances.get(bot_username)
    if not running_client:
        # If the bot is registered but not loaded in instances, we can use the current client as fallback
        running_client = client

    return channel_id, bot_username, running_client
