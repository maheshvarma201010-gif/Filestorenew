from helper_func import encode
from database.database import db

async def get_start_link(client, string):
    """Helper to generate a working start link (short token if needed)."""
    if len(string) > 48:
        token = await db.add_payload(string)
    else:
        token = await encode(string)
    # Ensure there's a valid https:// protocol and no double slashes
    username = client.username.strip().lower()
    return f"https://t.me/{username}?start={token}"

async def generate_final_link(client, cid, start_id, end_id=None):
    """
    Generates a link for single message or contiguous message range.
    """
    cid_val = abs(int(cid))
    if end_id and end_id != start_id:
        if start_id > end_id:
            start_id, end_id = end_id, start_id
        string = f"get-{start_id * cid_val}-{end_id * cid_val}"
    else:
        string = f"get-{start_id * cid_val}"
    return await get_start_link(client, string)

async def generate_list_link(client, cid, message_ids):
    """
    Generates a link for non-contiguous message IDs list.
    """
    cid_val = abs(int(cid))
    message_ids = sorted(list(set(message_ids)))
    if not message_ids:
        return None

    # Check if contiguous
    is_contiguous = True
    for i in range(len(message_ids) - 1):
        if message_ids[i+1] != message_ids[i] + 1:
            is_contiguous = False
            break

    if is_contiguous:
        return await generate_final_link(client, cid, message_ids[0], message_ids[-1])

    id_list = "-".join(map(str, message_ids))
    string = f"list-{cid_val}-{id_list}"
    return await get_start_link(client, string)
