import re
from core.message_metadata import clean_emojis_and_html

def detect_quality(text):
    if not text:
        return "UNKNOWN"
    text_upper = text.upper()
    for q in ["2160P", "1440P", "1080P", "900P", "720P", "540P", "480P", "360P"]:
        if q in text_upper:
            return q
    if "4K" in text_upper:
        return "4K"
    m_q = re.search(r'\b(\d{3,4})[pP](?:\D|$)', text)
    if m_q:
        q_val = f"{m_q.group(1)}P"
        if q_val in ["2160P", "1440P", "1080P", "900P", "720P", "540P", "480P", "360P"]:
            return q_val
    return "UNKNOWN"

def clean_episode_text(text):
    if not text:
        return ""
    # Replace underscores, dashes, commas with spaces to expose word boundaries
    text = text.replace('_', ' ').replace('-', ' ').replace(',', ' ')
    text_clean = text.lower()

    # Strip metadata keywords safely
    for word in ['duration', 'language', 'quality', 'size', 'codec', 'bitrate', 'resolution']:
        text_clean = text_clean.replace(word, ' ')

    # Strip common non-episode numbers
    text_clean = re.sub(r'\b(1080p|720p|480p|360p|2160p|1440p|4k|1080|720|480|360|2160|1440)\b', ' ', text_clean)
    text_clean = re.sub(r'\b(19\d{2}|20\d{2})\b', ' ', text_clean) # Year
    text_clean = re.sub(r'\b(x264|x265|h264|h265|hevc|10bit|8bit|aac|ddp|ac3|mp4|mkv|avi|webm)\b', ' ', text_clean)

    return text_clean

def parse_metadata_universal(text):
    """
    Universally parses (season, number, num_type) from text.
    num_type can be 'episode', 'part', 'season_only', or 'unknown'.
    """
    text_clean = clean_episode_text(text)
    season = 1

    # 1. Season detection
    m_s = re.search(r'\b(?:season|s)[\s_.-]*(\d+)\b', text_clean)
    if m_s:
        season = int(m_s.group(1))

    # 2. Check for explicit Part patterns: "Part 001", "Part001", "Part 01", "P001", "pt1"
    m_part = re.search(r'\b(?:part|pt|p)[\s_.-]*(\d+)\b', text_clean)
    if m_part:
        return season, int(m_part.group(1)), 'part'

    # 3. Match S01E01 / S01EP01 / S01 EP 01 / Episode 01 / E01
    m_s_e = re.search(r'\bs?(\d+)?[\s_.-]*e(?:p(?:isode)?)?[\s_.-]*(\d+(?:\.\d+)?)\b', text_clean)
    if m_s_e:
        if m_s_e.group(1):
            season = int(m_s_e.group(1))
        ep_str = m_s_e.group(2)
        ep = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, ep, 'episode'

    # 4. Match Season 1 Episode 1
    m_season_ep = re.search(r'\bseason[\s_.-]*(\d+)[\s_.-]*(?:episode|ep|e)[\s_.-]*(\d+(?:\.\d+)?)\b', text_clean)
    if m_season_ep:
        season = int(m_season_ep.group(1))
        ep_str = m_season_ep.group(2)
        ep = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, ep, 'episode'

    # 5. Match 1x01
    m_x = re.search(r'\b(\d+)x(\d+(?:\.\d+)?)\b', text_clean)
    if m_x:
        season = int(m_x.group(1))
        ep_str = m_x.group(2)
        ep = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, ep, 'episode'

    # 6. Check for "01", "001", "01.5"
    m_v2 = re.search(r'\b(\d+(?:\.\d+)?)v[1-9]\b', text_clean)
    if m_v2:
        ep_str = m_v2.group(1)
        ep = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, ep, 'episode'

    # 7. Fallback standalone digit (excluding season match if found)
    text_no_season = re.sub(r'\b(?:season|s)[\s_.-]*\d+\b', ' ', text_clean)
    m_num = re.search(r'\b(\d+(?:\.\d+)?)\b', text_no_season)
    if m_num:
        ep_str = m_num.group(1)
        ep = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, ep, 'episode'

    # If season was detected but no episode or part number exists
    if m_s:
        return season, None, 'season_only'

    return season, None, 'unknown'

def parse_season_episode_advanced(text):
    s, ep, _ = parse_metadata_universal(text)
    return s, ep

def detect_episode(caption, filename):
    """
    Detects episode and season from a message's caption and filename.
    Prioritizes caption first. Falls back to filename if caption lacks the required information.
    """
    # 1. Caption
    if caption and caption != "N/A":
        caption_clean = clean_emojis_and_html(caption)
        season, ep, ntype = parse_metadata_universal(caption_clean)
        if ep is not None or ntype == 'season_only':
            return season, ep

    # 2. Filename
    if filename:
        filename_clean = clean_emojis_and_html(filename)
        season, ep, ntype = parse_metadata_universal(filename_clean)
        if ep is not None or ntype == 'season_only':
            return season, ep

    return 1, None
