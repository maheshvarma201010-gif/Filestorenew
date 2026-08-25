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

import re
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery, WebAppInfo
from pyrogram.errors import MessageNotModified, FloodWait
from config import OWNER_ID, BOT_USERNAME, WEBSITE_URL, TUT_VID
import urllib.parse
from helper_func import encode, get_message_id, admin, get_messages, get_filename, get_exp_time, InlineKeyboardButton
from database.database import db
from utils.formatter import RichText
from database.db_premium import is_premium_user

# Global in-memory search sessions to track user search states
# user_id -> session dict
SEARCH_SESSIONS = {}

def extract_metadata(filename, caption):
    text = f"{filename or ''}\n{caption or ''}".strip()

    # Flags
    ova = bool(re.search(r'\bova\b', text, re.IGNORECASE))
    ona = bool(re.search(r'\bona\b', text, re.IGNORECASE))
    special = bool(re.search(r'\bspecial\b', text, re.IGNORECASE))
    extra = bool(re.search(r'\bextra\b', text, re.IGNORECASE))
    ncop = bool(re.search(r'\bncop\b', text, re.IGNORECASE))
    nced = bool(re.search(r'\bnced\b', text, re.IGNORECASE))
    movie = bool(re.search(r'\bmovie\b', text, re.IGNORECASE))

    # File extension
    ext = ""
    if filename:
        parts = filename.split('.')
        if len(parts) > 1:
            ext = parts[-1].lower()

    # Resolution
    resolution = ""
    res_match = re.search(r'\b(\d{3,4}p|4k|8k|2k|uhd|fhd|hd|sd)\b', text, re.IGNORECASE)
    if res_match:
        resolution = res_match.group(1).upper()
    else:
        # try matching digits before p (like 1080P, 720p)
        res_match2 = re.search(r'\b(\d{3,4})[pP]\b', text)
        if res_match2:
            resolution = f"{res_match2.group(1)}P"

    # Quality
    quality = ""
    # Look for common quality indicators
    qual_patterns = [r'\bweb-dl\b', r'\bwebrip\b', r'\bbluray\b', r'\bhdtv\b', r'\bbrrip\b', r'\bdvdrip\b', r'\bbdrip\b']
    for pat in qual_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            quality = m.group(0).upper()
            break
    if not quality and resolution:
        quality = resolution

    # Video Codec
    video_codec = ""
    vc_patterns = [r'\bx265\b', r'\bx264\b', r'\bhevc\b', r'\bh265\b', r'\bh264\b', r'\bavc\b', r'\b10bit\b', r'\b8bit\b']
    for pat in vc_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            video_codec = m.group(0).upper()
            break

    # Audio Codec
    audio_codec = ""
    ac_patterns = [r'\baac\b', r'\bddp5\.1\b', r'\bdd5\.1\b', r'\bddp2\.0\b', r'\bac3\b', r'\bopus\b', r'\bdts\b', r'\bflac\b', r'\btruehd\b', r'\batmos\b']
    for pat in ac_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            audio_codec = m.group(0).upper()
            break

    # Languages
    languages = []
    lang_map = {
        'hindi': 'Hindi', 'english': 'English', 'tamil': 'Tamil', 'telugu': 'Telugu',
        'bengali': 'Bengali', 'malayalam': 'Malayalam', 'kannada': 'Kannada',
        'marathi': 'Marathi', 'punjabi': 'Punjabi', 'gujarati': 'Gujarati',
        'japanese': 'Japanese', 'multi': 'Multi Audio', 'dual': 'Dual Audio'
    }
    for keyword, display in lang_map.items():
        if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
            languages.append(display)
    if not languages:
        if re.search(r'\b(esub|sub|subbed|engsub)\b', text, re.IGNORECASE):
            languages.append("Subbed")

    # Source
    source = ""
    src_patterns = [r'\bnetflix\b', r'\bnf\b', r'\bcrunchyroll\b', r'\bcr\b', r'\bamzn\b', r'\bamazon\b', r'\bdsnp\b', r'\bdisney\b', r'\bhmax\b', r'\bhbomax\b']
    for pat in src_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            source = m.group(0).upper()
            break

    # Season and Episode
    season = None
    episode = None

    # Check for S01E01 style
    s_e_match = re.search(r'\bs(\d+)[\s_.-]*e(\d+)\b', text, re.IGNORECASE)
    if s_e_match:
        season = int(s_e_match.group(1))
        episode = int(s_e_match.group(2))
    else:
        # Check for Season 1 Episode 1 style
        season_match = re.search(r'\b(?:season|s)[\s_.-]*(\d+)\b', text, re.IGNORECASE)
        if season_match:
            season = int(season_match.group(1))

        ep_match = re.search(r'\b(?:episode|ep|e|part|pt)[\s_.-]*(\d+)\b', text, re.IGNORECASE)
        if ep_match:
            episode = int(ep_match.group(1))
        else:
            # Match a hyphen followed by number, e.g. "Bleach - 12 [720p]"
            # But avoid years or resolutions
            raw_ep = re.search(r'\s-\s*(\d+)\b', text)
            if raw_ep:
                val = int(raw_ep.group(1))
                if val < 1000: # unlikely to be an episode if 1000+
                    episode = val

    # Clean Title extraction
    # Start with the first non-empty string among filename/caption
    base_text = ""
    if filename:
        # Strip extension
        base_text = filename.rsplit('.', 1)[0]
    else:
        # Get first line of caption
        lines = [l.strip() for l in caption.split('\n') if l.strip()]
        base_text = lines[0] if lines else "Unknown Title"

    cleaned = base_text
    # Remove anything inside brackets/parentheses
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    cleaned = re.sub(r'\([^\)]*\)', '', cleaned)

    # Strip season, episode, special indicators and everything that follows
    cleaned = re.sub(r'\bs\d+e\d+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:season|s|episode|ep|e|part|pt|ova|ona|special|extra|ncop|nced|movie)[\s_.-]*\d+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:season|s|episode|ep|e|part|pt|ova|ona|special|extra|ncop|nced|movie)\b.*$', '', cleaned, flags=re.IGNORECASE)

    # Strip metadata keywords
    keywords_to_remove = [
        'x265', 'x264', 'hevc', 'h265', 'h264', 'avc', '10bit', '8bit',
        '2160p', '1080p', '720p', '480p', '360p', '540p', '4k', '8k', 'uhd', 'fhd', 'hd', 'sd',
        'web-dl', 'webrip', 'bluray', 'hdtv', 'brrip', 'dvdrip', 'bdrip',
        'multi', 'dual', 'audio', 'esub', 'sub', 'dub', 'dubbed',
        'ova', 'ona', 'special', 'extra', 'ncop', 'nced', 'movie', 'show',
        'hindi', 'english', 'tamil', 'telugu', 'bengali', 'malayalam', 'kannada', 'marathi', 'punjabi', 'gujarati', 'japanese',
        'aac', 'ac3', 'ddp', 'truehd', 'atmos', 'opus', 'flac', 'dd', 'dts'
    ]
    for keyword in keywords_to_remove:
        cleaned = re.sub(rf'\b{keyword}\b', '', cleaned, flags=re.IGNORECASE)

    # Replace punctuation/dots/underscores with space
    cleaned = re.sub(r'[^\w\s-]', ' ', cleaned)
    cleaned = cleaned.replace('_', ' ').replace('-', ' ').replace('.', ' ')

    # Remove numbers that look like years (1900-2099)
    cleaned = re.sub(r'\b(19\d{2}|20\d{2})\b', '', cleaned)

    # Final whitespace normalization
    cleaned = " ".join(cleaned.split()).strip()

    if not cleaned:
        cleaned = "Unknown Title"

    return {
        'title': cleaned.title(),
        'season': season,
        'episode': episode,
        'resolution': resolution,
        'quality': quality,
        'languages': languages,
        'video_codec': video_codec,
        'audio_codec': audio_codec,
        'source': source,
        'movie': movie,
        'ova': ova,
        'ona': ona,
        'special': special,
        'extra': extra,
        'ncop': ncop,
        'nced': nced,
        'extension': ext
    }

async def create_indexes_safe(coll):
    try:
        await coll.create_index("unique_file_id", unique=True)
    except Exception as e:
        print(f"[INDEX ERROR] unique_file_id: {e}")
    try:
        await coll.create_index("file_id")
    except Exception as e:
        print(f"[INDEX ERROR] file_id: {e}")
    try:
        await coll.create_index("title")
    except Exception as e:
        print(f"[INDEX ERROR] title: {e}")
    try:
        await coll.create_index("title_normalized")
    except Exception as e:
        print(f"[INDEX ERROR] title_normalized: {e}")

async def get_collected_collection(bot_username):
    uname = bot_username.lower().replace("@", "").strip()
    coll = db.database[f"collected_{uname}"]
    # Create indexes asynchronously in background to ensure lightning speed and robustness
    asyncio.create_task(create_indexes_safe(coll))
    return coll

def format_eta(seconds):
    if seconds < 0:
        return "0s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

def get_quality_display(doc):
    res = doc.get('resolution') or ""
    vc = doc.get('video_codec') or ""
    if "X265" in vc or "HEVC" in vc or "10BIT" in vc:
        vc_clean = "HEVC"
    elif "X264" in vc or "AVC" in vc:
        vc_clean = "AVC"
    else:
        vc_clean = vc

    parts = []
    if res:
        parts.append(res)
    if vc_clean:
        parts.append(vc_clean)

    return " ".join(parts) if parts else "UNKNOWN"

def ensure_underscore_wrapping(url: str) -> str:
    if not url or not url.startswith("http"):
        return url
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.strip('/')
    if path and not (path.startswith("___") and path.endswith("___")):
        if '/' not in path:
            return f"{parsed.scheme}://{parsed.netloc}/___{path}___"
    return url

# ---------------- COMMANDS ----------------

@Client.on_message(filters.private & admin & filters.command('collect'))
async def collect_command(client: Client, message: Message):
    bot_username = client.username
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ <b>Missing range!</b>\n\n"
            "Usage:\n"
            "<code>/collect https://t.me/c/3929301787/691-https://t.me/c/3929301787/695</code>\n"
            "or\n"
            "<code>/collect 691-695</code>"
        )

    range_text = message.text.split(None, 1)[1].strip()
    parts = range_text.split("-")
    if len(parts) != 2:
        return await message.reply_text("❌ <b>Invalid range format! Use Start-End with a hyphen.</b>")

    start_str = parts[0].strip()
    end_str = parts[1].strip()

    # Resolve CID and Start/End IDs
    link_pattern = r"t\.me\/(?:c\/)?([a-zA-Z0-9_-]+)\/(\d+)"
    m_start = re.search(link_pattern, start_str)
    m_end = re.search(link_pattern, end_str)

    cid = None
    start_id = None
    end_id = None

    if m_start and m_end:
        ch_start = m_start.group(1)
        ch_end = m_end.group(1)
        if ch_start != ch_end:
            return await message.reply_text("❌ <b>Channel mismatch in message links!</b>")

        if "t.me/c/" in start_str:
            cid_str = ch_start
            if cid_str.isdigit():
                cid = int("-100" + cid_str)
            else:
                cid = cid_str
        else:
            cid = ch_start

        start_id = int(m_start.group(2))
        end_id = int(m_end.group(2))
    elif start_str.isdigit() and end_str.isdigit():
        db_channels = await db.get_all_db_channels(bot_username)
        if not db_channels:
            if hasattr(client, 'db_channel_id') and client.db_channel_id:
                db_channels = [client.db_channel_id]
            elif hasattr(client, 'db_channel') and client.db_channel:
                db_channels = [client.db_channel.id]

        if not db_channels:
            return await message.reply_text("❌ <b>No configured DB channels found! Please add one first.</b>")

        cid = db_channels[0]
        start_id = int(start_str)
        end_id = int(end_str)
    else:
        return await message.reply_text("❌ <b>Invalid message range or links format!</b>")

    if start_id > end_id:
        return await message.reply_text("❌ <b>Start ID must be less than or equal to End ID!</b>")

    status_msg = await message.reply_text("<b>⏳ Initializing collection...</b>")

    settings = await db.get_settings(bot_username=bot_username)
    session_str = settings.get('session_string')
    session_client = None
    if session_str:
        try:
            from plugins.start import get_session_client
            session_client = await get_session_client(session_str)
        except Exception as e:
            print(f"[COLLECT] Error fetching session client: {e}")

    coll = await get_collected_collection(bot_username)

    start_time = time.time()
    added_count = 0
    skipped_count = 0
    duplicate_count = 0
    processed_count = 0
    total_count = end_id - start_id + 1
    last_edit_time = 0

    all_mids = list(range(start_id, end_id + 1))

    # Update progress status message immediately to give instant feedback
    await status_msg.edit_text(
        "<b>Collecting...</b>\n\n"
        f"<b>Current:</b> 0 / {total_count}\n"
        f"<b>Stored:</b> 0\n"
        f"<b>Skipped:</b> 0\n"
        f"<b>Duplicates:</b> 0\n"
        "<b>ETA:</b> Calculating..."
    )

    # Process in chunks of 50 message IDs at a time with a careful delay to prevent rate limits/freezing
    for i in range(0, len(all_mids), 50):
        chunk_ids = all_mids[i:i+50]
        try:
            # Batch fetch messages using session client (if configured) for maximum private channel access
            msgs = await get_messages(session_client or client, chunk_ids, chat_id=cid)
            msg_map = {m.id: m for m in msgs if m and not m.empty}

            for mid in chunk_ids:
                processed_count += 1
                m = msg_map.get(mid)

                if not m:
                    skipped_count += 1
                    continue

                media = m.document or m.video or m.audio or m.animation
                if not media:
                    skipped_count += 1
                    continue

                unique_file_id = getattr(media, 'file_unique_id', None)
                file_id = getattr(media, 'file_id', None)
                if not unique_file_id or not file_id:
                    skipped_count += 1
                    continue

                # Duplicate Detection
                existing = await coll.find_one({'unique_file_id': unique_file_id})
                if existing:
                    duplicate_count += 1
                    continue

                filename = get_filename(m) or getattr(media, 'file_name', None) or ""
                caption = m.caption or ""
                meta = extract_metadata(filename, caption)

                doc = {
                    'title': meta['title'],
                    'title_normalized': re.sub(r'[\s_.-]', '', meta['title'].lower()),
                    'season': meta['season'],
                    'episode': meta['episode'],
                    'resolution': meta['resolution'],
                    'quality': meta['quality'],
                    'languages': meta['languages'],
                    'video_codec': meta['video_codec'],
                    'audio_codec': meta['audio_codec'],
                    'source': meta['source'],
                    'movie': meta['movie'],
                    'ova': meta['ova'],
                    'ona': meta['ona'],
                    'special': meta['special'],
                    'extra': meta['extra'],
                    'ncop': meta['ncop'],
                    'nced': meta['nced'],
                    'extension': meta['extension'],
                    'file_name': filename,
                    'caption': caption,
                    'file_id': file_id,
                    'unique_file_id': unique_file_id,
                    'file_size': getattr(media, 'file_size', 0),
                    'message_id': m.id,
                    'cid': cid,
                    'created_at': time.time()
                }
                await coll.insert_one(doc)
                added_count += 1

        except Exception as batch_err:
            print(f"[COLLECT BATCH ERROR] {batch_err}")
            skipped_count += len(chunk_ids)
            processed_count += len(chunk_ids)

        # Non-blocking safe pause between chunk iterations to ensure bot never gets stuck
        await asyncio.sleep(1.0)

        # Periodic progress update (avoid hitting Rate Limits on edits)
        now = time.time()
        if now - last_edit_time >= 4 or processed_count >= total_count:
            last_edit_time = now
            elapsed = now - start_time
            avg_time = elapsed / processed_count if processed_count > 0 else 0
            remaining_msgs = total_count - processed_count
            text_eta_secs = avg_time * remaining_msgs
            eta_str = format_eta(text_eta_secs)

            progress_text = (
                "<b>Collecting...</b>\n\n"
                f"<b>Current:</b> {processed_count} / {total_count}\n"
                f"<b>Stored:</b> {added_count}\n"
                f"<b>Skipped:</b> {skipped_count}\n"
                f"<b>Duplicates:</b> {duplicate_count}\n"
                f"<b>ETA:</b> {eta_str}"
            )
            try:
                await status_msg.edit_text(progress_text)
            except MessageNotModified:
                pass
            except Exception as edit_err:
                print(f"[PROGRESS EDIT ERROR] {edit_err}")

    # Complete
    complete_text = (
        "<b>✅ Collection Completed!</b>\n\n"
        f"• <b>Total Messages Processed:</b> {processed_count}\n"
        f"• <b>Successfully Stored:</b> {added_count}\n"
        f"• <b>Skipped (Non-media/Errors):</b> {skipped_count}\n"
        f"• <b>Duplicates Ignored:</b> {duplicate_count}"
    )
    try:
        await status_msg.edit_text(complete_text)
    except Exception as e:
        print(f"Error editing final collection status: {e}")


@Client.on_message(filters.private & filters.command('search'))
async def search_command(client: Client, message: Message):
    bot_username = client.username
    user_id = message.from_user.id

    is_premium = await is_premium_user(user_id)
    is_admin = await db.admin_exist(user_id) or user_id == OWNER_ID
    settings = await db.get_settings(bot_username=bot_username)

    # Verification Checking
    if not is_premium and not is_admin and settings.get('shortener_active', True):
        verified = await db.is_user_verified(user_id, bot_username=bot_username)
        if not verified:
            session_id, mask_token = await db.create_verification_session(
                user_id, "verify_general", bot_username=bot_username
            )
            web_url = (settings.get('api_url') or settings.get('website_url', WEBSITE_URL)).rstrip('/')
            protected_redirect = f"{web_url}/verify/{session_id}"

            shortener_cfg = settings.get('shortener', {})
            final_redirect = protected_redirect
            original_shortlink = protected_redirect
            if shortener_cfg and shortener_cfg.get('enabled') and shortener_cfg.get('domain') and shortener_cfg.get('api_key_encrypted'):
                from protect import get_short_link
                try:
                    shortened = await get_short_link(
                        f"{web_url}/track/{session_id}",
                        alias=mask_token,
                        shortener_url=shortener_cfg['domain'],
                        api_key=shortener_cfg['api_key_encrypted']
                    )
                    if shortened and shortened.startswith("http"):
                        original_shortlink = ensure_underscore_wrapping(shortened)
                        final_redirect = original_shortlink
                        await db.sessions.update_one(
                            {"session_id": session_id},
                            {"$set": {"original_shortlink": original_shortlink, "traced_url": original_shortlink}}
                        )
                except Exception as e:
                    print(f"Error shortening URL in search: {e}")

            buttons = [
                [InlineKeyboardButton("✅ Verify Now", web_app=WebAppInfo(url=final_redirect), style="primary")]
            ]
            tut_link = settings.get("tutorial_link", TUT_VID)
            tut_enabled = settings.get("tutorial_enabled", True)
            if tut_enabled and tut_link:
                buttons.append([InlineKeyboardButton("📹 Tutorial", url=tut_link, style="primary")])

            buttons.append([
                InlineKeyboardButton(
                    "✅ I Have Verified",
                    url=f"https://t.me/{bot_username}?start=verify_{session_id}",
                    style="success"
                )
            ])

            validity_secs = settings.get('verify_window', 86400)
            validity_text = get_exp_time(validity_secs)
            access_limit = settings.get('access_limit', 1)
            access_text = "Unlimited" if access_limit == -1 else f"{access_limit} accesses"

            heading = RichText.format_heading("Verification Required", level=1)
            body = "🔐 <b>Verification is required before searching files.</b>\n\nComplete verification to continue."
            blockquote_content = (
                f"◈ Search System Access\n"
                f"◈ Expiry Duration: <b>{validity_text}</b>\n"
                f"◈ Access Limit: <b>{access_text}</b>"
            )
            quote = RichText.format_quote(blockquote_content, expandable=True)
            caption = f"{heading}\n\n{body}\n\n{quote}"

            is_legacy = False
            try:
                user_doc = await db.user_data.find_one({"_id": user_id})
                if user_doc and user_doc.get("legacy_client") is True:
                    is_legacy = True
            except: pass

            caption = RichText.clean_unsupported(caption, is_legacy=is_legacy)
            return await message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    if len(message.command) < 2:
        return await message.reply_text(
            "🔍 <b>Search System</b>\n\n"
            "Usage: <code>/search &lt;query&gt;</code>\n"
            "Example: <code>/search naruto</code>"
        )

    query_text = message.text.split(None, 1)[1].strip()
    query_norm = re.sub(r'[\s_.-]', '', query_text.lower())

    coll = await get_collected_collection(bot_username)
    docs = await coll.find({
        '$or': [
            {'title_normalized': {'$regex': query_norm, '$options': 'i'}},
            {'file_name': {'$regex': query_text, '$options': 'i'}},
            {'caption': {'$regex': query_text, '$options': 'i'}}
        ]
    }).to_list(length=None)

    if not docs:
        return await message.reply_text("❌ <b>No matching files found in your bot's database!</b>")

    matching_titles = sorted(list(set(d['title'] for d in docs)))

    # Save Search Session
    SEARCH_SESSIONS[user_id] = {
        'bot_username': bot_username,
        'matching_titles': matching_titles,
        'all_docs': docs
    }

    # If only one title matches, automatically continue to the next step
    if len(matching_titles) == 1:
        dummy_query = CallbackQuery(
            id="dummy",
            from_user=message.from_user,
            message=message,
            data=f"sc:{user_id}:title:0",
            client=client
        )
        return await select_title_handler(client, dummy_query, 0, user_id)

    # Display titles as inline buttons
    buttons = []
    for idx, title in enumerate(matching_titles[:20]): # Limit to top 20 titles for UI size
        buttons.append([InlineKeyboardButton(title, callback_data=f"sc:{user_id}:title:{idx}")])

    await message.reply_text(
        "🔍 <b>Select matching title:</b>",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ---------------- AUTOMATIC COLLECTION ----------------

@Client.on_message(filters.channel)
async def auto_collect_channel_post(client: Client, message: Message):
    bot_username = client.username
    cid = message.chat.id

    db_channels = await db.get_all_db_channels(bot_username)
    if not db_channels:
        if hasattr(client, 'db_channel_id') and client.db_channel_id:
            db_channels = [client.db_channel_id]
        elif hasattr(client, 'db_channel') and client.db_channel:
            db_channels = [client.db_channel.id]

    if cid not in db_channels:
        return

    media = message.document or message.video or message.audio or message.animation
    if not media:
        return

    filename = get_filename(message) or getattr(media, 'file_name', None) or ""
    caption = message.caption or ""

    unique_file_id = getattr(media, 'file_unique_id', None)
    file_id = getattr(media, 'file_id', None)
    if not unique_file_id or not file_id:
        return

    coll = await get_collected_collection(bot_username)
    meta = extract_metadata(filename, caption)

    doc = {
        'title': meta['title'],
        'title_normalized': re.sub(r'[\s_.-]', '', meta['title'].lower()),
        'season': meta['season'],
        'episode': meta['episode'],
        'resolution': meta['resolution'],
        'quality': meta['quality'],
        'languages': meta['languages'],
        'video_codec': meta['video_codec'],
        'audio_codec': meta['audio_codec'],
        'source': meta['source'],
        'movie': meta['movie'],
        'ova': meta['ova'],
        'ona': meta['ona'],
        'special': meta['special'],
        'extra': meta['extra'],
        'ncop': meta['ncop'],
        'nced': meta['nced'],
        'extension': meta['extension'],
        'file_name': filename,
        'caption': caption,
        'file_id': file_id,
        'unique_file_id': unique_file_id,
        'file_size': getattr(media, 'file_size', 0),
        'message_id': message.id,
        'cid': cid,
        'created_at': time.time()
    }

    try:
        await coll.update_one(
            {'unique_file_id': unique_file_id},
            {'$set': doc},
            upsert=True
        )
        print(f"[AUTO COLLECT] Indexed {filename} from channel {cid}")
    except Exception as e:
        print(f"[AUTO COLLECT ERROR] {e}")


# ---------------- CALLBACK QUERY HANDLERS ----------------

@Client.on_callback_query(filters.regex(r"^sc:"))
async def handle_search_callbacks(client: Client, query: CallbackQuery):
    data = query.data
    parts = data.split(":")
    owner_id = int(parts[1])

    # Strictly check that the callback belongs to the user who initiated the search
    if query.from_user.id != owner_id:
        return await query.answer("❌ This menu belongs to another user.", show_alert=True)

    session = SEARCH_SESSIONS.get(owner_id)
    if not session:
        return await query.answer("⚠️ Session expired! Please search again using /search.", show_alert=True)

    action = parts[2]

    # 1. Title Selection
    if action == "title":
        idx = int(parts[3])
        await select_title_handler(client, query, idx, owner_id)

    # 2. Quality Selection
    elif action == "qual":
        idx = int(parts[3])
        quality = session['matching_qualities'][idx]
        await deliver_files_by_quality(client, query, quality, owner_id)

    # 3. Static Page Label or Dummy Clicks
    elif action == "nop":
        await query.answer()

    # 4. Back Button Logic
    elif action == "back":
        step = parts[3]
        if step == "title":
            # Go back to title selection
            buttons = []
            for idx, title in enumerate(session['matching_titles'][:20]):
                buttons.append([InlineKeyboardButton(title, callback_data=f"sc:{owner_id}:title:{idx}")])
            await query.message.edit_text(
                "🔍 <b>Select matching title:</b>",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await query.answer()

async def select_title_handler(client, query, idx, owner_id):
    session = SEARCH_SESSIONS.get(owner_id)
    title = session['matching_titles'][idx]
    session['title'] = title

    docs_title = [d for d in session['all_docs'] if d['title'] == title]
    session['docs_title'] = docs_title

    # Extract available qualities for this title
    qualities = sorted(list(set(get_quality_display(d) for d in docs_title)))
    session['matching_qualities'] = qualities

    # If only one quality exists, automatically send all files for that title directly
    if len(qualities) <= 1:
        quality_to_send = qualities[0] if qualities else "UNKNOWN"
        if query.id != "dummy":
            await query.message.delete()
        await deliver_files_by_quality_internal(client, query.message, quality_to_send, owner_id)
        await query.answer("Files delivered!")
    else:
        # Display available qualities as inline buttons
        buttons = []
        for i, q in enumerate(qualities):
            buttons.append([InlineKeyboardButton(q, callback_data=f"sc:{owner_id}:qual:{i}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"sc:{owner_id}:back:title")])

        text = (
            f"🎬 <b>Title:</b> {title}\n\n"
            f"Select Quality:"
        )
        if query.id == "dummy":
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()

async def deliver_files_by_quality(client, query, quality, owner_id):
    await query.message.delete()
    await deliver_files_by_quality_internal(client, query.message, quality, owner_id)
    await query.answer("Files delivered!")

async def deliver_files_by_quality_internal(client, message, quality, owner_id):
    session = SEARCH_SESSIONS.get(owner_id)
    if not session:
        return

    delivery_msg = await message.reply_text("📤 <b>Delivering selected files...</b>")

    docs_title = session['docs_title']
    # Filter documents by selected quality
    to_deliver = [d for d in docs_title if get_quality_display(d) == quality]

    # Maintain original sorting order of items by episode, season, or file name
    to_deliver = sorted(to_deliver, key=lambda d: (d.get('season') or 0, d.get('episode') or 0, d.get('file_name', '')))

    # Deliver sequentially preserving exact copy properties
    for item in to_deliver:
        try:
            await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=item['cid'],
                message_id=item['message_id']
            )
            await asyncio.sleep(0.5) # safe pause to prevent floodwaits
        except Exception as e:
            print(f"[SEARCH DELIVERY ERROR] msg {item['message_id']}: {e}")

    await delivery_msg.delete()
    SEARCH_SESSIONS.pop(owner_id, None)
