import re
from core.message_metadata import clean_emojis_and_html

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
    text_clean = re.sub(r'\b(1080p|720p|480p|360p|2160p|4k|1080|720|480|360|2160)\b', ' ', text_clean)
    text_clean = re.sub(r'\b(19\d{2}|20\d{2})\b', ' ', text_clean) # Year
    text_clean = re.sub(r'\b(x264|x265|h264|h265|hevc|10bit|8bit|aac|ddp|mp4|mkv|avi|webm)\b', ' ', text_clean)

    return text_clean

def parse_season_episode_advanced(text):
    text_clean = clean_episode_text(text)
    season = 1
    episode = None

    # 1. Match S01E01 / S01EP01 / S01 EP 01 / S01_E01
    m_s_e = re.search(r'\bs(\d+)[\s_.-]*e(?:p(?:isode)?)?[\s_.-]*(\d+(?:\.\d+)?)\b', text_clean)
    if m_s_e:
        season = int(m_s_e.group(1))
        ep_str = m_s_e.group(2)
        episode = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, episode

    # 2. Match Season 1 Episode 1
    m_season_ep = re.search(r'\bseason[\s_.-]*(\d+)[\s_.-]*(?:episode|ep|e)[\s_.-]*(\d+(?:\.\d+)?)\b', text_clean)
    if m_season_ep:
        season = int(m_season_ep.group(1))
        ep_str = m_season_ep.group(2)
        episode = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, episode

    # 3. Match 1x01
    m_x = re.search(r'\b(\d+)x(\d+(?:\.\d+)?)\b', text_clean)
    if m_x:
        season = int(m_x.group(1))
        ep_str = m_x.group(2)
        episode = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, episode

    # 4. Standalone Season
    m_s_standalone = re.search(r'\b(?:season|s)[\s_.-]*(\d+)\b', text_clean)
    if m_s_standalone:
        season = int(m_s_standalone.group(1))

    # 5. Standalone Episode
    m_ep = re.search(r'\b(?:episode|ep|e|part|pt)[\s_.-]*(\d+(?:\.\d+)?)\b', text_clean)
    if m_ep:
        ep_str = m_ep.group(1)
        episode = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, episode

    # 6. Check for split/multi-part patterns: part001, pt1, .001.ext as episode numbers
    m_part_split = re.search(r'\b(?:part|pt)[\s_.-]*(\d+)\b', text_clean)
    if m_part_split:
        return season, int(m_part_split.group(1))

    # Fallback to check raw split format like .001
    m_dot_split = re.search(r'\.(\d{3})\.[a-z0-9]{3,4}$', text_clean)
    if m_dot_split:
        return season, int(m_dot_split.group(1))

    # 7. Check for "01", "01v2", "01.5"
    m_v2 = re.search(r'\b(\d+(?:\.\d+)?)v[1-9]\b', text_clean)
    if m_v2:
        ep_str = m_v2.group(1)
        episode = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, episode

    # 8. Check for Special string markers: OVA, ONA, Movie, Special, NCOP, NCED
    for marker in ["ova", "ona", "movie", "special", "ncop", "nced"]:
        if re.search(rf'\b{marker}\b', text_clean):
            return season, marker.upper()

    # 9. Fallback standalone digit
    m_num = re.search(r'\b(\d+(?:\.\d+)?)\b', text_clean)
    if m_num:
        ep_str = m_num.group(1)
        episode = float(ep_str) if '.' in ep_str else int(ep_str)
        return season, episode

    return season, None

def detect_episode(caption, filename):
    """
    Detects episode and season from a message's caption and filename.
    Prioritizes caption first. Falls back to filename if caption lacks the required information.
    """
    # 1. Caption
    if caption and caption != "N/A":
        caption_clean = clean_emojis_and_html(caption)
        season, ep = parse_season_episode_advanced(caption_clean)
        if ep is not None:
            return season, ep

    # 2. Filename
    if filename:
        filename_clean = clean_emojis_and_html(filename)
        season, ep = parse_season_episode_advanced(filename_clean)
        if ep is not None:
            return season, ep

    return 1, None
