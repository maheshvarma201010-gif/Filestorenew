import re

def split_blocks_into_parts(blocks, limit=4000):
    parts = []
    current_part = []
    current_length = 0

    for block in blocks:
        block_len = len(block) + 2 # +2 for '\n\n'
        if current_length + block_len > limit:
            if current_part:
                parts.append("\n\n".join(current_part))
                current_part = [block]
                current_length = block_len
            else:
                parts.append(block)
                current_part = []
                current_length = 0
        else:
            current_part.append(block)
            current_length += block_len

    if current_part:
        parts.append("\n\n".join(current_part))

    return parts

def label_parts(parts, header_info=""):
    num_parts = len(parts)
    if num_parts <= 1:
        return [f"{header_info}\n\n{parts[0]}".strip() if header_info else parts[0]]

    labeled = []
    for idx, part in enumerate(parts, 1):
        label = f"<b>Part {idx}/{num_parts}</b>"
        if header_info:
            labeled.append(f"{header_info}\n\n{label}\n\n{part}")
        else:
            labeled.append(f"{label}\n\n{part}")
    return labeled

def format_single_link_ui(original, filename, caption, link):
    return (
        f"╭─── ✦ LINK GENERATED ✦ ───╮\n\n"
        f"<b>Original Link:</b>\n"
        f"{original}\n\n"
        f"<b>Filename:</b>\n"
        f"<code>{filename}</code>\n\n"
        f"<b>Filecaption:</b>\n"
        f"{caption}\n\n"
        f"🔗 <b>Link:</b>\n"
        f"<code>{link}</code>\n\n"
        f"╰──────────────────────────╯"
    )

def format_batch_link_ui(original, first_file, first_cap, last_file, last_cap, link):
    return (
        f"╭─── ✦ BATCH GENERATED ✦ ───╮\n\n"
        f"<b>Original RANGE Link:</b>\n"
        f"{original}\n\n"
        f"<b>FIRST Filename:</b>\n"
        f"<code>{first_file}</code>\n"
        f"<b>FIRST Filecaption:</b>\n"
        f"{first_cap}\n\n"
        f"<b>LAST Filename:</b>\n"
        f"<code>{last_file}</code>\n"
        f"<b>LAST Filecaption:</b>\n"
        f"{last_cap}\n\n"
        f"🔗 <b>Link:</b>\n"
        f"<code>{link}</code>\n\n"
        f"╰──────────────────────────╯"
    )

def format_bulk_summary_ui(success_count, failed_count, failed_items=None):
    text = (
        f"╭─── ✦ COMPLETED ✦ ───╮\n\n"
        f"✅ <b>Successful:</b> {success_count}\n"
        f"❌ <b>Failed:</b> {failed_count}\n"
    )
    if failed_items:
        text += "\n<b>Failed Details:</b>\n"
        for item in failed_items:
            text += f"• {item}\n"
    text += "\n╰─────────────────────╯"
    return text
