from bs4 import BeautifulSoup
import re

class RichText:
    @staticmethod
    def format_heading(text, level=1):
        """Format a heading using standard bold sizing."""
        if level == 1:
            return f"<b>👑 {text.upper()} 👑</b>"
        elif level == 2:
            return f"<b>✨ {text} ✨</b>"
        else:
            return f"<b>• {text}</b>"

    @staticmethod
    def format_quote(text, expandable=False):
        """Format a quote using HTML blockquote, with optional expandable attribute."""
        if expandable:
            return f"<blockquote expandable>{text}</blockquote>"
        return f"<blockquote>{text}</blockquote>"

    @staticmethod
    def format_table(headers, rows):
        """Generate a Unicode-based text table."""
        if not headers and not rows:
            return ""
        # Determine column widths
        num_cols = max(len(headers) if headers else 0, max(len(row) for row in rows) if rows else 0)
        col_widths = [0] * num_cols

        if headers:
            for i, h in enumerate(headers):
                if i < num_cols:
                    col_widths[i] = max(col_widths[i], len(str(h)))
        for row in rows:
            for i, val in enumerate(row):
                if i < num_cols:
                    col_widths[i] = max(col_widths[i], len(str(val)))

        # Add padding
        col_widths = [w + 2 for w in col_widths]

        # Build components
        top = "┌" + "┬".join("─" * w for w in col_widths) + "┐"
        middle = "├" + "┼".join("─" * w for w in col_widths) + "┤"
        bottom = "└" + "┴".join("─" * w for w in col_widths) + "┘"

        lines = [top]
        if headers:
            header_line = "│" + "│".join(f" {str(headers[i]).ljust(col_widths[i]-1)}" for i in range(len(headers))) + "│"
            lines.append(header_line)
            lines.append(middle)

        for row in rows:
            row_vals = []
            for i in range(num_cols):
                val = str(row[i]) if i < len(row) else ""
                row_vals.append(f" {val.ljust(col_widths[i]-1)}")
            row_line = "│" + "│".join(row_vals) + "│"
            lines.append(row_line)

        lines.append(bottom)
        table_str = "\n".join(lines)
        return f"<pre>{table_str}</pre>"

    @staticmethod
    def format_bullet_list(items):
        return "\n".join(f"• {item}" for item in items)

    @staticmethod
    def format_numbered_list(items):
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

    @staticmethod
    def format_checkbox_list(items_with_checked):
        # list of tuples (checked_bool, text) or dicts
        lines = []
        for item in items_with_checked:
            if isinstance(item, tuple):
                checked, text = item
            else:
                checked = item.get('checked', False)
                text = item.get('text', '')
            box = "[x]" if checked else "[ ]"
            lines.append(f"{box} {text}")
        return "\n".join(lines)

    @staticmethod
    def format_mention(user_id, name):
        return f'<a href="tg://user?id={user_id}">{name}</a>'

    @staticmethod
    def format_custom_emoji(emoji_id, fallback_text):
        return f'<tg-emoji id="{emoji_id}">{fallback_text}</tg-emoji>'

    @staticmethod
    def clean_unsupported(html_text, is_legacy=False):
        """
        Parses and strips unsupported tags to fall back gracefully.
        If is_legacy is True:
          - Strips <tg-emoji> and replaces with inner text.
          - Strips nested blockquotes or <blockquote expandable> down to standard blockquote.
        """
        if not html_text:
            return html_text

        try:
            soup = BeautifulSoup(html_text, "html.parser")
        except Exception:
            # Fallback regex if bs4 fails
            if is_legacy:
                html_text = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', html_text)
                html_text = html_text.replace("<blockquote expandable>", "<blockquote>")
            return html_text

        if is_legacy:
            # Strip tg-emoji tag but keep its text content
            for tg_emoji in soup.find_all("tg-emoji"):
                tg_emoji.unwrap()

            # Convert <blockquote expandable> to normal blockquote
            for bq in soup.find_all("blockquote"):
                if bq.has_attr("expandable"):
                    del bq["expandable"]

            # Check for nested blockquotes
            for bq in soup.find_all("blockquote"):
                parent_bq = bq.find_parent("blockquote")
                if parent_bq:
                    bq.insert_before("\n  ")
                    bq.unwrap()

        return str(soup)

async def check_client_compatibility(query) -> bool:
    """
    Check client compatibility from a callback query.
    Detects if the user's client is legacy or older.
    Uses user settings/preferences in MongoDB user collection,
    or checks callback query data for legacy indicator.
    """
    if not query or not query.from_user:
        return True

    user_id = query.from_user.id

    # 1. Check callback query data for legacy indicator
    if hasattr(query, "data") and query.data and "legacy" in query.data:
        return False

    # 2. Check user document in database
    try:
        from database.database import db
        user_doc = await db.user_data.find_one({"_id": user_id})
        if user_doc and user_doc.get("legacy_client") is True:
            return False
    except Exception as e:
        print(f"Error checking user client compatibility: {e}")

    return True
