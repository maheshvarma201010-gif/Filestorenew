import unittest
import sys
import os
import re

# Ensure current folder is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from plugins.search_collect import extract_metadata, ensure_underscore_wrapping, get_quality_display

class TestSearchCollect(unittest.TestCase):

    def test_extract_metadata_standard(self):
        meta = extract_metadata(
            "[SomeGroup] Naruto Shippuden S01E05 1080p HEVC Dual Audio.mkv",
            "This is a great episode of Naruto!"
        )
        self.assertEqual(meta['title'], "Naruto Shippuden")
        self.assertEqual(meta['season'], 1)
        self.assertEqual(meta['episode'], 5)
        self.assertEqual(meta['resolution'], "1080P")
        self.assertEqual(meta['quality'], "1080P")
        self.assertEqual(meta['video_codec'], "HEVC")
        self.assertIn("Dual Audio", meta['languages'])
        self.assertEqual(meta['extension'], "mkv")

    def test_extract_metadata_complex_and_bracketed(self):
        meta = extract_metadata(
            "Bleach S02E15 [1080p] [HEVC 10bit] [x265] [Dual Audio] [Multi-Sub] [WEB-DL].mkv",
            ""
        )
        self.assertEqual(meta['title'], "Bleach")
        self.assertEqual(meta['season'], 2)
        self.assertEqual(meta['episode'], 15)
        self.assertEqual(meta['resolution'], "1080P")
        self.assertEqual(meta['quality'], "WEB-DL")
        self.assertEqual(meta['video_codec'], "X265")
        self.assertIn("Dual Audio", meta['languages'])

    def test_extract_metadata_movie(self):
        meta = extract_metadata(
            "Spirited Away 2001 Bluray 1080p x264 DTS.mkv",
            "An amazing Ghibli movie!"
        )
        self.assertEqual(meta['title'], "Spirited Away")
        self.assertIsNone(meta['season'])
        self.assertIsNone(meta['episode'])
        self.assertEqual(meta['quality'], "BLURAY")
        self.assertTrue(meta['movie'])

    def test_extract_metadata_flags(self):
        meta = extract_metadata(
            "Attack on Titan Special OVA 1 720p.mkv",
            "Extra content"
        )
        self.assertEqual(meta['title'], "Attack On Titan")
        self.assertTrue(meta['special'])
        self.assertTrue(meta['ova'])

    def test_ensure_underscore_wrapping(self):
        url = "https://example.com/abc123xyz"
        wrapped = ensure_underscore_wrapping(url)
        self.assertEqual(wrapped, "https://example.com/___abc123xyz___")

        already_wrapped = "https://example.com/___abc123xyz___"
        self.assertEqual(ensure_underscore_wrapping(already_wrapped), already_wrapped)

    def test_get_quality_display(self):
        doc1 = {'resolution': '1080P', 'video_codec': 'HEVC'}
        self.assertEqual(get_quality_display(doc1), "1080P HEVC")

        doc2 = {'resolution': '720P', 'video_codec': 'X264'}
        self.assertEqual(get_quality_display(doc2), "720P AVC")

        doc3 = {'resolution': '480P', 'video_codec': ''}
        self.assertEqual(get_quality_display(doc3), "480P")

    def test_pagination_logic(self):
        items = list(range(100))
        PAGE_SIZE = 15

        # Test Page 0
        start = 0 * PAGE_SIZE
        end = start + PAGE_SIZE
        chunk = items[start:end]
        self.assertEqual(len(chunk), 15)
        self.assertEqual(chunk[0], 0)
        self.assertEqual(chunk[-1], 14)

        # Test Page 6 (last page)
        start = 6 * PAGE_SIZE
        end = start + PAGE_SIZE
        chunk = items[start:end]
        self.assertEqual(len(chunk), 10)
        self.assertEqual(chunk[0], 90)
        self.assertEqual(chunk[-1], 99)

if __name__ == '__main__':
    unittest.main()
