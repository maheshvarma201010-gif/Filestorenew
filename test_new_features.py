import unittest
import sys
import os
import time
import re
from bs4 import BeautifulSoup

# Ensure current folder is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.formatter import RichText, check_client_compatibility
from utils.carousel import get_input_media
from helper_func import FSUB_CACHE
from plugins.hyperlink import HYPERLINK_SESSIONS

# Import core infrastructure
from core.telegram_parser import parse_telegram_link, normalize_telegram_url
from core.range_parser import parse_range_token, parse_mixed_inputs
from core.message_metadata import get_message_metadata, determine_filename, determine_caption
from core.episode_detector import detect_episode, parse_season_episode_advanced, clean_episode_text, parse_metadata_universal
from core.batch_generator import generate_final_link, generate_list_link
from plugins.auto_batch import detect_quality

class TestQualityDetector(unittest.TestCase):
    def test_detect_quality_patterns(self):
        # Test 480px264 pattern
        text = "Demon Slayer Kimetsu no Yaiba [S01] [480px264] [Multi Audio]Esub.mkv"
        res = detect_quality(text)
        self.assertEqual(res, "480P")

        # Test standard 1080p pattern
        text2 = "Naruto Shippuden S01E01 1080p HEVC x265"
        res2 = detect_quality(text2)
        self.assertEqual(res2, "1080P")

        # Test 720px264 pattern
        text3 = "Solo Leveling S01E12 720px264"
        res3 = detect_quality(text3)
        self.assertEqual(res3, "720P")

class TestCoreTelegramParser(unittest.TestCase):
    def test_parse_public_links(self):
        # Public channel link
        res = parse_telegram_link("https://t.me/mychannel/12345")
        self.assertEqual(res, ("mychannel", 12345))

        # Public telegram.me link
        res2 = parse_telegram_link("http://telegram.me/some_channel/9876")
        self.assertEqual(res2, ("some_channel", 9876))

        # Public telegram.dog link
        res3 = parse_telegram_link("https://telegram.dog/another_chan/112")
        self.assertEqual(res3, ("another_chan", 112))

    def test_parse_private_links(self):
        # Private channel link with standard prefix
        res = parse_telegram_link("https://t.me/c/4446716010/37150")
        self.assertEqual(res, (-1004446716010, 37150))

        # Private channel link without -100 prefix in URL (should automatically append internally)
        res2 = parse_telegram_link("https://t.me/c/123456789/55")
        self.assertEqual(res2, (-100123456789, 55))

    def test_normalize_telegram_url(self):
        # Numeric private channel ID
        url = normalize_telegram_url(-100123456789, 55)
        self.assertEqual(url, "https://t.me/c/123456789/55")

        # Public channel ID
        url2 = normalize_telegram_url("mychannel", 12345)
        self.assertEqual(url2, "https://t.me/mychannel/12345")

class TestCoreRangeParser(unittest.TestCase):
    def test_parse_single_tokens(self):
        # Single URL
        res = parse_range_token("https://t.me/mychannel/123")
        self.assertEqual(res['type'], 'single')
        self.assertEqual(res['channel'], 'mychannel')
        self.assertEqual(res['start_id'], 123)

        # Full URL Range
        res = parse_range_token("https://t.me/c/12345/10-https://t.me/c/12345/20")
        self.assertEqual(res['type'], 'range')
        self.assertEqual(res['channel'], -10012345)
        self.assertEqual(res['start_id'], 10)
        self.assertEqual(res['end_id'], 20)

        # Short URL-ID Range
        res = parse_range_token("https://t.me/mychannel/10-20")
        self.assertEqual(res['type'], 'range')
        self.assertEqual(res['channel'], 'mychannel')
        self.assertEqual(res['start_id'], 10)
        self.assertEqual(res['end_id'], 20)

        # Raw IDs Range
        res = parse_range_token("100-200")
        self.assertEqual(res['type'], 'range')
        self.assertEqual(res['channel'], None)
        self.assertEqual(res['start_id'], 100)
        self.assertEqual(res['end_id'], 200)

    def test_parse_mixed_inputs(self):
        text = """
        https://t.me/mychannel/123
        https://t.me/mychannel/200-https://t.me/mychannel/300
        https://t.me/c/12345/500-600
        700-800
        """
        parsed = parse_mixed_inputs(text)
        self.assertEqual(len(parsed), 4)
        self.assertEqual(parsed[0]['type'], 'single')
        self.assertEqual(parsed[1]['type'], 'range')
        self.assertEqual(parsed[2]['type'], 'range')
        self.assertEqual(parsed[3]['type'], 'range')

class DummyMessage:
    def __init__(self, text=None, caption=None, document=None, video=None, photo=None):
        self.text = text
        self.caption = caption
        self.document = document
        self.video = video
        self.photo = photo
        self.audio = None
        self.animation = None
        self.empty = False

class DummyFile:
    def __init__(self, file_id, file_name=None):
        self.file_id = file_id
        self.file_name = file_name

class TestMessageMetadata(unittest.TestCase):
    def test_determine_filename_caption_priority(self):
        # Priority 1: File caption
        msg = DummyMessage(caption="My Custom Caption Name.mkv", video=DummyFile("vid_id", "ignored.mp4"))
        fn = determine_filename(msg)
        self.assertEqual(fn, "My Custom Caption Name.mkv")

        # Priority 2: Telegram document/video filename
        msg2 = DummyMessage(video=DummyFile("vid_id", "my_video_file.mp4"))
        fn2 = determine_filename(msg2)
        self.assertEqual(fn2, "my_video_file.mp4")

        # Priority 3: Fallback
        msg3 = DummyMessage()
        fn3 = determine_filename(msg3)
        self.assertEqual(fn3, "File")

    def test_determine_caption(self):
        msg = DummyMessage(caption="Complete original file caption")
        cap = determine_caption(msg)
        self.assertEqual(cap, "Complete original file caption")

        msg2 = DummyMessage()
        cap2 = determine_caption(msg2)
        self.assertEqual(cap2, "N/A")

class TestEpisodeDetector(unittest.TestCase):
    def test_clean_episode_text(self):
        raw = "Naruto_Shippuden-S01E05,1080p.mkv"
        cleaned = clean_episode_text(raw)
        self.assertIn("naruto", cleaned)
        self.assertNotIn("_", cleaned)
        self.assertNotIn("-", cleaned)
        self.assertNotIn(",", cleaned)
        self.assertNotIn("1080p", cleaned)

    def test_parse_season_episode_advanced(self):
        # S01E05
        s, e = parse_season_episode_advanced("Naruto Shippuden S01E05")
        self.assertEqual(s, 1)
        self.assertEqual(e, 5)

        # EP01 / E1
        s2, e2 = parse_season_episode_advanced("Naruto EP01")
        self.assertEqual(s2, 1)
        self.assertEqual(e2, 1)

        # Part naming / Split001
        s3, e3 = parse_season_episode_advanced("Marriagetoxin S02 pt3")
        self.assertEqual(s3, 2)
        self.assertEqual(e3, 3)

class TestRichTextFormatter(unittest.TestCase):
    def test_format_heading(self):
        h1 = RichText.format_heading("Welcome", level=1)
        self.assertEqual(h1, "<b>👑 WELCOME 👑</b>")

        h2 = RichText.format_heading("Info", level=2)
        self.assertEqual(h2, "<b>✨ Info ✨</b>")

        h3 = RichText.format_heading("Item", level=3)
        self.assertEqual(h3, "<b>• Item</b>")

    def test_format_quote(self):
        q1 = RichText.format_quote("Hello World")
        self.assertEqual(q1, "<blockquote>Hello World</blockquote>")

        q2 = RichText.format_quote("Hello World", expandable=True)
        self.assertEqual(q2, "<blockquote expandable>Hello World</blockquote>")

    def test_format_table(self):
        headers = ["ID", "Name"]
        rows = [[1, "Alice"], [2, "Bob"]]
        table = RichText.format_table(headers, rows)
        self.assertIn("Alice", table)
        self.assertIn("Bob", table)
        self.assertIn("┌", table)
        self.assertIn("└", table)
        self.assertIn("<pre>", table)

    def test_lists(self):
        bullets = RichText.format_bullet_list(["A", "B"])
        self.assertEqual(bullets, "• A\n• B")

        numbers = RichText.format_numbered_list(["A", "B"])
        self.assertEqual(numbers, "1. A\n2. B")

        checkboxes = RichText.format_checkbox_list([
            {"checked": True, "text": "Task 1"},
            {"checked": False, "text": "Task 2"}
        ])
        self.assertEqual(checkboxes, "[x] Task 1\n[ ] Task 2")

    def test_mention_and_emoji(self):
        mention = RichText.format_mention(12345, "User")
        self.assertEqual(mention, '<a href="tg://user?id=12345">User</a>')

        emoji = RichText.format_custom_emoji("emoji_1", "fallback")
        self.assertEqual(emoji, '<tg-emoji id="emoji_1">fallback</tg-emoji>')

    def test_clean_unsupported(self):
        original = 'Hello <tg-emoji id="123">🔥</tg-emoji> <blockquote expandable>nested blockquote</blockquote>'

        # Modern client (legacy=False)
        cleaned_modern = RichText.clean_unsupported(original, is_legacy=False)
        self.assertIn("tg-emoji", cleaned_modern)
        self.assertIn("blockquote", cleaned_modern)
        self.assertIn("expandable", cleaned_modern)

        # Legacy client (legacy=True)
        cleaned_legacy = RichText.clean_unsupported(original, is_legacy=True)
        self.assertNotIn("tg-emoji", cleaned_legacy)
        self.assertNotIn("expandable", cleaned_legacy)
        self.assertIn("🔥", cleaned_legacy)
        self.assertIn("<blockquote>", cleaned_legacy)

class TestCarousel(unittest.TestCase):
    def test_get_input_media(self):
        msg_photo = DummyMessage(photo=DummyFile("photo_id"))
        media_photo = get_input_media(msg_photo, "My Caption")
        self.assertIsNotNone(media_photo)
        self.assertEqual(media_photo.media, "photo_id")
        self.assertEqual(media_photo.caption, "My Caption")

        msg_video = DummyMessage(video=DummyFile("video_id"))
        media_video = get_input_media(msg_video, "Video Caption")
        self.assertIsNotNone(media_video)
        self.assertEqual(media_video.media, "video_id")

class TestUniversalMetadataDetector(unittest.TestCase):
    def test_parse_metadata_universal(self):
        # Test Episode 01 / E01 / S01E01
        s1, ep1, t1 = parse_metadata_universal("Naruto Shippuden Episode 01 1080p 2024")
        self.assertEqual((s1, ep1, t1), (1, 1, 'episode'))

        s2, ep2, t2 = parse_metadata_universal("Solo Leveling S02E12 720p x264")
        self.assertEqual((s2, ep2, t2), (2, 12, 'episode'))

        # Test Part 001 / Part01 / P001
        s3, ep3, t3 = parse_metadata_universal("Anime Name Part001 480p")
        self.assertEqual((s3, ep3, t3), (1, 1, 'part'))

        s4, ep4, t4 = parse_metadata_universal("Anime Name Part 025 1080p")
        self.assertEqual((s4, ep4, t4), (1, 25, 'part'))

        # Test Season Only
        s5, ep5, t5 = parse_metadata_universal("Anime Name Season 02 480p")
        self.assertEqual((s5, ep5, t5), (2, None, 'season_only'))

class TestIdDecoder(unittest.TestCase):
    def test_get_real_id_multiplied_and_raw(self):
        db_channels = [-1003748914288]
        CHANNEL_ID = -1003748914288

        def get_real_id(val):
            if not val or val == 0:
                return None, None
            for cid in db_channels:
                if cid and val % abs(cid) == 0:
                    return val // abs(cid), cid

            default_cid = None
            if db_channels:
                default_cid = db_channels[0]
            elif CHANNEL_ID:
                default_cid = CHANNEL_ID

            if default_cid and val % abs(default_cid) == 0:
                return val // abs(default_cid), default_cid

            return val, default_cid

        # Test 1: Multiplied ID
        raw_msg_id = 37150
        channel_id = -1003748914288
        converted_val = raw_msg_id * abs(channel_id)
        msg_id, cid = get_real_id(converted_val)
        self.assertEqual(msg_id, 37150)
        self.assertEqual(cid, -1003748914288)

        # Test 2: Raw message ID (unmultiplied)
        raw_val = 37150
        msg_id2, cid2 = get_real_id(raw_val)
        self.assertEqual(msg_id2, 37150)
        self.assertEqual(cid2, -1003748914288)

        # Test 3: None/Zero ID
        self.assertEqual(get_real_id(0), (None, None))
        self.assertEqual(get_real_id(None), (None, None))

class TestCrossBotLinkGeneration(unittest.TestCase):
    def test_get_start_link_and_list_link_custom_bot_username(self):
        import asyncio

        class DummyClient:
            username = "main_bot"

        client = DummyClient()

        # Test start link with explicit bot_username
        link_clone = asyncio.run(generate_list_link(client, -100123456789, [10, 11, 12], bot_username="clone_bot"))
        self.assertIn("https://t.me/clone_bot?start=", link_clone)

        # Test start link fallback to client username
        link_main = asyncio.run(generate_list_link(client, -100123456789, [10, 11, 12]))
        self.assertIn("https://t.me/main_bot?start=", link_main)

class TestColorInlineKeyboardButton(unittest.TestCase):
    def test_color_button_styles_and_emoji(self):
        from helper_func import ColorInlineKeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

        btn = ColorInlineKeyboardButton("Confirm", callback_data="test", style="success", icon_custom_emoji_id="5355142851615283756")
        self.assertEqual(getattr(btn, "style", None), "success")
        self.assertEqual(getattr(btn, "icon_custom_emoji_id", None), "5355142851615283756")

        btn_primary = InlineKeyboardButton("Settings", callback_data="s", style="primary", icon_custom_emoji_id="5440389890787281213")
        self.assertEqual(getattr(btn_primary, "style", None), "primary")

        markup = InlineKeyboardMarkup([[btn]])
        self.assertEqual(getattr(markup.inline_keyboard[0][0], "style", None), "success")

class TestShortlinkFallback(unittest.TestCase):
    def test_trace_and_store_session_url_fallback(self):
        import asyncio
        from unittest.mock import patch, AsyncMock
        from web_server import trace_and_store_session_url

        token_data = {
            'session_id': 'test_sess_123',
            'shortener_url': 'https://antibypass-ijri.onrender.com',
            'shortener_api': 'sk_R1PT8X44NUQOGKS3DNnBgg'
        }
        settings = {'website_url': 'https://cdn26.pixeldrain.eu.cc'}

        class DummyRequest:
            url = type('URL', (), {'scheme': 'https', 'netloc': 'cdn26.pixeldrain.eu.cc'})()

        async def run_test():
            with patch('web_server.db.sessions.find_one', new=AsyncMock(return_value=None)), \
                 patch('web_server.get_short_link', new=AsyncMock(return_value=None)), \
                 patch('web_server.db.sessions.update_one', new=AsyncMock()) as mock_update:

                res = await trace_and_store_session_url('token_123', token_data, settings, DummyRequest())
                self.assertEqual(res, 'https://cdn26.pixeldrain.eu.cc/track/test_sess_123')
                self.assertNotIn('/st?api=', res)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
