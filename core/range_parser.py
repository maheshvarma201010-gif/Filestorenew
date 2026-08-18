import re
from core.telegram_parser import parse_telegram_link

def parse_range_token(token: str):
    """
    Parses a single token which could be a single URL, URL-URL, URL-ID, ID-URL, or ID-ID.
    Returns:
       - {'type': 'single', 'channel': chan, 'start_id': id, 'end_id': id}
       - {'type': 'range', 'channel': chan, 'start_id': id, 'end_id': id}
       - None if invalid
    """
    token = token.strip()
    if not token:
        return None

    # Remove whitespace inside token (around hyphens)
    token = re.sub(r'\s*-\s*', '-', token)

    if '-' in token:
        parts = token.split('-', 1)
        left = parts[0].strip()
        right = parts[1].strip()

        # Case 1: URL-URL
        left_parsed = parse_telegram_link(left)
        right_parsed = parse_telegram_link(right)
        if left_parsed and right_parsed:
            chan_l, id_l = left_parsed
            chan_r, id_r = right_parsed
            return {
                'type': 'range',
                'channel': chan_l,
                'start_id': id_l,
                'end_id': id_r,
                'channel_right': chan_r
            }

        # Case 2: URL-ID
        if left_parsed and right.isdigit():
            chan, id_l = left_parsed
            return {
                'type': 'range',
                'channel': chan,
                'start_id': id_l,
                'end_id': int(right)
            }

        # Case 3: ID-URL
        if left.isdigit() and right_parsed:
            chan, id_r = right_parsed
            return {
                'type': 'range',
                'channel': chan,
                'start_id': int(left),
                'end_id': id_r
            }

        # Case 4: ID-ID
        if left.isdigit() and right.isdigit():
            return {
                'type': 'range',
                'channel': None,
                'start_id': int(left),
                'end_id': int(right)
            }
    else:
        # Case 5: Single URL
        parsed = parse_telegram_link(token)
        if parsed:
            chan, msg_id = parsed
            return {
                'type': 'single',
                'channel': chan,
                'start_id': msg_id,
                'end_id': msg_id
            }
        # Case 6: Single ID
        if token.isdigit():
            return {
                'type': 'single',
                'channel': None,
                'start_id': int(token),
                'end_id': int(token)
            }

    return None

def parse_mixed_inputs(text: str):
    """
    Cleans commas, splits text by whitespaces/newlines to find all tokens,
    parses each token, and returns a list of parsed dictionaries.
    """
    if not text:
        return []
    # Replace commas and newlines with spaces
    cleaned_text = text.replace(',', ' ').replace('\n', ' ')
    tokens = cleaned_text.split()

    parsed_items = []
    for tok in tokens:
        item = parse_range_token(tok)
        if item:
            item['original'] = tok
            parsed_items.append(item)
    return parsed_items
